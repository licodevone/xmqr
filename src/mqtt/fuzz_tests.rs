// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Luis E. S. Pinheiro
//! P90: stable-Rust, seeded mutational fuzzing, not coverage-guided fuzzing.
//! Only synthetic fixtures and private temporary Linux state are used.

use std::{
    collections::{BTreeMap, BTreeSet, VecDeque},
    panic::{AssertUnwindSafe, catch_unwind},
    sync::Arc,
    time::Instant as WallClock,
};

use serde::{Deserialize, Serialize};
use tempfile::TempDir;

use super::{FrameReader, MAX_PACKET, decode, frame_header};
use crate::{
    auth::AccessPolicy,
    mqtt::{
        Router, StateLimits,
        router::{AckKind, Delivery},
        store::{
            DurableSession, DurableState, InboundQos2, MqttStore, OutboundInflight, OutboundStage,
            PendingWill, StoredMessage, validate_with_limits,
        },
        topic::{TopicFilter, TopicName},
    },
    persistence::Store,
};

const PRINCIPAL: &str = "__open_lab__";
const CORPUS: &str = include_str!("../../tests/fuzz-corpus/codec.hex");
const TOPICS: &str = include_str!("../../tests/fuzz-corpus/topics.txt");

struct Rng(u64);
impl Rng {
    fn next(&mut self) -> u64 {
        // Fixed xorshift64* algorithm; seed 0 is rejected by the driver.
        self.0 ^= self.0 >> 12;
        self.0 ^= self.0 << 25;
        self.0 ^= self.0 >> 27;
        self.0.wrapping_mul(0x2545_f491_4f6c_dd1d)
    }
    fn index(&mut self, length: usize) -> usize {
        usize::try_from(self.next() % u64::try_from(length.max(1)).unwrap()).unwrap()
    }
    fn byte(&mut self) -> u8 {
        u8::try_from(self.next() & 255).unwrap()
    }
}

fn seed() -> u64 {
    let result = std::env::var("XMQR_FUZZ_SEED")
        .ok()
        .map_or(0x90_311_001, |v| v.parse::<u64>().expect("decimal seed"));
    assert_ne!(result, 0);
    result
}

fn rounds(name: &str, default: usize, maximum: usize) -> usize {
    let count = std::env::var(name)
        .ok()
        .map_or(default, |v| v.parse::<usize>().expect("iteration count"));
    assert!((1..=maximum).contains(&count));
    count
}

fn corpus() -> Vec<Vec<u8>> {
    CORPUS
        .lines()
        .filter(|line| !line.starts_with('#') && !line.is_empty())
        .map(|line| {
            line.split_whitespace()
                .map(|word| u8::from_str_radix(word, 16).unwrap())
                .collect()
        })
        .collect()
}

fn mutate(input: &[u8], corpus: &[Vec<u8>], rng: &mut Rng, max: usize) -> Vec<u8> {
    let mut bytes = input.to_vec();
    for _ in 0..=rng.index(5) {
        let position = rng.index(bytes.len() + 1);
        match rng.index(7) {
            0 if position < bytes.len() => bytes[position] ^= 1 << rng.index(8),
            1 if position < bytes.len() => bytes[position] = rng.byte(),
            2 if bytes.len() < max => bytes.insert(position, rng.byte()),
            3 if position < bytes.len() => {
                bytes.remove(position);
            }
            4 => bytes.truncate(position),
            5 => {
                let extra = &corpus[rng.index(corpus.len())];
                bytes.extend_from_slice(&extra[..extra.len().min(max - bytes.len())]);
            }
            6 => {
                let count = rng.index(128).min(max - bytes.len());
                let value = rng.byte();
                bytes.resize(bytes.len() + count, value);
            }
            _ => {}
        }
    }
    assert!(bytes.len() <= max);
    bytes
}

#[derive(Debug, Eq, PartialEq)]
enum Framing {
    Incomplete,
    Invalid,
    Body(usize, usize),
}

fn reference_header(input: &[u8]) -> Framing {
    // Independently collect RL digits then evaluate bit weights in a u64.
    let digits: Vec<_> = input.iter().skip(1).take(4).copied().collect();
    for end in 0..digits.len() {
        let sum = digits[..=end]
            .iter()
            .enumerate()
            .map(|(place, byte)| u64::from(byte & 127) << (7 * place))
            .sum::<u64>();
        let size = sum + u64::try_from(end + 2).unwrap();
        if size > 65_536 {
            return Framing::Invalid;
        }
        if digits[end] < 128 {
            return Framing::Body(end + 2, usize::try_from(sum).unwrap());
        }
    }
    if digits.len() == 4 {
        Framing::Invalid
    } else {
        Framing::Incomplete
    }
}

fn header_agrees(bytes: &[u8]) -> bool {
    let actual = match frame_header(bytes) {
        Ok(Some((length, remaining))) => Framing::Body(length, remaining),
        Ok(None) => Framing::Incomplete,
        Err(_) => Framing::Invalid,
    };
    actual == reference_header(bytes)
}

fn bad_case(bytes: &[u8], agrees: &impl Fn(&[u8]) -> bool) -> bool {
    !catch_unwind(AssertUnwindSafe(|| agrees(bytes))).unwrap_or(false)
}

fn verify_case(target: &str, iteration: usize, bytes: &[u8], agrees: impl Fn(&[u8]) -> bool) {
    if !bad_case(bytes, &agrees) {
        return;
    }
    // A bounded deletion reducer persists a reproducible synthetic regression.
    let mut reduced = bytes.to_vec();
    let mut width = reduced.len().div_ceil(2).max(1);
    let mut attempts = 0;
    while width > 0 && attempts < 256 {
        let mut offset = 0;
        while offset < reduced.len() && attempts < 256 {
            let mut candidate = reduced.clone();
            candidate.drain(offset..(offset + width).min(candidate.len()));
            attempts += 1;
            if bad_case(&candidate, &agrees) {
                reduced = candidate;
            } else {
                offset += width;
            }
        }
        width /= 2;
    }
    if let Ok(directory) = std::env::var("XMQR_FUZZ_FAILURE_DIR") {
        let directory = std::path::PathBuf::from(directory);
        std::fs::create_dir_all(&directory).unwrap();
        let stem = format!("{target}-{}-{iteration}", seed());
        std::fs::write(directory.join(format!("{stem}.input")), bytes).unwrap();
        std::fs::write(directory.join(format!("{stem}.min.input")), &reduced).unwrap();
        std::fs::write(
            directory.join(format!("{stem}.txt")),
            format!(
                "seed={}\niteration={iteration}\nbytes={}\nminimized={}\n",
                seed(),
                bytes.len(),
                reduced.len()
            ),
        )
        .unwrap();
    }
    panic!(
        "synthetic fuzz mismatch target={target} seed={} iteration={iteration} original={} minimized={}",
        seed(),
        bytes.len(),
        reduced.len()
    );
}

fn report(target: &str, count: usize, accepted: usize, max: usize, start: WallClock) {
    println!(
        "XMQR_FUZZ_RESULT {{\"target\":\"{target}\",\"seed\":{},\"cases\":{count},\"accepted\":{accepted},\"max_input_bytes\":{max},\"elapsed_ms\":{}}}",
        seed(),
        start.elapsed().as_millis()
    );
}

fn reference_text(bytes: &[u8]) -> Option<&str> {
    let text = std::str::from_utf8(bytes).ok()?;
    // XMQR local policy rejects controls/noncharacters as well as mandatory NUL.
    text.chars()
        .all(|ch| {
            let scalar = u32::from(ch);
            scalar != 0
                && !(1..=31).contains(&scalar)
                && !(127..=159).contains(&scalar)
                && !(0xfdd0..=0xfdef).contains(&scalar)
                && ![0xfffe, 0xffff].contains(&(scalar & 0xffff))
        })
        .then_some(text)
}

fn common_topic(text: &str) -> bool {
    !text.is_empty() && text.len() <= 1024 && !text.contains('\0')
}

fn reference_name(text: &str) -> bool {
    common_topic(text) && !text.contains(['+', '#'])
}

fn reference_filter(text: &str) -> bool {
    if !common_topic(text) {
        return false;
    }
    let levels: Vec<_> = text.split('/').collect();
    levels.iter().enumerate().all(|(index, level)| {
        (!level.contains('+') || *level == "+")
            && (!level.contains('#') || (*level == "#" && index == levels.len() - 1))
    })
}

fn reference_match(filter: &str, topic: &str) -> bool {
    fn recurse(filters: &[&str], topics: &[&str]) -> bool {
        match (filters.split_first(), topics.split_first()) {
            (None, None) => true,
            (Some((level, [])), _) if *level == "#" => true,
            (Some((level, next_f)), Some((actual, next_t))) if *level == "+" || level == actual => {
                recurse(next_f, next_t)
            }
            _ => false,
        }
    }
    if topic.starts_with('$') && matches!(filter.split('/').next(), Some("+" | "#")) {
        return false;
    }
    recurse(
        &filter.split('/').collect::<Vec<_>>(),
        &topic.split('/').collect::<Vec<_>>(),
    )
}

struct Fields<'a>(&'a [u8]);
impl<'a> Fields<'a> {
    fn take(&mut self, size: usize) -> Option<&'a [u8]> {
        let (part, tail) = self.0.split_at_checked(size)?;
        self.0 = tail;
        Some(part)
    }
    fn word(&mut self) -> Option<u16> {
        Some(u16::from_be_bytes(self.take(2)?.try_into().ok()?))
    }
    fn binary(&mut self) -> Option<&'a [u8]> {
        let length = usize::from(self.word()?);
        self.take(length)
    }
    fn text(&mut self) -> Option<&'a str> {
        reference_text(self.binary()?)
    }
    fn id(&mut self) -> Option<()> {
        (self.word()? != 0).then_some(())
    }
}

#[allow(clippy::too_many_lines)] // Independent test grammar, intentionally separate from codec Cursor.
fn reference_decode(header: u8, bytes: &[u8]) -> Option<()> {
    let mut fields = Fields(bytes);
    match (header >> 4, header & 0x0f) {
        (1, 0) => {
            if fields.text()? != "MQTT" || fields.take(1)? != [4] {
                return None;
            }
            let flags = fields.take(1)?[0];
            let will_qos = (flags & 0x18) / 8;
            if flags & 1 != 0
                || will_qos == 3
                || (flags & 4 == 0 && flags & 0x38 != 0)
                || (flags & 64 != 0 && flags & 128 == 0)
            {
                return None;
            }
            fields.take(2)?;
            fields.text()?; // Empty ID rejection is a connection-layer decision.
            if flags & 4 != 0 && (!reference_name(fields.text()?) || fields.binary()?.len() > 4096)
            {
                return None;
            }
            if flags & 128 != 0 {
                fields.text()?;
            }
            if flags & 64 != 0 {
                fields.binary()?;
            }
        }
        (3, _) => {
            let qos = (header & 6) / 2;
            if qos == 3 || (qos == 0 && header & 8 != 0) || !reference_name(fields.text()?) {
                return None;
            }
            if qos != 0 {
                fields.id()?;
            }
            if fields.0.len() > 4096 {
                return None;
            }
            fields.0 = &[];
        }
        (4 | 5 | 7, 0) | (6, 2) => fields.id()?,
        (8 | 10, 2) => {
            fields.id()?;
            let mut count = 0;
            while !fields.0.is_empty() {
                count += 1;
                if count > 256 || !reference_filter(fields.text()?) {
                    return None;
                }
                if header >> 4 == 8 && fields.take(1)?[0] > 2 {
                    return None;
                }
            }
            if count == 0 {
                return None;
            }
        }
        (12 | 14, 0) => {}
        _ => return None,
    }
    fields.0.is_empty().then_some(())
}

fn decoder_agrees(input: &[u8]) -> bool {
    input.split_first().is_none_or(|(header, body)| {
        decode(*header, body).is_ok() == reference_decode(*header, body).is_some()
    })
}

fn fragment_agrees(bytes: &[u8], chunk: usize) -> bool {
    let mut reader = FrameReader::new(Vec::new());
    let mut pending = Vec::new();
    for piece in bytes.chunks(chunk.max(1)) {
        reader.buffer.extend_from_slice(piece);
        pending.extend_from_slice(piece);
        loop {
            let expected = match reference_header(&pending) {
                Framing::Invalid => Some(Err(())),
                Framing::Body(header, body) if pending.len() >= header + body => {
                    let result = reference_decode(pending[0], &pending[header..header + body]);
                    pending.drain(..header + body);
                    Some(result.ok_or(()))
                }
                _ => None,
            };
            let actual = reader.try_take_packet();
            match (actual, expected) {
                (Ok(None), None) if reader.buffer == pending => break,
                (Ok(Some(_)), Some(Ok(()))) if reader.buffer == pending => {}
                (Err(_), Some(Err(()))) => return true,
                _ => return false,
            }
        }
    }
    reader.buffer == pending
}

fn complete_valid_stream(mut bytes: &[u8]) -> bool {
    if bytes.is_empty() {
        return false;
    }
    while !bytes.is_empty() {
        let Framing::Body(header, body) = reference_header(bytes) else {
            return false;
        };
        if bytes.len() < header + body
            || reference_decode(bytes[0], &bytes[header..header + body]).is_none()
        {
            return false;
        }
        bytes = &bytes[header + body..];
    }
    true
}

#[test]
fn deterministic_fuzz_corpus_smoke() {
    for frame in corpus() {
        assert!(header_agrees(&frame));
        assert!(fragment_agrees(&frame, 1));
        assert!(fragment_agrees(&frame, 7));
    }
    for line in TOPICS.lines().filter(|line| !line.starts_with("# ")) {
        let Some((filter, topic)) = line.split_once('\t') else {
            continue;
        };
        let valid_filter = TopicFilter::try_from(filter.to_owned()).unwrap();
        let valid_topic = TopicName::try_from(topic.to_owned()).unwrap();
        assert_eq!(
            valid_filter.matches(&valid_topic),
            reference_match(filter, topic)
        );
    }
}

#[test]
#[ignore = "explicit P90 seeded campaign, bounded by scripts/run_fuzz.py"]
fn fuzz_frame_campaign() {
    let start = WallClock::now();
    let count = rounds("XMQR_FUZZ_ITERATIONS", 25_000, 1_000_000);
    let samples = corpus();
    let mut rng = Rng(seed());
    let mut max = 0;
    let mut accepted = 0;
    for index in 0..count {
        let mut bytes = mutate(
            &samples[rng.index(samples.len())],
            &samples,
            &mut rng,
            MAX_PACKET,
        );
        if index % 997 == 0 {
            bytes = vec![0; [65_536, 65_535, 16_386, 129][rng.index(4)]];
            bytes[..4].copy_from_slice(&[0x30, 0xfc, 0xff, 3]);
        }
        max = max.max(bytes.len());
        accepted += usize::from(matches!(reference_header(&bytes), Framing::Body(_, _)));
        verify_case("frame", index, &bytes, header_agrees);
    }
    report("frame", count, accepted, max, start);
}

#[test]
#[ignore = "explicit P90 seeded campaign, bounded by scripts/run_fuzz.py"]
fn fuzz_decode_campaign() {
    let start = WallClock::now();
    let count = rounds("XMQR_FUZZ_ITERATIONS", 25_000, 1_000_000);
    let samples: Vec<_> = corpus()
        .into_iter()
        .map(|frame| {
            let offset = match reference_header(&frame) {
                Framing::Body(header, _) => header,
                _ => 1,
            };
            [vec![frame[0]], frame[offset..].to_vec()].concat()
        })
        .collect();
    let mut rng = Rng(seed());
    let mut accepted = 0;
    let mut max = 0;
    for index in 0..count {
        let mut bytes = mutate(
            &samples[rng.index(samples.len())],
            &samples,
            &mut rng,
            MAX_PACKET,
        );
        if index % 1021 == 0 {
            // Independent quota-edge PUBLISH, no use of encode_publish.
            bytes = vec![0x30, 0, 1, b't'];
            bytes.resize([4096 + 4, 4097 + 4, 65_536][rng.index(3)], b'x');
        }
        max = max.max(bytes.len());
        accepted += usize::from(!bytes.is_empty() && decode(bytes[0], &bytes[1..]).is_ok());
        verify_case("decode", index, &bytes, decoder_agrees);
    }
    report("decode", count, accepted, max, start);
}

#[test]
#[ignore = "explicit P90 seeded campaign, bounded by scripts/run_fuzz.py"]
fn fuzz_fragment_campaign() {
    let start = WallClock::now();
    let count = rounds("XMQR_FUZZ_ITERATIONS", 25_000, 1_000_000);
    let samples = corpus();
    let mut rng = Rng(seed());
    let mut max = 0;
    let mut accepted = 0;
    for index in 0..count {
        let mut base = samples[rng.index(samples.len())].clone();
        base.extend_from_slice(&samples[rng.index(samples.len())]);
        let bytes = mutate(&base, &samples, &mut rng, MAX_PACKET);
        let chunk = rng.index(32) + 1;
        max = max.max(bytes.len());
        accepted += usize::from(complete_valid_stream(&bytes));
        verify_case("fragment", index, &bytes, |case| {
            fragment_agrees(case, chunk)
        });
    }
    report("fragment", count, accepted, max, start);
}

fn topic_agrees(input: &[u8]) -> bool {
    let Some(position) = input.iter().position(|b| *b == 0xff) else {
        return true;
    };
    let (Ok(filter), Ok(topic)) = (
        std::str::from_utf8(&input[..position]),
        std::str::from_utf8(&input[position + 1..]),
    ) else {
        return true;
    };
    let actual_filter = TopicFilter::try_from(filter.to_owned());
    let actual_topic = TopicName::try_from(topic.to_owned());
    if actual_filter.is_ok() != reference_filter(filter)
        || actual_topic.is_ok() != reference_name(topic)
    {
        return false;
    }
    match (actual_filter, actual_topic) {
        (Ok(f), Ok(t)) => f.matches(&t) == reference_match(filter, topic),
        _ => true,
    }
}

#[test]
#[ignore = "explicit P90 seeded campaign, bounded by scripts/run_fuzz.py"]
fn fuzz_topics_campaign() {
    let start = WallClock::now();
    let count = rounds("XMQR_FUZZ_ITERATIONS", 25_000, 1_000_000);
    let samples: Vec<Vec<u8>> = TOPICS
        .lines()
        .filter_map(|line| {
            if line.starts_with("# ") {
                return None;
            }
            let (f, t) = line.split_once('\t')?;
            Some([f.as_bytes(), &[0xff], t.as_bytes()].concat())
        })
        .collect();
    let mut rng = Rng(seed());
    let mut max = 0;
    let mut valid = 0;
    for index in 0..count {
        let mut bytes = mutate(&samples[rng.index(samples.len())], &samples, &mut rng, 4096);
        if index % 1009 == 0 {
            // Up to 513 levels: bounded recursion in the independent reference.
            let filter = "+/".repeat(511) + "+";
            let topic = "a/".repeat(511) + "a";
            bytes = [filter.as_bytes(), &[0xff], topic.as_bytes()].concat();
        }
        max = max.max(bytes.len());
        if let Some(position) = bytes.iter().position(|b| *b == 0xff)
            && let (Ok(filter), Ok(topic)) = (
                std::str::from_utf8(&bytes[..position]),
                std::str::from_utf8(&bytes[position + 1..]),
            )
        {
            valid += usize::from(reference_filter(filter) && reference_name(topic));
        }
        verify_case("topics", index, &bytes, topic_agrees);
    }
    report("topics", count, valid, max, start);
}

fn message(topic: &str, payload: Vec<u8>, qos: u8, retain: bool) -> StoredMessage {
    StoredMessage {
        topic: TopicName::try_from(topic.to_owned()).unwrap(),
        payload,
        qos,
        retain,
        expiry_at_unix_ms: None,
        payload_format_indicator: None,
        content_type: None,
        response_topic: None,
        correlation_data: None,
        user_properties: Vec::new(),
        subscription_identifiers: Vec::new(),
        shared_origin: None,
    }
}

fn base_state() -> DurableState {
    let mut state = DurableState::default();
    let mut session = DurableSession::new(PRINCIPAL.to_owned(), true);
    session
        .subscriptions
        .insert(TopicFilter::try_from("fuzz/#".to_owned()).unwrap(), 1);
    session
        .offline
        .push_back(message("fuzz/a", vec![1], 1, false));
    session.inbound_qos2.push(InboundQos2 {
        packet_id: 7,
        message: message("fuzz/a", vec![2], 2, false),
    });
    session.outbound.push(OutboundInflight {
        packet_id: 8,
        message: message("fuzz/a", vec![3], 1, false),
        stage: OutboundStage::AwaitPubAck,
    });
    state.sessions.insert("fuzz".to_owned(), session);
    let item = message("fuzz/a", vec![4], 1, true);
    state.retained.insert(item.topic.clone(), item);
    state
}

fn reference_state(state: &DurableState, limits: StateLimits) -> bool {
    let message_valid = |message: &StoredMessage| message.payload.len() <= 4096 && message.qos <= 2;
    if state.sessions.len() > limits.max_sessions
        || state.pending_wills.len() > limits.max_sessions
        || state.retained.len() > limits.max_retained
    {
        return false;
    }
    for (id, session) in &state.sessions {
        let mut incoming = BTreeSet::new();
        let mut outgoing = BTreeSet::new();
        if id.is_empty()
            || id.len() > 256
            || session.principal.is_empty()
            || session.principal.len() > 256
            || session.next_packet_id == 0
            || session.subscriptions.len() > limits.max_subscriptions
            || session.subscriptions.values().any(|qos| *qos > 2)
            || session.offline.len() > limits.max_offline
            || session
                .offline
                .iter()
                .any(|m| !message_valid(m) || m.qos == 0)
            || session.inbound_qos2.len() > limits.max_inflight
            || session.outbound.len() > limits.max_inflight
        {
            return false;
        }
        for entry in &session.inbound_qos2 {
            if entry.packet_id == 0
                || !incoming.insert(entry.packet_id)
                || !message_valid(&entry.message)
                || entry.message.qos != 2
            {
                return false;
            }
        }
        for entry in &session.outbound {
            if entry.packet_id == 0
                || !outgoing.insert(entry.packet_id)
                || !message_valid(&entry.message)
            {
                return false;
            }
            if !matches!(
                (entry.stage, entry.message.qos),
                (OutboundStage::AwaitPubAck, 1)
                    | (OutboundStage::AwaitPubRec | OutboundStage::AwaitPubComp, 2)
            ) {
                return false;
            }
        }
    }
    state.retained.iter().all(|(topic, m)| {
        message_valid(m) && !m.payload.is_empty() && m.retain && topic == &m.topic
    }) && state.pending_wills.iter().all(|(id, will)| {
        message_valid(&will.message)
            && state
                .sessions
                .get(id)
                .is_some_and(|session| session.principal == will.principal)
    })
}

fn state_candidate(rng: &mut Rng) -> DurableState {
    let mut state = base_state();
    let session = state.sessions.get_mut("fuzz").unwrap();
    // Known-valid/invalid semantic changes, independently classified by model.
    match rng.index(15) {
        0 => session.next_packet_id = 0,
        1 => session.principal.clear(),
        2 => session.offline[0].qos = rng.byte(),
        3 => session.offline[0].payload.resize(4097, 0),
        4 => session.inbound_qos2[0].packet_id = 0,
        5 => session.inbound_qos2.push(session.inbound_qos2[0].clone()),
        6 => session.outbound[0].stage = OutboundStage::AwaitPubComp,
        7 => session.outbound.push(session.outbound[0].clone()),
        8 => session
            .subscriptions
            .values_mut()
            .for_each(|qos| *qos = rng.byte()),
        9 => state
            .retained
            .values_mut()
            .for_each(|item| item.retain = false),
        10 => state
            .retained
            .values_mut()
            .for_each(|item| item.payload.clear()),
        11 => state
            .retained
            .values_mut()
            .for_each(|item| item.topic = TopicName::try_from("different".to_owned()).unwrap()),
        12 => {
            state.pending_wills.insert(
                "missing".to_owned(),
                PendingWill {
                    principal: PRINCIPAL.to_owned(),
                    message: message("fuzz/a", vec![1], 0, false),
                    delay_seconds: 0,
                    publish_at_unix_ms: None,
                },
            );
        }
        13 => {
            session.offline = VecDeque::from(vec![message("fuzz/a", vec![1], 1, false); 5]);
        }
        _ => session.offline[0].payload = vec![rng.byte(); rng.index(64)],
    }
    state
}

#[derive(Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct TestDocument {
    version: u16,
    state: DurableState,
}

fn reference_document(bytes: &[u8], limits: StateLimits) -> Option<DurableState> {
    let document: TestDocument = toml::from_str(std::str::from_utf8(bytes).ok()?).ok()?;
    (matches!(document.version, 1 | 2) && reference_state(&document.state, limits))
        .then_some(document.state)
}

#[tokio::test]
async fn deterministic_fuzz_state_smoke() {
    let limits = StateLimits::new(4, 4, 4, 4, 4).unwrap();
    let mut rng = Rng(0x90_311_001);
    for _ in 0..64 {
        let state = state_candidate(&mut rng);
        assert_eq!(
            validate_with_limits(&state, limits).is_ok(),
            reference_state(&state, limits)
        );
    }
    let dir = TempDir::new().unwrap();
    let (store, _) = MqttStore::open_with_limits(dir.path(), limits)
        .await
        .unwrap();
    store.commit(&base_state()).await.unwrap();
    store.shutdown().await.unwrap();
    let (store, recovered) = MqttStore::open_with_limits(dir.path(), limits)
        .await
        .unwrap();
    assert_eq!(recovered, base_state());
    store.shutdown().await.unwrap();
}

#[tokio::test]
#[ignore = "explicit P90 seeded campaign, bounded by scripts/run_fuzz.py"]
async fn fuzz_state_campaign() {
    let start = WallClock::now();
    let count = rounds("XMQR_FUZZ_STATE_ITERATIONS", 128, 1024);
    let limits = StateLimits::new(4, 4, 4, 4, 4).unwrap();
    let mut rng = Rng(seed());
    let template = toml::to_string(&TestDocument {
        version: 2,
        state: base_state(),
    })
    .unwrap()
    .into_bytes();
    let raw = b"version = 2\n[state]\n[state.sessions]\n[state.retained]\n[state.pending_wills]\n"
        .to_vec();
    let samples = [
        template,
        raw,
        b"version=999\n[state]\nsessions={}\nretained={}\n".to_vec(),
    ]
    .to_vec();
    let mut max = 0;
    let mut accepted = 0;
    for index in 0..count {
        let candidate = state_candidate(&mut rng);
        assert_eq!(
            validate_with_limits(&candidate, limits).is_ok(),
            reference_state(&candidate, limits),
            "seed={} iteration={index}",
            seed()
        );
        let bytes = if index % 8 == 0 {
            samples[rng.index(samples.len())].clone()
        } else {
            mutate(
                &samples[rng.index(samples.len())],
                &samples,
                &mut rng,
                65_536,
            )
        };
        max = max.max(bytes.len());
        let expected = reference_document(&bytes, limits);
        let dir = TempDir::new().unwrap();
        let path = dir.path().to_path_buf();
        tokio::task::spawn_blocking(move || {
            let mut writer = Store::open(path).unwrap();
            writer.put(b"mqtt311.state.v1", &bytes).unwrap();
        })
        .await
        .unwrap();
        let actual = MqttStore::open_with_limits(dir.path(), limits).await;
        match (actual, expected) {
            (Ok((writer, state)), Some(expected)) => {
                assert_eq!(state, expected);
                accepted += 1;
                writer.shutdown().await.unwrap();
            }
            (Err(_), None) => {}
            _ => panic!(
                "state restore disagreement seed={} iteration={index}",
                seed()
            ),
        }
    }
    report("state", count, accepted, max, start);
}

#[tokio::test]
#[ignore = "explicit P90 seeded campaign, bounded by scripts/run_fuzz.py"]
#[allow(clippy::too_many_lines)] // Keep each sequential model epoch, recovery and ACK check together.
async fn fuzz_router_campaign() {
    let start = WallClock::now();
    let count = rounds("XMQR_FUZZ_ROUTER_ITERATIONS", 256, 4096);
    let limits = StateLimits::new(4, 8, 4, 32, 32).unwrap();
    let dir = TempDir::new().unwrap();
    let policy = Arc::new(AccessPolicy::open_lab());
    let mut rng = Rng(seed());
    let mut model = BTreeMap::<String, Vec<u8>>::new();
    let mut offline = Vec::<(String, Vec<u8>)>::new();
    let mut accepted = 0;
    let mut maximum_payload = 0;
    for epoch in 0..count.div_ceil(16) {
        let router =
            Router::start_observed_with_limits(dir.path(), policy.clone(), Arc::default(), limits)
                .await
                .unwrap();
        let publisher = router
            .register("publisher".to_owned(), PRINCIPAL.to_owned(), false)
            .await
            .unwrap();
        if epoch == 0 {
            let subscriber = router
                .register("subscriber".to_owned(), PRINCIPAL.to_owned(), false)
                .await
                .unwrap();
            let result = router
                .subscribe(
                    &subscriber,
                    vec![(TopicFilter::try_from("fuzz/#".to_owned()).unwrap(), Some(1))],
                )
                .await
                .unwrap();
            assert_eq!(result.0, [1]);
            router.unregister(&subscriber, true).await.unwrap();
        }
        for index in (epoch * 16)..((epoch + 1) * 16).min(count) {
            let topic = format!("fuzz/{}", rng.index(11));
            let payload = if rng.index(4) == 0 {
                Vec::new()
            } else {
                vec![rng.byte(); rng.index(31) + 1]
            };
            let retain = rng.index(3) != 0;
            maximum_payload = maximum_payload.max(payload.len());
            let qos = u8::try_from(rng.index(2)).unwrap();
            let mut next = model.clone();
            if retain {
                if payload.is_empty() {
                    next.remove(&topic);
                } else {
                    next.insert(topic.clone(), payload.clone());
                }
            }
            let result = router
                .publish(
                    &publisher,
                    message(&topic, payload.clone(), qos, retain),
                    (qos == 1).then_some(1),
                )
                .await;
            let success = next.len() <= 8 && (qos == 0 || offline.len() < 32);
            assert_eq!(
                result.is_ok(),
                success,
                "seed={} transition={index}",
                seed()
            );
            if success {
                model = next;
                accepted += 1;
                if qos == 1 {
                    offline.push((topic, payload));
                }
            }
        }
        router.shutdown().await.unwrap();
        let (writer, restored) = MqttStore::open_with_limits(dir.path(), limits)
            .await
            .unwrap();
        let retained: BTreeMap<_, _> = restored
            .retained
            .iter()
            .map(|(topic, item)| (topic.as_str().to_owned(), item.payload.clone()))
            .collect();
        assert_eq!(retained, model, "seed={} epoch={epoch}", seed());
        let actual_offline: Vec<_> = restored.sessions["subscriber"]
            .offline
            .iter()
            .map(|item| (item.topic.as_str().to_owned(), item.payload.clone()))
            .collect();
        assert_eq!(actual_offline, offline);
        writer.shutdown().await.unwrap();
        let router =
            Router::start_observed_with_limits(dir.path(), policy.clone(), Arc::default(), limits)
                .await
                .unwrap();
        let subscriber = router
            .register("subscriber".to_owned(), PRINCIPAL.to_owned(), false)
            .await
            .unwrap();
        assert!(subscriber.resumed);
        let replay: Vec<_> = subscriber
            .replay
            .iter()
            .map(|delivery| match delivery {
                Delivery::Publish {
                    message,
                    packet_id: Some(_),
                    ..
                } => (message.topic.as_str().to_owned(), message.payload.clone()),
                _ => panic!("unexpected replay"),
            })
            .collect();
        assert_eq!(replay, offline);
        for delivery in &subscriber.replay {
            let Delivery::Publish {
                packet_id: Some(id),
                ..
            } = delivery
            else {
                unreachable!()
            };
            assert_eq!(
                router
                    .ack(&subscriber, AckKind::Ack, *id)
                    .await
                    .unwrap()
                    .len(),
                0
            );
        }
        offline.clear();
        router.unregister(&subscriber, true).await.unwrap();
        router.shutdown().await.unwrap();
    }
    report("router", count, accepted, maximum_payload, start);
}
