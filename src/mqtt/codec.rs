use std::time::Duration;

use tokio::time::Instant;

use crate::transport::BrokerConnection;

const MAX_PACKET: usize = 64 * 1024;
const MAX_BUFFER: usize = MAX_PACKET + 5;
const MAX_PAYLOAD: usize = 4096;
const MAX_SUBSCRIPTIONS: usize = 256;
const MAX_PARTIAL_FRAME_TIME: Duration = Duration::from_secs(30);

#[derive(Clone, Copy, Debug, Eq, PartialEq, Ord, PartialOrd)]
#[allow(clippy::enum_variant_names)] // MQTT's official QoS names share this suffix.
pub(super) enum Qos {
    AtMostOnce,
    AtLeastOnce,
    ExactlyOnce,
}

impl Qos {
    pub(super) fn from_u8(value: u8) -> Result<Self, &'static str> {
        match value {
            0 => Ok(Self::AtMostOnce),
            1 => Ok(Self::AtLeastOnce),
            2 => Ok(Self::ExactlyOnce),
            _ => Err("invalid MQTT QoS"),
        }
    }

    pub(super) fn as_u8(self) -> u8 {
        match self {
            Self::AtMostOnce => 0,
            Self::AtLeastOnce => 1,
            Self::ExactlyOnce => 2,
        }
    }
}

#[derive(Debug)]
pub(super) enum Packet {
    Connect {
        client_id: String,
        clean_session: bool,
        keep_alive: u16,
        username: Option<String>,
        password: Option<Vec<u8>>,
    },
    Subscribe {
        packet_id: u16,
        filters: Vec<(String, Qos)>,
    },
    Unsubscribe {
        packet_id: u16,
        filters: Vec<String>,
    },
    Publish {
        topic: String,
        payload: Vec<u8>,
        qos: Qos,
        retain: bool,
        dup: bool,
        packet_id: Option<u16>,
    },
    PubAck(u16),
    PubRec(u16),
    PubRel(u16),
    PubComp(u16),
    PingReq,
    Disconnect,
}

pub(super) struct FrameReader {
    buffer: Vec<u8>,
    partial_since: Option<Instant>,
}

impl FrameReader {
    pub(super) fn new(initial: Vec<u8>) -> Self {
        Self {
            buffer: initial,
            partial_since: None,
        }
    }

    pub(super) async fn read_packet(
        &mut self,
        connection: &mut BrokerConnection,
        deadline: Instant,
    ) -> Result<Packet, Box<dyn std::error::Error + Send + Sync>> {
        loop {
            if let Some(packet) = self.try_take_packet()? {
                return Ok(packet);
            }
            if self.buffer.len() >= MAX_BUFFER {
                return Err("MQTT input buffer exceeded".into());
            }
            let now = Instant::now();
            let left = self
                .read_deadline(deadline, now)
                .saturating_duration_since(now);
            if left.is_zero() {
                return Err("MQTT packet/idle deadline exceeded".into());
            }
            let mut chunk = [0_u8; 4096];
            let n = connection.read_with_deadline(&mut chunk, left).await?;
            if n == 0 {
                return Err("MQTT client closed connection".into());
            }
            self.buffer.extend_from_slice(&chunk[..n]);
        }
    }

    fn read_deadline(&mut self, idle_deadline: Instant, now: Instant) -> Instant {
        if self.buffer.is_empty() {
            self.partial_since = None;
            idle_deadline
        } else {
            let started = *self.partial_since.get_or_insert(now);
            idle_deadline.min(started + MAX_PARTIAL_FRAME_TIME)
        }
    }

    fn try_take_packet(
        &mut self,
    ) -> Result<Option<Packet>, Box<dyn std::error::Error + Send + Sync>> {
        if let Some((header_len, remaining)) = frame_header(&self.buffer)?
            && self.buffer.len() >= header_len + remaining
        {
            let body = self.buffer[header_len..header_len + remaining].to_vec();
            let header = self.buffer[0];
            self.buffer.drain(..header_len + remaining);
            self.partial_since = None;
            return decode(header, &body).map(Some);
        }
        Ok(None)
    }
}

fn frame_header(
    data: &[u8],
) -> Result<Option<(usize, usize)>, Box<dyn std::error::Error + Send + Sync>> {
    if data.is_empty() {
        return Ok(None);
    }
    let mut value = 0_usize;
    let mut multiplier = 1_usize;
    for index in 1..=4 {
        let Some(&byte) = data.get(index) else {
            return Ok(None);
        };
        value += usize::from(byte & 0x7f) * multiplier;
        if value > MAX_PACKET {
            return Err("MQTT packet too large".into());
        }
        if byte & 0x80 == 0 {
            return Ok(Some((index + 1, value)));
        }
        multiplier *= 128;
    }
    Err("invalid MQTT remaining length".into())
}

struct Cursor<'a> {
    input: &'a [u8],
    pos: usize,
}
impl<'a> Cursor<'a> {
    fn new(input: &'a [u8]) -> Self {
        Self { input, pos: 0 }
    }
    fn byte(&mut self) -> Result<u8, &'static str> {
        let value = *self.input.get(self.pos).ok_or("truncated MQTT field")?;
        self.pos += 1;
        Ok(value)
    }
    fn word(&mut self) -> Result<u16, &'static str> {
        Ok(u16::from_be_bytes([self.byte()?, self.byte()?]))
    }
    fn bytes(&mut self, len: usize) -> Result<&'a [u8], &'static str> {
        let end = self.pos.checked_add(len).ok_or("MQTT length overflow")?;
        let out = self
            .input
            .get(self.pos..end)
            .ok_or("truncated MQTT field")?;
        self.pos = end;
        Ok(out)
    }
    fn binary(&mut self) -> Result<&'a [u8], &'static str> {
        let len = usize::from(self.word()?);
        self.bytes(len)
    }
    fn text(&mut self) -> Result<String, &'static str> {
        let raw = self.binary()?;
        let value = std::str::from_utf8(raw).map_err(|_| "invalid MQTT UTF-8")?;
        if value
            .chars()
            .any(|ch| ch == '\0' || ch.is_control() || is_noncharacter(ch))
        {
            return Err("invalid MQTT UTF-8 scalar");
        }
        Ok(value.to_owned())
    }
    fn end(&self) -> Result<(), &'static str> {
        if self.pos == self.input.len() {
            Ok(())
        } else {
            Err("trailing MQTT packet bytes")
        }
    }
}

fn is_noncharacter(ch: char) -> bool {
    let x = ch as u32;
    (0xfdd0..=0xfdef).contains(&x) || x & 0xffff == 0xfffe || x & 0xffff == 0xffff
}

#[allow(clippy::too_many_lines)] // One fixed-header dispatch keeps malformed forms centralized.
fn decode(header: u8, body: &[u8]) -> Result<Packet, Box<dyn std::error::Error + Send + Sync>> {
    let mut c = Cursor::new(body);
    let packet = match header {
        0x10 => {
            if c.text()? != "MQTT" || c.byte()? != 4 {
                return Err("unsupported MQTT protocol".into());
            }
            let flags = c.byte()?;
            if flags & 0x01 != 0 || flags & 0x3c != 0 {
                return Err("unsupported CONNECT flags (no Will)".into());
            }
            let has_username = flags & 0x80 != 0;
            let has_password = flags & 0x40 != 0;
            if has_password && !has_username {
                return Err("password flag requires username flag".into());
            }
            let clean_session = flags & 0x02 != 0;
            let keep_alive = c.word()?;
            let client_id = c.text()?;
            let username = has_username.then(|| c.text()).transpose()?;
            let password = has_password
                .then(|| c.binary().map(<[u8]>::to_vec))
                .transpose()?;
            Packet::Connect {
                client_id,
                clean_session,
                keep_alive,
                username,
                password,
            }
        }
        0x82 => {
            let packet_id = c.word()?;
            if packet_id == 0 {
                return Err("zero SUBSCRIBE packet id".into());
            }
            let mut filters = Vec::new();
            while c.pos < body.len() {
                if filters.len() >= MAX_SUBSCRIPTIONS {
                    return Err("too many subscriptions".into());
                }
                let topic = c.text()?;
                // MQTT-3-8.3-4: QoS 3 and reserved option bits are malformed.
                let qos = Qos::from_u8(c.byte()?)?;
                if topic.is_empty() {
                    return Err("empty subscription filter".into());
                }
                filters.push((topic, qos));
            }
            if filters.is_empty() {
                return Err("empty SUBSCRIBE".into());
            }
            Packet::Subscribe { packet_id, filters }
        }
        0xa2 => {
            let packet_id = c.word()?;
            if packet_id == 0 {
                return Err("zero UNSUBSCRIBE packet id".into());
            }
            let mut filters = Vec::new();
            while c.pos < body.len() {
                if filters.len() >= MAX_SUBSCRIPTIONS {
                    return Err("too many unsubscribe filters".into());
                }
                let filter = c.text()?;
                if filter.is_empty() {
                    return Err("empty unsubscribe filter".into());
                }
                filters.push(filter);
            }
            // MQTT-3.10.3-2: UNSUBSCRIBE requires at least one filter.
            if filters.is_empty() {
                return Err("empty UNSUBSCRIBE".into());
            }
            Packet::Unsubscribe { packet_id, filters }
        }
        0x30..=0x3f => {
            // MQTT-3.3.1-4: QoS 3 is reserved and closes the connection.
            let qos = Qos::from_u8((header >> 1) & 0x03)?;
            let retain = header & 0x01 != 0;
            let dup = header & 0x08 != 0;
            // MQTT-3.3.1-2: QoS 0 PUBLISH may not set DUP.
            if qos == Qos::AtMostOnce && dup {
                return Err("QoS 0 PUBLISH with DUP flag".into());
            }
            let topic = c.text()?;
            if !valid_exact_topic(&topic) {
                return Err("invalid publish topic".into());
            }
            // MQTT-2.3.1-5: only QoS 1/2 PUBLISH carries a Packet Identifier.
            let packet_id = if qos == Qos::AtMostOnce {
                None
            } else {
                let id = c.word()?;
                if id == 0 {
                    return Err("zero PUBLISH packet id".into());
                }
                Some(id)
            };
            let payload = c.bytes(body.len() - c.pos)?.to_vec();
            if payload.len() > MAX_PAYLOAD {
                return Err("MQTT payload too large".into());
            }
            Packet::Publish {
                topic,
                payload,
                qos,
                retain,
                dup,
                packet_id,
            }
        }
        0x40 => Packet::PubAck(nonzero_ack_id(&mut c)?),
        0x50 => Packet::PubRec(nonzero_ack_id(&mut c)?),
        // MQTT-3.6.1-1: PUBREL low nibble must be 0010.
        0x62 => Packet::PubRel(nonzero_ack_id(&mut c)?),
        0x70 => Packet::PubComp(nonzero_ack_id(&mut c)?),
        0xc0 if body.is_empty() => Packet::PingReq,
        0xe0 if body.is_empty() => Packet::Disconnect,
        _ => return Err("unsupported MQTT packet type or flags".into()),
    };
    c.end()?;
    Ok(packet)
}

fn nonzero_ack_id(c: &mut Cursor<'_>) -> Result<u16, &'static str> {
    let id = c.word()?;
    if id == 0 {
        return Err("zero acknowledgment packet id");
    }
    Ok(id)
}

pub(super) fn valid_exact_topic(topic: &str) -> bool {
    !topic.is_empty() && !topic.contains(['+', '#']) && !topic.starts_with('$')
}

fn encode_length(mut len: usize, output: &mut Vec<u8>) {
    loop {
        let mut byte = u8::try_from(len % 128).expect("base-128 digit fits u8");
        len /= 128;
        if len > 0 {
            byte |= 0x80;
        }
        output.push(byte);
        if len == 0 {
            break;
        }
    }
}
pub(super) fn encode_connack(code: u8) -> [u8; 4] {
    [0x20, 0x02, 0x00, code]
}
pub(super) fn encode_connack_with_session(
    code: u8,
    session_present: bool,
) -> Result<[u8; 4], &'static str> {
    // MQTT-3.2.2-4/5: Session Present is 0 on refusal and clean sessions.
    if code != 0 && session_present {
        return Err("refused CONNACK cannot set Session Present");
    }
    Ok([0x20, 0x02, u8::from(session_present), code])
}
pub(super) fn encode_pingresp() -> [u8; 2] {
    [0xd0, 0x00]
}
pub(super) fn encode_suback(packet_id: u16, codes: &[u8]) -> Vec<u8> {
    let mut out = vec![0x90];
    encode_length(2 + codes.len(), &mut out);
    out.extend_from_slice(&packet_id.to_be_bytes());
    out.extend_from_slice(codes);
    out
}
pub(super) fn encode_puback(packet_id: u16) -> [u8; 4] {
    encode_ack(0x40, packet_id)
}
pub(super) fn encode_pubrec(packet_id: u16) -> [u8; 4] {
    encode_ack(0x50, packet_id)
}
pub(super) fn encode_pubrel(packet_id: u16) -> [u8; 4] {
    encode_ack(0x62, packet_id)
}
pub(super) fn encode_pubcomp(packet_id: u16) -> [u8; 4] {
    encode_ack(0x70, packet_id)
}
pub(super) fn encode_unsuback(packet_id: u16) -> [u8; 4] {
    encode_ack(0xb0, packet_id)
}
fn encode_ack(header: u8, packet_id: u16) -> [u8; 4] {
    [
        header,
        0x02,
        packet_id.to_be_bytes()[0],
        packet_id.to_be_bytes()[1],
    ]
}

pub(super) fn encode_publish(
    topic: &str,
    payload: &[u8],
    qos: Qos,
    retain: bool,
    dup: bool,
    packet_id: Option<u16>,
) -> Result<Vec<u8>, &'static str> {
    // MQTT-2.3.1-5 and MQTT-3.3.1-2: identifier and DUP follow QoS.
    match (qos, packet_id) {
        (Qos::AtMostOnce, None) if !dup => (),
        (Qos::AtLeastOnce | Qos::ExactlyOnce, Some(1..=u16::MAX)) => (),
        _ => return Err("invalid outbound PUBLISH QoS/packet id/dup"),
    }
    if !valid_exact_topic(topic) || payload.len() > MAX_PAYLOAD {
        return Err("invalid outbound MQTT topic or payload");
    }
    let name = topic.as_bytes();
    let len = 2 + name.len() + usize::from(packet_id.is_some()) * 2 + payload.len();
    if name.len() > u16::MAX as usize || len > MAX_PACKET {
        return Err("outbound MQTT packet too large");
    }
    let mut out = vec![0x30 | (qos.as_u8() << 1) | u8::from(retain) | (u8::from(dup) << 3)];
    encode_length(len, &mut out);
    let topic_len = u16::try_from(name.len()).map_err(|_| "topic too long")?;
    out.extend_from_slice(&topic_len.to_be_bytes());
    out.extend_from_slice(name);
    if let Some(id) = packet_id {
        out.extend_from_slice(&id.to_be_bytes());
    }
    out.extend_from_slice(payload);
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn basic_vectors() {
        assert!(matches!(
            decode(
                0x10,
                &[
                    0, 4, b'M', b'Q', b'T', b'T', 4, 0xc2, 0, 60, 0, 1, b'a', 0, 1, b'u', 0, 1,
                    b'p'
                ]
            )
            .unwrap(),
            Packet::Connect { .. }
        ));
        assert!(matches!(
            decode(0x82, &[0, 1, 0, 1, b'a', 0]).unwrap(),
            Packet::Subscribe { .. }
        ));
        assert_eq!(encode_suback(1, &[0]), [0x90, 3, 0, 1, 0]);
        assert_eq!(
            encode_publish("a", b"x", Qos::AtMostOnce, false, false, None).unwrap(),
            [0x30, 4, 0, 1, b'a', b'x']
        );
        assert!(frame_header(&[0x30, 0xff, 0xff, 0xff, 0x7f]).is_err());
    }

    #[test]
    fn accepts_connect_without_credentials_for_policy_to_decide() {
        // MQTT-3.1.2-19/21: username and password flags may both be zero.
        assert!(matches!(
            decode(
                0x10,
                &[
                    0, 4, b'M', b'Q', b'T', b'T', 4, 0x02, 0, 30, 0, 3, b'l', b'a', b'b'
                ]
            )
            .unwrap(),
            Packet::Connect {
                username: None,
                password: None,
                ..
            }
        ));
        assert!(
            decode(
                0x10,
                &[
                    0, 4, b'M', b'Q', b'T', b'T', 4, 0x42, 0, 30, 0, 3, b'l', b'a', b'b', 0, 1,
                    b'p'
                ]
            )
            .is_err()
        );
    }

    #[test]
    fn fragmented_and_concatenated_packets() {
        let mut reader = FrameReader::new(vec![0xc0]);
        assert!(reader.try_take_packet().unwrap().is_none());
        reader.buffer.extend_from_slice(&[0, 0xe0, 0]);
        assert!(matches!(
            reader.try_take_packet().unwrap(),
            Some(Packet::PingReq)
        ));
        assert!(matches!(
            reader.try_take_packet().unwrap(),
            Some(Packet::Disconnect)
        ));
        assert!(reader.try_take_packet().unwrap().is_none());
    }

    #[test]
    fn incomplete_frame_has_independent_completion_deadline() {
        let now = Instant::now();
        let idle_deadline = now + Duration::from_secs(90_000);
        let mut reader = FrameReader::new(Vec::new());
        assert_eq!(reader.read_deadline(idle_deadline, now), idle_deadline);

        reader.buffer.push(0xc0);
        let frame_deadline = now + MAX_PARTIAL_FRAME_TIME;
        assert_eq!(reader.read_deadline(idle_deadline, now), frame_deadline);
        assert_eq!(
            reader.read_deadline(idle_deadline, now + Duration::from_secs(29)),
            frame_deadline
        );
        assert!(
            reader.read_deadline(idle_deadline, now + Duration::from_secs(31))
                <= now + Duration::from_secs(31)
        );

        reader.buffer.extend_from_slice(&[0, 0xc0]);
        assert!(matches!(
            reader.try_take_packet().unwrap(),
            Some(Packet::PingReq)
        ));
        assert_eq!(
            reader.read_deadline(idle_deadline, now + Duration::from_secs(31)),
            now + Duration::from_secs(31) + MAX_PARTIAL_FRAME_TIME
        );
    }

    #[test]
    fn rejects_malformed_qos_and_bad_connect_flags() {
        // MQTT-3.3.1-4, MQTT-3.3.1-2, MQTT-2.3.1-5.
        assert!(decode(0x36, &[0, 1, b'a', 0, 1, b'x']).is_err());
        assert!(decode(0x38, &[0, 1, b'a', b'x']).is_err());
        assert!(decode(0x32, &[0, 1, b'a', 0, 0, b'x']).is_err());
        assert!(
            decode(
                0x10,
                &[0, 4, b'M', b'Q', b'T', b'T', 4, 0x03, 0, 0, 0, 1, b'a']
            )
            .is_err()
        );
        assert!(frame_header(&[0x30, 0x80, 0x80, 0x80, 0x80]).is_err());
    }

    #[test]
    fn qos_publish_and_ack_known_vectors() {
        // MQTT-2.3.1-5/6, MQTT-3.3.1-1/2/4, MQTT-3.6.1-1.
        let one = encode_publish("a", b"x", Qos::AtLeastOnce, true, false, Some(1)).unwrap();
        assert_eq!(one, [0x33, 6, 0, 1, b'a', 0, 1, b'x']);
        assert!(matches!(
            decode(one[0], &one[2..]).unwrap(),
            Packet::Publish {
                qos: Qos::AtLeastOnce,
                retain: true,
                dup: false,
                packet_id: Some(1),
                ..
            }
        ));
        let two = encode_publish("a", b"x", Qos::ExactlyOnce, false, true, Some(2)).unwrap();
        assert_eq!(two, [0x3c, 6, 0, 1, b'a', 0, 2, b'x']);
        assert_eq!(encode_puback(1), [0x40, 2, 0, 1]);
        assert_eq!(encode_pubrec(2), [0x50, 2, 0, 2]);
        assert_eq!(encode_pubrel(2), [0x62, 2, 0, 2]);
        assert_eq!(encode_pubcomp(2), [0x70, 2, 0, 2]);
        assert!(matches!(decode(0x40, &[0, 1]).unwrap(), Packet::PubAck(1)));
        assert!(matches!(decode(0x50, &[0, 2]).unwrap(), Packet::PubRec(2)));
        assert!(matches!(decode(0x62, &[0, 2]).unwrap(), Packet::PubRel(2)));
        assert!(matches!(decode(0x70, &[0, 2]).unwrap(), Packet::PubComp(2)));
        assert!(decode(0x6a, &[0, 2]).is_err());
        assert!(decode(0x62, &[0, 2, 0]).is_err());
        assert!(encode_publish("a", b"x", Qos::AtMostOnce, false, true, None).is_err());
        assert!(encode_publish("a", b"x", Qos::ExactlyOnce, false, false, None).is_err());
    }

    #[test]
    fn subscribe_unsubscribe_qos_and_clean_session_vectors() {
        // MQTT-3-8.3-4, MQTT-3.10.3-2, MQTT-3.1.2-4/6.
        assert!(matches!(
            decode(0x82, &[0, 1, 0, 1, b'a', 2]).unwrap(),
            Packet::Subscribe { filters, .. } if filters == vec![("a".to_owned(), Qos::ExactlyOnce)]
        ));
        assert!(decode(0x82, &[0, 1, 0, 1, b'a', 3]).is_err());
        assert!(decode(0x82, &[0, 1, 0, 1, b'a', 0x80]).is_err());
        assert!(matches!(
            decode(0xa2, &[0, 4, 0, 1, b'a']).unwrap(),
            Packet::Unsubscribe { packet_id: 4, filters } if filters == vec!["a"]
        ));
        assert!(decode(0xa2, &[0, 4]).is_err());
        assert!(decode(0xa0, &[0, 4, 0, 1, b'a']).is_err());
        assert_eq!(encode_unsuback(4), [0xb0, 2, 0, 4]);
        // MQTT-3.2.2-4/5: resumed session sets Session Present; refusal cannot.
        assert_eq!(
            encode_connack_with_session(0, true).unwrap(),
            [0x20, 2, 1, 0]
        );
        assert!(encode_connack_with_session(5, true).is_err());
        assert!(matches!(
            decode(
                0x10,
                &[
                    0, 4, b'M', b'Q', b'T', b'T', 4, 0xc0, 0, 60, 0, 1, b'a', 0, 1, b'u', 0, 1,
                    b'p'
                ]
            )
            .unwrap(),
            Packet::Connect {
                clean_session: false,
                ..
            }
        ));
    }
}
