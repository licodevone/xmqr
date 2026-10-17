use std::{collections::HashMap, time::Duration};

use tokio::time::Instant;

use crate::transport::BrokerConnection;

use super::topic::{TopicFilter, TopicName, valid_topic_name};

#[cfg(all(test, unix))]
#[path = "fuzz_tests.rs"]
mod fuzz_tests;

// Local quota includes the first byte, Remaining Length bytes and body.
const MAX_PACKET: usize = 64 * 1024;
const MAX_BUFFER: usize = MAX_PACKET;
const MAX_PAYLOAD: usize = 4096;
const MAX_SUBSCRIPTIONS: usize = 256;
const MAX_PARTIAL_FRAME_TIME: Duration = Duration::from_secs(30);
pub(super) const MAX_TOPIC_ALIAS: u8 = 16;

#[derive(Debug, thiserror::Error)]
#[error("unsupported MQTT protocol level {0}")]
pub(super) struct UnsupportedProtocolLevel(pub(super) u8);

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
        mqtt5: bool,
        client_id: String,
        clean_session: bool,
        session_expiry: u32,
        receive_maximum: u16,
        maximum_packet_size: Option<u32>,
        topic_alias_maximum: u16,
        keep_alive: u16,
        will: Option<super::store::StoredMessage>,
        will_delay_seconds: u32,
        username: Option<String>,
        password: Option<Vec<u8>>,
    },
    Subscribe {
        packet_id: u16,
        filters: Vec<(TopicFilter, Qos, u8)>,
    },
    Unsubscribe {
        packet_id: u16,
        filters: Vec<TopicFilter>,
    },
    Publish {
        topic: Option<TopicName>,
        topic_alias: Option<u16>,
        payload: Vec<u8>,
        qos: Qos,
        retain: bool,
        dup: bool,
        packet_id: Option<u16>,
        expiry_interval: Option<u32>,
        payload_format_indicator: Option<u8>,
        content_type: Option<String>,
        response_topic: Option<TopicName>,
        correlation_data: Option<Vec<u8>>,
        user_properties: Vec<(String, String)>,
    },
    PubAck(u16),
    PubRec(u16),
    PubRel(u16),
    PubComp(u16),
    PingReq,
    Disconnect {
        expiry_interval: Option<u32>,
    },
    UnsupportedConnect5 {
        maximum_packet_size: Option<u32>,
    },
}

pub(super) struct FrameReader {
    buffer: Vec<u8>,
    partial_since: Option<Instant>,
    mqtt5: bool,
    topic_alias_maximum: u16,
    topic_aliases: HashMap<u16, TopicName>,
}

impl FrameReader {
    pub(super) fn new(initial: Vec<u8>) -> Self {
        Self {
            buffer: initial,
            partial_since: None,
            mqtt5: false,
            topic_alias_maximum: 0,
            topic_aliases: HashMap::new(),
        }
    }

    pub(super) fn set_mqtt5(&mut self, topic_alias_maximum: u16) {
        self.mqtt5 = true;
        self.topic_alias_maximum = topic_alias_maximum;
        self.topic_aliases.clear();
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
            let mut packet = decode_for(header, &body, self.mqtt5)?;
            if let Packet::Publish {
                topic, topic_alias, ..
            } = &mut packet
            {
                match (*topic_alias, topic.as_ref()) {
                    (Some(alias), Some(name)) if alias <= self.topic_alias_maximum => {
                        self.topic_aliases.insert(alias, name.clone());
                    }
                    (Some(alias), None) if alias <= self.topic_alias_maximum => {
                        *topic = Some(
                            self.topic_aliases
                                .get(&alias)
                                .ok_or("unknown MQTT 5 Topic Alias")?
                                .clone(),
                        );
                    }
                    (Some(_), _) => return Err("MQTT 5 Topic Alias exceeds maximum".into()),
                    (None, Some(_)) => (),
                    (None, None) => return Err("empty MQTT 5 Topic Name without alias".into()),
                }
            }
            return Ok(Some(packet));
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
        if value + index + 1 > MAX_PACKET {
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
    fn variable_integer(&mut self) -> Result<usize, &'static str> {
        let mut value = 0_usize;
        let mut multiplier = 1_usize;
        for _ in 0..4 {
            let digit = self.byte()?;
            value += usize::from(digit & 0x7f) * multiplier;
            if digit & 0x80 == 0 {
                return Ok(value);
            }
            multiplier *= 128;
        }
        Err("invalid MQTT variable integer")
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

#[derive(Debug, PartialEq, Eq)]
enum Mqtt5ConnectProperties {
    Supported {
        expiry: u32,
        receive_maximum: u16,
        maximum_packet_size: Option<u32>,
        topic_alias_maximum: u16,
    },
    Unsupported {
        maximum_packet_size: Option<u32>,
    },
}

fn mqtt5_connect_properties_supported(raw: &[u8]) -> Result<Mqtt5ConnectProperties, &'static str> {
    let mut properties = Cursor::new(raw);
    let mut expiry_seen = false;
    let mut expiry = 0;
    let mut receive_seen = false;
    let mut receive_maximum = u16::MAX;
    let mut maximum_packet_size = None;
    let mut topic_alias_maximum = 0;
    let mut problem_seen = false;
    let mut response_seen = false;
    let mut alias_seen = false;
    while properties.pos < raw.len() {
        match properties.byte()? {
            0x11 => {
                if expiry_seen {
                    return Err("duplicate MQTT 5 Session Expiry");
                }
                expiry_seen = true;
                expiry = u32::from_be_bytes(properties.bytes(4)?.try_into().unwrap());
            }
            0x21 => {
                if receive_seen {
                    return Err("duplicate MQTT 5 Receive Maximum");
                }
                receive_seen = true;
                receive_maximum = properties.word()?;
                if receive_maximum == 0 {
                    return Err("zero MQTT 5 Receive Maximum");
                }
            }
            0x27 => {
                if maximum_packet_size.is_some() {
                    return Err("duplicate MQTT 5 Maximum Packet Size");
                }
                let maximum = u32::from_be_bytes(properties.bytes(4)?.try_into().unwrap());
                if maximum == 0 {
                    return Err("zero MQTT 5 Maximum Packet Size");
                }
                maximum_packet_size = Some(maximum);
            }
            0x17 => {
                if problem_seen || properties.byte()? > 1 {
                    return Err("invalid MQTT 5 Request Problem Information");
                }
                problem_seen = true;
            }
            0x19 => {
                if response_seen || properties.byte()? > 1 {
                    return Err("invalid MQTT 5 Request Response Information");
                }
                response_seen = true;
            }
            0x22 => {
                if alias_seen {
                    return Err("duplicate MQTT 5 Topic Alias Maximum");
                }
                alias_seen = true;
                topic_alias_maximum = properties.word()?;
            }
            0x26 => {
                let _ = properties.text()?;
                let _ = properties.text()?;
            }
            _ => {
                return Ok(Mqtt5ConnectProperties::Unsupported {
                    maximum_packet_size,
                });
            }
        }
    }
    Ok(Mqtt5ConnectProperties::Supported {
        expiry,
        receive_maximum,
        maximum_packet_size,
        topic_alias_maximum,
    })
}

fn is_noncharacter(ch: char) -> bool {
    let x = ch as u32;
    (0xfdd0..=0xfdef).contains(&x) || x & 0xffff == 0xfffe || x & 0xffff == 0xffff
}

#[cfg(test)]
fn decode(header: u8, body: &[u8]) -> Result<Packet, Box<dyn std::error::Error + Send + Sync>> {
    decode_for(header, body, false)
}

#[allow(clippy::too_many_lines)]
fn decode_for(
    header: u8,
    body: &[u8],
    mqtt5: bool,
) -> Result<Packet, Box<dyn std::error::Error + Send + Sync>> {
    let mut c = Cursor::new(body);
    if mqtt5
        && !matches!(
            header,
            0x30..=0x3f | 0x40 | 0x50 | 0x62 | 0x70 | 0x82 | 0xa2 | 0xc0 | 0xe0
        )
    {
        return Err("unsupported MQTT 5 packet in current subset".into());
    }
    let packet = match header {
        0x10 => {
            if c.text()? != "MQTT" {
                return Err("unsupported MQTT protocol".into());
            }
            let level = c.byte()?;
            if level != 4 && level != 5 {
                return Err(UnsupportedProtocolLevel(level).into());
            }
            if mqtt5 {
                return Err("duplicate MQTT 5 CONNECT".into());
            }
            let flags = c.byte()?;
            // MQTT-3.1.2-3/11/13/14/15: reserved and conditional Will flags.
            let has_will = flags & 0x04 != 0;
            let will_qos = (flags >> 3) & 0x03;
            let will_retain = flags & 0x20 != 0;
            if flags & 0x01 != 0 || will_qos == 3 || (!has_will && (will_qos != 0 || will_retain)) {
                return Err("invalid CONNECT Will flags".into());
            }
            let has_username = flags & 0x80 != 0;
            let has_password = flags & 0x40 != 0;
            if level == 4 && has_password && !has_username {
                return Err("password flag requires username flag".into());
            }
            let clean_session = flags & 0x02 != 0;
            let keep_alive = c.word()?;
            let mut session_expiry = 0;
            let mut receive_maximum = u16::MAX;
            let mut maximum_packet_size = None;
            let mut topic_alias_maximum = 0;
            if level == 5 {
                let property_length = c.variable_integer()?;
                let properties = c.bytes(property_length)?;
                match mqtt5_connect_properties_supported(properties)? {
                    Mqtt5ConnectProperties::Supported {
                        expiry,
                        receive_maximum: receive,
                        maximum_packet_size: maximum,
                        topic_alias_maximum: aliases,
                    } => {
                        session_expiry = expiry;
                        receive_maximum = receive;
                        maximum_packet_size = maximum;
                        topic_alias_maximum = aliases;
                    }
                    Mqtt5ConnectProperties::Unsupported {
                        maximum_packet_size,
                    } => {
                        return Ok(Packet::UnsupportedConnect5 {
                            maximum_packet_size,
                        });
                    }
                }
            }
            let client_id = c.text()?;
            let mut will_delay_seconds = 0;
            // MQTT-3.1.3-1: Will precedes username/password. Message is binary.
            let will = if has_will {
                if level == 5 {
                    let property_length = c.variable_integer()?;
                    let raw = c.bytes(property_length)?;
                    let mut properties = Cursor::new(raw);
                    if properties.pos < raw.len() {
                        if properties.byte()? != 0x18 {
                            return Ok(Packet::UnsupportedConnect5 {
                                maximum_packet_size,
                            });
                        }
                        will_delay_seconds =
                            u32::from_be_bytes(properties.bytes(4)?.try_into().unwrap());
                        properties.end()?;
                    }
                }
                let topic = TopicName::try_from(c.text()?)?;
                let payload = c.binary()?.to_vec();
                if payload.len() > MAX_PAYLOAD {
                    return Err("Will payload too large".into());
                }
                Some(super::store::StoredMessage {
                    topic,
                    payload,
                    qos: will_qos,
                    retain: will_retain,
                    expiry_at_unix_ms: None,
                    payload_format_indicator: None,
                    content_type: None,
                    response_topic: None,
                    correlation_data: None,
                    user_properties: Vec::new(),
                })
            } else {
                None
            };
            let username = has_username.then(|| c.text()).transpose()?;
            let password = has_password
                .then(|| c.binary().map(<[u8]>::to_vec))
                .transpose()?;
            Packet::Connect {
                mqtt5: level == 5,
                client_id,
                clean_session,
                session_expiry,
                receive_maximum,
                maximum_packet_size,
                topic_alias_maximum,
                keep_alive,
                will,
                will_delay_seconds,
                username,
                password,
            }
        }
        0x82 => {
            let packet_id = c.word()?;
            if packet_id == 0 {
                return Err("zero SUBSCRIBE packet id".into());
            }
            if mqtt5 {
                let property_length = c.variable_integer()?;
                c.bytes(property_length)?;
                if property_length != 0 {
                    return Err("MQTT 5 SUBSCRIBE properties not supported".into());
                }
            }
            let mut filters = Vec::new();
            while c.pos < body.len() {
                if filters.len() >= MAX_SUBSCRIPTIONS {
                    return Err("too many subscriptions".into());
                }
                let topic = TopicFilter::try_from(c.text()?)?;
                let options = c.byte()?;
                let retain_handling = if mqtt5 {
                    if options & 0xcc != 0 {
                        return Err("unsupported MQTT 5 SUBSCRIBE option or reserved bit".into());
                    }
                    let handling = (options >> 4) & 0x03;
                    if handling == 3 {
                        return Err("invalid MQTT 5 Retain Handling value".into());
                    }
                    handling
                } else {
                    0
                };
                // MQTT-3-8.3-4: QoS 3 and reserved option bits are malformed.
                let qos = Qos::from_u8(if mqtt5 { options & 0x03 } else { options })?;
                filters.push((topic, qos, retain_handling));
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
            if mqtt5 {
                let property_length = c.variable_integer()?;
                c.bytes(property_length)?;
                if property_length != 0 {
                    return Err("MQTT 5 UNSUBSCRIBE properties not supported".into());
                }
            }
            let mut filters = Vec::new();
            while c.pos < body.len() {
                if filters.len() >= MAX_SUBSCRIPTIONS {
                    return Err("too many unsubscribe filters".into());
                }
                let filter = TopicFilter::try_from(c.text()?)?;
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
            let topic_name = c.text()?;
            let topic = if mqtt5 && topic_name.is_empty() {
                None
            } else {
                Some(TopicName::try_from(topic_name)?)
            };
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
            let mut expiry_interval = None;
            let mut topic_alias = None;
            let mut payload_format_indicator = None;
            let mut content_type = None;
            let mut response_topic = None;
            let mut correlation_data = None;
            let mut user_properties = Vec::new();
            let mut user_property_bytes = 0_usize;
            if mqtt5 {
                let property_length = c.variable_integer()?;
                let raw = c.bytes(property_length)?;
                let mut properties = Cursor::new(raw);
                while properties.pos < raw.len() {
                    match properties.byte()? {
                        0x02 if expiry_interval.is_none() => {
                            expiry_interval =
                                Some(u32::from_be_bytes(properties.bytes(4)?.try_into().unwrap()));
                        }
                        0x23 if topic_alias.is_none() => {
                            let alias = properties.word()?;
                            if alias == 0 {
                                return Err("zero MQTT 5 Topic Alias".into());
                            }
                            topic_alias = Some(alias);
                        }
                        0x01 if payload_format_indicator.is_none() => {
                            let value = properties.byte()?;
                            if value > 1 {
                                return Err("invalid MQTT 5 Payload Format Indicator".into());
                            }
                            payload_format_indicator = Some(value);
                        }
                        0x03 if content_type.is_none() => {
                            let value = properties.text()?;
                            if value.len() > 256 {
                                return Err("MQTT 5 Content Type too long".into());
                            }
                            content_type = Some(value);
                        }
                        0x08 if response_topic.is_none() => {
                            response_topic = Some(TopicName::try_from(properties.text()?)?);
                        }
                        0x09 if correlation_data.is_none() => {
                            let value = properties.binary()?;
                            if value.len() > 256 {
                                return Err("MQTT 5 Correlation Data too long".into());
                            }
                            correlation_data = Some(value.to_vec());
                        }
                        0x26 => {
                            let key = properties.text()?;
                            let value = properties.text()?;
                            if key.len() > 256 || value.len() > 256 {
                                return Err("MQTT 5 User Property field too long".into());
                            }
                            user_property_bytes =
                                user_property_bytes.saturating_add(5 + key.len() + value.len());
                            if user_properties.len() >= 16 || user_property_bytes > 2048 {
                                return Err("MQTT 5 User Properties exceed limits".into());
                            }
                            user_properties.push((key, value));
                        }
                        _ => return Err("unsupported or duplicate MQTT 5 PUBLISH property".into()),
                    }
                }
            }
            if topic.is_none() && topic_alias.is_none() {
                return Err("empty MQTT 5 Topic Name without alias".into());
            }
            let payload = c.bytes(body.len() - c.pos)?.to_vec();
            if payload.len() > MAX_PAYLOAD {
                return Err("MQTT payload too large".into());
            }
            Packet::Publish {
                topic,
                topic_alias,
                payload,
                qos,
                retain,
                dup,
                packet_id,
                expiry_interval,
                payload_format_indicator,
                content_type,
                response_topic,
                correlation_data,
                user_properties,
            }
        }
        0x40 => Packet::PubAck(success_ack_id(&mut c, mqtt5)?),
        0x50 => Packet::PubRec(success_ack_id(&mut c, mqtt5)?),
        // MQTT-3.6.1-1: PUBREL low nibble must be 0010.
        0x62 => Packet::PubRel(success_ack_id(&mut c, mqtt5)?),
        0x70 => Packet::PubComp(success_ack_id(&mut c, mqtt5)?),
        0xc0 if body.is_empty() => Packet::PingReq,
        0xe0 => {
            let expiry_interval = if mqtt5 && c.pos < c.input.len() {
                if c.byte()? != 0 {
                    return Err("MQTT 5 DISCONNECT reason outside supported success subset".into());
                }
                if c.pos == c.input.len() {
                    None
                } else {
                    let length = c.variable_integer()?;
                    let raw = c.bytes(length)?;
                    let mut properties = Cursor::new(raw);
                    if properties.pos == raw.len() {
                        None
                    } else {
                        if properties.byte()? != 0x11 {
                            return Err("unsupported MQTT 5 DISCONNECT property".into());
                        }
                        let seconds = u32::from_be_bytes(properties.bytes(4)?.try_into().unwrap());
                        properties.end()?;
                        Some(seconds)
                    }
                }
            } else {
                None
            };
            Packet::Disconnect { expiry_interval }
        }
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

fn success_ack_id(c: &mut Cursor<'_>, mqtt5: bool) -> Result<u16, &'static str> {
    let id = nonzero_ack_id(c)?;
    if mqtt5 {
        mqtt5_optional_success_and_empty_properties(c)?;
    }
    Ok(id)
}

fn mqtt5_optional_success_and_empty_properties(c: &mut Cursor<'_>) -> Result<(), &'static str> {
    if c.pos < c.input.len() && c.byte()? != 0 {
        return Err("MQTT 5 reason code outside the supported success subset");
    }
    if c.pos < c.input.len() && c.byte()? != 0 {
        return Err("MQTT 5 packet properties not supported");
    }
    Ok(())
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

pub(super) fn encode_mqtt5_connack(reason: u8) -> [u8; 5] {
    [0x20, 0x03, 0x00, reason, 0x00]
}
pub(super) fn encode_mqtt5_success_connack(session_present: bool) -> [u8; 10] {
    // Maximum QoS absent means 2; Maximum Packet Size=65536 (0x27).
    [
        0x20,
        0x08,
        u8::from(session_present),
        0x00,
        0x05,
        0x27,
        0,
        1,
        0,
        0,
    ]
}
pub(super) fn encode_mqtt5_alias_connack(session_present: bool) -> [u8; 13] {
    // The server accepts only inbound aliases 1..=16 for this connection.
    [
        0x20,
        0x0b,
        u8::from(session_present),
        0,
        0x08,
        0x27,
        0,
        1,
        0,
        0,
        0x22,
        0,
        MAX_TOPIC_ALIAS,
    ]
}

pub(super) fn append_mqtt5_receive_maximum(mut connack: Vec<u8>, maximum: u16) -> Vec<u8> {
    // Success CONNACKs in this subset have one-byte Remaining/Property Lengths.
    debug_assert_eq!(connack[0], 0x20);
    debug_assert_ne!(maximum, 0);
    connack[1] += 3;
    connack[4] += 3;
    connack.push(0x21);
    connack.extend_from_slice(&maximum.to_be_bytes());
    connack
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
pub(super) fn encode_mqtt5_suback(packet_id: u16, codes: &[u8]) -> Vec<u8> {
    let mut out = vec![0x90];
    encode_length(3 + codes.len(), &mut out);
    out.extend_from_slice(&packet_id.to_be_bytes());
    out.push(0); // No SUBACK properties.
    out.extend_from_slice(codes);
    out
}
pub(super) fn encode_puback(packet_id: u16) -> [u8; 4] {
    encode_ack(0x40, packet_id)
}

pub(super) fn encode_mqtt5_puback_reason(packet_id: u16, reason: u8) -> [u8; 6] {
    // MQTT 5 §3.4.2: a non-success reason requires the reason byte;
    // the zero property length makes the variable header unambiguous.
    [
        0x40,
        0x04,
        packet_id.to_be_bytes()[0],
        packet_id.to_be_bytes()[1],
        reason,
        0,
    ]
}
pub(super) fn encode_mqtt5_pubrec_reason(packet_id: u16, reason: u8) -> [u8; 6] {
    [
        0x50,
        0x04,
        packet_id.to_be_bytes()[0],
        packet_id.to_be_bytes()[1],
        reason,
        0,
    ]
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
pub(super) fn encode_mqtt5_unsuback(packet_id: u16, codes: &[u8]) -> Vec<u8> {
    let mut out = vec![0xb0];
    encode_length(3 + codes.len(), &mut out);
    out.extend_from_slice(&packet_id.to_be_bytes());
    out.push(0); // No UNSUBACK properties.
    out.extend_from_slice(codes);
    out
}
fn encode_ack(header: u8, packet_id: u16) -> [u8; 4] {
    [
        header,
        0x02,
        packet_id.to_be_bytes()[0],
        packet_id.to_be_bytes()[1],
    ]
}

#[cfg(test)]
pub(super) fn encode_publish(
    topic: &str,
    payload: &[u8],
    qos: Qos,
    retain: bool,
    dup: bool,
    packet_id: Option<u16>,
) -> Result<Vec<u8>, &'static str> {
    encode_publish_for(topic, payload, qos, retain, dup, packet_id, false)
}

#[cfg(test)]
pub(super) fn encode_publish_for(
    topic: &str,
    payload: &[u8],
    qos: Qos,
    retain: bool,
    dup: bool,
    packet_id: Option<u16>,
    mqtt5: bool,
) -> Result<Vec<u8>, &'static str> {
    encode_publish_with_expiry(topic, payload, qos, retain, dup, packet_id, mqtt5, None)
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(super) enum TopicAliasMode {
    None,
    Establish(u16),
    Use(u16),
}

#[cfg(test)]
#[allow(clippy::too_many_arguments)]
pub(super) fn encode_publish_with_expiry(
    topic: &str,
    payload: &[u8],
    qos: Qos,
    retain: bool,
    dup: bool,
    packet_id: Option<u16>,
    mqtt5: bool,
    expiry_interval: Option<u32>,
) -> Result<Vec<u8>, &'static str> {
    encode_publish_with_expiry_alias(
        topic,
        payload,
        qos,
        retain,
        dup,
        packet_id,
        mqtt5,
        expiry_interval,
        TopicAliasMode::None,
    )
}

#[cfg(test)]
#[allow(clippy::too_many_arguments)]
pub(super) fn encode_publish_with_expiry_alias(
    topic: &str,
    payload: &[u8],
    qos: Qos,
    retain: bool,
    dup: bool,
    packet_id: Option<u16>,
    mqtt5: bool,
    expiry_interval: Option<u32>,
    alias_mode: TopicAliasMode,
) -> Result<Vec<u8>, &'static str> {
    encode_publish_with_properties(
        topic,
        payload,
        qos,
        retain,
        dup,
        packet_id,
        mqtt5,
        expiry_interval,
        alias_mode,
        None,
        None,
        None,
        None,
        &[],
    )
}

#[allow(clippy::too_many_arguments, clippy::too_many_lines)] // One packet boundary validates all MQTT 5 PUBLISH properties and size limits.
pub(super) fn encode_publish_with_properties(
    topic: &str,
    payload: &[u8],
    qos: Qos,
    retain: bool,
    dup: bool,
    packet_id: Option<u16>,
    mqtt5: bool,
    expiry_interval: Option<u32>,
    alias_mode: TopicAliasMode,
    payload_format_indicator: Option<u8>,
    content_type: Option<&str>,
    response_topic: Option<&str>,
    correlation_data: Option<&[u8]>,
    user_properties: &[(String, String)],
) -> Result<Vec<u8>, &'static str> {
    // MQTT-2.3.1-5 and MQTT-3.3.1-2: identifier and DUP follow QoS.
    match (qos, packet_id) {
        (Qos::AtMostOnce, None) if !dup => (),
        (Qos::AtLeastOnce | Qos::ExactlyOnce, Some(1..=u16::MAX)) => (),
        _ => return Err("invalid outbound PUBLISH QoS/packet id/dup"),
    }
    if !valid_topic_name(topic) || payload.len() > MAX_PAYLOAD {
        return Err("invalid outbound MQTT topic or payload");
    }
    if (expiry_interval.is_some()
        || alias_mode != TopicAliasMode::None
        || payload_format_indicator.is_some()
        || content_type.is_some()
        || response_topic.is_some()
        || correlation_data.is_some()
        || !user_properties.is_empty())
        && !mqtt5
    {
        return Err("MQTT 5 property on MQTT 3.1.1 PUBLISH");
    }
    if payload_format_indicator.is_some_and(|value| value > 1) {
        return Err("invalid outbound MQTT 5 Payload Format Indicator");
    }
    if content_type.is_some_and(|value| {
        value.len() > 256
            || value
                .chars()
                .any(|ch| ch == '\0' || ch.is_control() || is_noncharacter(ch))
    }) {
        return Err("invalid outbound MQTT 5 Content Type");
    }
    if response_topic.is_some_and(|value| !valid_topic_name(value)) {
        return Err("invalid outbound MQTT 5 Response Topic");
    }
    if correlation_data.is_some_and(|value| value.len() > 256) {
        return Err("outbound MQTT 5 Correlation Data too long");
    }
    if user_properties.len() > 16 {
        return Err("too many outbound MQTT 5 User Properties");
    }
    let mut user_property_bytes = 0_usize;
    for (key, value) in user_properties {
        if key.len() > 256
            || value.len() > 256
            || key
                .chars()
                .chain(value.chars())
                .any(|ch| ch == '\0' || ch.is_control() || is_noncharacter(ch))
        {
            return Err("invalid outbound MQTT 5 User Property");
        }
        user_property_bytes = user_property_bytes.saturating_add(5 + key.len() + value.len());
    }
    if user_property_bytes > 2048 {
        return Err("outbound MQTT 5 User Properties too large");
    }
    let alias = match alias_mode {
        TopicAliasMode::None => None,
        TopicAliasMode::Establish(value) | TopicAliasMode::Use(value) => Some(value),
    };
    if alias == Some(0) {
        return Err("invalid outbound MQTT 5 Topic Alias");
    }
    let name = if matches!(alias_mode, TopicAliasMode::Use(_)) {
        b"".as_slice()
    } else {
        topic.as_bytes()
    };
    let properties_len = usize::from(expiry_interval.is_some()) * 5
        + usize::from(alias.is_some()) * 3
        + usize::from(payload_format_indicator.is_some()) * 2
        + content_type.map_or(0, |value| 3 + value.len())
        + response_topic.map_or(0, |value| 3 + value.len())
        + correlation_data.map_or(0, |value| 3 + value.len())
        + user_property_bytes;
    let mut properties_header = Vec::new();
    encode_length(properties_len, &mut properties_header);
    let len = 2
        + name.len()
        + usize::from(packet_id.is_some()) * 2
        + usize::from(mqtt5) * (properties_header.len() + properties_len)
        + payload.len();
    if name.len() > u16::MAX as usize {
        return Err("outbound MQTT packet too large");
    }
    let mut out = vec![0x30 | (qos.as_u8() << 1) | u8::from(retain) | (u8::from(dup) << 3)];
    encode_length(len, &mut out);
    if out.len() + len > MAX_PACKET {
        return Err("outbound MQTT packet too large");
    }
    let topic_len = u16::try_from(name.len()).map_err(|_| "topic too long")?;
    out.extend_from_slice(&topic_len.to_be_bytes());
    out.extend_from_slice(name);
    if let Some(id) = packet_id {
        out.extend_from_slice(&id.to_be_bytes());
    }
    if mqtt5 {
        out.extend_from_slice(&properties_header);
        if let Some(value) = payload_format_indicator {
            out.extend_from_slice(&[0x01, value]);
        }
        if let Some(seconds) = expiry_interval {
            out.push(0x02);
            out.extend_from_slice(&seconds.to_be_bytes());
        }
        if let Some(alias) = alias {
            out.push(0x23);
            out.extend_from_slice(&alias.to_be_bytes());
        }
        if let Some(value) = response_topic {
            out.push(0x08);
            out.extend_from_slice(
                &u16::try_from(value.len())
                    .expect("valid topic")
                    .to_be_bytes(),
            );
            out.extend_from_slice(value.as_bytes());
        }
        if let Some(value) = correlation_data {
            out.push(0x09);
            out.extend_from_slice(
                &u16::try_from(value.len())
                    .expect("at most 256")
                    .to_be_bytes(),
            );
            out.extend_from_slice(value);
        }
        for (key, value) in user_properties {
            out.push(0x26);
            out.extend_from_slice(&u16::try_from(key.len()).expect("at most 256").to_be_bytes());
            out.extend_from_slice(key.as_bytes());
            out.extend_from_slice(
                &u16::try_from(value.len())
                    .expect("at most 256")
                    .to_be_bytes(),
            );
            out.extend_from_slice(value.as_bytes());
        }
        if let Some(value) = content_type {
            out.push(0x03);
            out.extend_from_slice(
                &u16::try_from(value.len())
                    .expect("at most 256")
                    .to_be_bytes(),
            );
            out.extend_from_slice(value.as_bytes());
        }
    }
    out.extend_from_slice(payload);
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn mqtt5_outbound_topic_alias_vectors() {
        let established = encode_publish_with_expiry_alias(
            "alias/one",
            b"x",
            Qos::AtMostOnce,
            false,
            false,
            None,
            true,
            None,
            TopicAliasMode::Establish(1),
        )
        .unwrap();
        assert_eq!(
            established,
            [
                0x30, 16, 0, 9, b'a', b'l', b'i', b'a', b's', b'/', b'o', b'n', b'e', 3, 0x23, 0,
                1, b'x'
            ]
        );
        let reused = encode_publish_with_expiry_alias(
            "alias/one",
            b"x",
            Qos::AtMostOnce,
            false,
            false,
            None,
            true,
            None,
            TopicAliasMode::Use(1),
        )
        .unwrap();
        assert_eq!(reused, [0x30, 7, 0, 0, 3, 0x23, 0, 1, b'x']);
        assert!(
            encode_publish_with_expiry_alias(
                "alias/one",
                b"x",
                Qos::AtMostOnce,
                false,
                false,
                None,
                false,
                None,
                TopicAliasMode::Use(1),
            )
            .is_err()
        );
        assert!(
            encode_publish_with_expiry_alias(
                "alias/one",
                b"x",
                Qos::AtMostOnce,
                false,
                false,
                None,
                true,
                None,
                TopicAliasMode::Establish(0),
            )
            .is_err()
        );
    }

    #[test]
    fn mqtt5_inbound_topic_alias_is_connection_local_and_bounded() {
        let mut reader = FrameReader::new(Vec::new());
        reader.set_mqtt5(u16::from(MAX_TOPIC_ALIAS));
        let mut publish = |body: &[u8]| -> Result<String, String> {
            reader.buffer.push(0x30);
            reader.buffer.push(u8::try_from(body.len()).unwrap());
            reader.buffer.extend_from_slice(body);
            let result = reader
                .try_take_packet()
                .map_err(|error| error.to_string())?;
            let Some(Packet::Publish { topic, .. }) = result else {
                panic!("expected PUBLISH");
            };
            Ok(topic.unwrap().as_str().to_owned())
        };
        assert_eq!(publish(&[0, 1, b'a', 3, 0x23, 0, 1, b'x']).unwrap(), "a");
        assert_eq!(publish(&[0, 0, 3, 0x23, 0, 1, b'y']).unwrap(), "a");
        assert_eq!(publish(&[0, 1, b'b', 3, 0x23, 0, 1, b'z']).unwrap(), "b");
        assert_eq!(publish(&[0, 0, 3, 0x23, 0, 1, b'z']).unwrap(), "b");
        assert!(publish(&[0, 1, b'a', 3, 0x23, 0, 17, b'x']).is_err());
        assert!(publish(&[0, 1, b'a', 3, 0x23, 0, 0, b'x']).is_err());
        assert!(publish(&[0, 1, b'a', 6, 0x23, 0, 1, 0x23, 0, 1]).is_err());
        assert!(publish(&[0, 0, 0, b'x']).is_err());
        drop(publish);
        reader.set_mqtt5(u16::from(MAX_TOPIC_ALIAS));
        reader
            .buffer
            .extend_from_slice(&[0x30, 7, 0, 0, 3, 0x23, 0, 1, b'y']);
        assert!(reader.try_take_packet().is_err());
        assert_eq!(
            encode_mqtt5_alias_connack(false),
            [0x20, 0x0b, 0, 0, 8, 0x27, 0, 1, 0, 0, 0x22, 0, 16]
        );
    }

    #[test]
    fn mqtt5_will_delay_connect_vectors() {
        let body = [
            0, 4, b'M', b'Q', b'T', b'T', 5, 6, 0, 30, 0, 0, 1, b'a', 5, 0x18, 0, 0, 0, 2, 0, 1,
            b't', 0, 1, b'x',
        ];
        assert!(matches!(
            decode(0x10, &body).unwrap(),
            Packet::Connect {
                mqtt5: true,
                will_delay_seconds: 2,
                will: Some(_),
                ..
            }
        ));
        let mut duplicate = body.to_vec();
        duplicate[14] = 10;
        duplicate.splice(20..20, [0x18, 0, 0, 0, 3]);
        assert!(decode(0x10, &duplicate).is_err());
        let mut truncated = body;
        truncated[14] = 4;
        assert!(decode(0x10, &truncated).is_err());
    }

    #[test]
    fn mqtt5_message_expiry_property_vectors_and_rejections() {
        let body = [0, 1, b't', 5, 2, 0, 0, 0, 7, b'x'];
        assert!(matches!(
            decode_for(0x30, &body, true).unwrap(),
            Packet::Publish { expiry_interval: Some(7), payload, .. } if payload == b"x"
        ));
        assert_eq!(
            encode_publish_with_expiry(
                "t",
                b"x",
                Qos::AtMostOnce,
                false,
                false,
                None,
                true,
                Some(7)
            )
            .unwrap(),
            [0x30, 10, 0, 1, b't', 5, 2, 0, 0, 0, 7, b'x']
        );
        for properties in [
            &[10, 2, 0, 0, 0, 1, 2, 0, 0, 0, 2][..],
            &[4, 2, 0, 0, 0][..],
            &[1, 0x26][..],
        ] {
            let mut invalid = vec![0, 1, b't'];
            invalid.extend_from_slice(properties);
            invalid.push(b'x');
            assert!(decode_for(0x30, &invalid, true).is_err());
        }
        assert!(
            encode_publish_with_expiry(
                "t",
                b"x",
                Qos::AtMostOnce,
                false,
                false,
                None,
                false,
                Some(7)
            )
            .is_err()
        );
    }

    #[test]
    fn mqtt5_publish_format_and_content_type_vectors_and_rejections() {
        let encoded = encode_publish_with_properties(
            "t",
            b"x",
            Qos::AtMostOnce,
            false,
            false,
            None,
            true,
            None,
            TopicAliasMode::None,
            Some(1),
            Some("text/plain"),
            None,
            None,
            &[],
        )
        .unwrap();
        assert_eq!(
            encoded,
            [
                0x30, 20, 0, 1, b't', 15, 0x01, 1, 0x03, 0, 10, b't', b'e', b'x', b't', b'/', b'p',
                b'l', b'a', b'i', b'n', b'x',
            ]
        );
        assert!(matches!(
            decode_for(0x30, &encoded[2..], true).unwrap(),
            Packet::Publish {
                payload_format_indicator: Some(1),
                content_type: Some(value),
                ..
            } if value == "text/plain"
        ));
        for properties in [
            &[4, 0x01, 1, 0x01, 0][..],
            &[2, 0x01, 2][..],
            &[4, 0x03, 0, 1, 0xff][..],
            &[3, 0x03, 0, 1][..],
            &[10, 0x03, 0, 2, b'a', b'b', 0x03, 0, 2, b'c', b'd'][..],
        ] {
            let mut body = vec![0, 1, b't'];
            body.extend_from_slice(properties);
            body.push(b'x');
            assert!(decode_for(0x30, &body, true).is_err());
        }
        let long = "x".repeat(128);
        let encoded = encode_publish_with_properties(
            "t",
            b"x",
            Qos::AtMostOnce,
            false,
            false,
            None,
            true,
            None,
            TopicAliasMode::None,
            Some(0),
            Some(&long),
            None,
            None,
            &[],
        )
        .unwrap();
        assert_eq!(&encoded[6..8], &[0x85, 0x01]); // 133 property bytes.
        assert!(matches!(
            decode_for(0x30, &encoded[3..], true).unwrap(),
            Packet::Publish { content_type: Some(value), .. } if value == long
        ));
        let too_long = "x".repeat(257);
        assert!(
            encode_publish_with_properties(
                "t",
                b"x",
                Qos::AtMostOnce,
                false,
                false,
                None,
                true,
                None,
                TopicAliasMode::None,
                None,
                Some(&too_long),
                None,
                None,
                &[],
            )
            .is_err()
        );
    }

    #[test]
    fn mqtt5_publish_request_properties_roundtrip_and_rejections() {
        let pairs = vec![
            ("trace".into(), "one".into()),
            ("trace".into(), "two".into()),
        ];
        let encoded = encode_publish_with_properties(
            "request/one",
            b"body",
            Qos::AtMostOnce,
            false,
            false,
            None,
            true,
            None,
            TopicAliasMode::None,
            None,
            None,
            Some("reply/one"),
            Some(&[0, 255, 7]),
            &pairs,
        )
        .unwrap();
        let remaining = if encoded[1] & 0x80 == 0 { 2 } else { 3 };
        assert!(
            matches!(decode_for(0x30, &encoded[remaining..], true).unwrap(),
            Packet::Publish { response_topic: Some(topic), correlation_data: Some(data), user_properties, .. }
                if topic.as_str() == "reply/one" && data == [0, 255, 7] && user_properties == pairs)
        );
        let invalid = encode_publish_with_properties(
            "request/one",
            b"body",
            Qos::AtMostOnce,
            false,
            false,
            None,
            true,
            None,
            TopicAliasMode::None,
            None,
            None,
            Some("reply/+"),
            None,
            &[],
        );
        assert!(invalid.is_err());
        let reject = |properties: &[u8]| {
            let mut body = vec![0, 1, b't'];
            encode_length(properties.len(), &mut body);
            body.extend_from_slice(properties);
            body.push(b'x');
            assert!(decode_for(0x30, &body, true).is_err());
        };
        reject(b"\x08\x00\x01r\x08\x00\x01s"); // Duplicate Response Topic.
        reject(b"\x09\x00\x01r\x09\x00\x01s"); // Duplicate Correlation Data.
        reject(b"\x08\x00\x07reply/+"); // Wildcard.
        reject(b"\x26\x00\x01k\x00\x01\xff"); // Invalid UTF-8 value.
        reject(b"\x26\x00\x01k\x00\x02v"); // Truncated value.
        let many = b"\x26\x00\x00\x00\x00".repeat(17);
        reject(&many);
        let mut long_correlation = vec![0x09, 0x01, 0x01];
        long_correlation.extend([0; 257]);
        reject(&long_correlation);
        let mut long_response = vec![0x08, 0x04, 0x01];
        long_response.extend([b'r'; 1025]);
        reject(&long_response);
        let mut large_user_properties = Vec::new();
        for _ in 0..5 {
            large_user_properties.extend([0x26, 0x01, 0]);
            large_user_properties.extend([b'k'; 256]);
            large_user_properties.extend([0x01, 0]);
            large_user_properties.extend([b'v'; 256]);
        }
        reject(&large_user_properties);
        let large = vec![("k".repeat(256), "v".repeat(256)); 5];
        assert!(
            encode_publish_with_properties(
                "t",
                b"x",
                Qos::AtMostOnce,
                false,
                false,
                None,
                true,
                None,
                TopicAliasMode::None,
                None,
                None,
                None,
                None,
                &large,
            )
            .is_err()
        );
    }

    #[test]
    fn mqtt5_connect_uses_versioned_connack() {
        let body = [0, 4, b'M', b'Q', b'T', b'T', 5, 2, 0, 30, 0, 0, 0];
        assert!(matches!(
            decode(0x10, &body).unwrap(),
            Packet::Connect {
                mqtt5: true,
                receive_maximum: u16::MAX,
                ..
            }
        ));
        assert_eq!(encode_mqtt5_connack(0), [0x20, 3, 0, 0, 0]);
        assert_eq!(
            encode_mqtt5_success_connack(false),
            [0x20, 8, 0, 0, 5, 0x27, 0, 1, 0, 0]
        );
        assert_eq!(encode_mqtt5_success_connack(true)[2], 1);
        assert_eq!(
            append_mqtt5_receive_maximum(encode_mqtt5_alias_connack(true).to_vec(), 1),
            [
                0x20, 0x0e, 1, 0, 0x0b, 0x27, 0, 1, 0, 0, 0x22, 0, 16, 0x21, 0, 1
            ]
        );
        assert_eq!(
            append_mqtt5_receive_maximum(encode_mqtt5_connack(0).to_vec(), 32),
            [0x20, 6, 0, 0, 3, 0x21, 0, 32]
        );
    }

    #[test]
    fn mqtt5_subscribe_and_delivery_have_versioned_wire_format() {
        assert!(matches!(
            decode_for(0x82, &[0, 1, 0, 0, 1, b'x', 1], true).unwrap(),
            Packet::Subscribe { packet_id: 1, .. }
        ));
        assert_eq!(encode_mqtt5_suback(1, &[0, 1]), [0x90, 5, 0, 1, 0, 0, 1]);
        assert_eq!(
            encode_mqtt5_puback_reason(1, 0x87),
            [0x40, 4, 0, 1, 0x87, 0]
        );
        assert_eq!(
            encode_publish_for("x", b"y", Qos::AtMostOnce, false, false, None, true).unwrap(),
            [0x30, 5, 0, 1, b'x', 0, b'y']
        );
        for body in [
            &[0, 0, 0, 0, 1, b'x', 0][..],       // Zero packet ID.
            &[0, 1, 1, 0x26, 0, 1, b'x', 0][..], // Unsupported property.
            &[0, 1, 0, 0, 1, b'x', 4][..],       // No Local.
            &[0, 1, 0][..],                      // No filters.
        ] {
            assert!(decode_for(0x82, body, true).is_err());
        }
    }

    #[test]
    fn mqtt5_retain_handling_accepts_zero_one_two_and_rejects_reserved_options() {
        for handling in 0_u8..=2 {
            let body = [0, 1, 0, 0, 1, b'x', handling << 4 | 1];
            assert!(matches!(
                decode_for(0x82, &body, true).unwrap(),
                Packet::Subscribe { filters, .. }
                    if filters.len() == 1
                        && filters[0].1 == Qos::AtLeastOnce
                        && filters[0].2 == handling
            ));
        }
        for invalid in [0x30, 0x04, 0x08, 0x40, 0x80] {
            assert!(decode_for(0x82, &[0, 1, 0, 0, 1, b'x', invalid], true).is_err());
        }
        assert!(decode_for(0x82, &[0, 1, 0, 1, b'x', 0x20], false).is_err());
    }

    #[test]
    fn mqtt5_unsubscribe_has_properties_and_reason_codes() {
        assert!(matches!(
            decode_for(0xa2, &[0, 9, 0, 0, 1, b'x'], true).unwrap(),
            Packet::Unsubscribe { packet_id: 9, filters }
                if filters.len() == 1 && filters[0].as_str() == "x"
        ));
        assert!(decode_for(0xa2, &[0, 9, 1, 0x26, 0, 1, b'x'], true).is_err());
        assert!(decode_for(0xa2, &[0, 9, 0], true).is_err());
        assert!(decode_for(0xa2, &[0, 9, 0, 0, 2, b'x'], true).is_err());
        assert!(decode_for(0xa2, &[0, 9, 0, 0, 1, b'x'], false).is_err());
        assert_eq!(
            encode_mqtt5_unsuback(9, &[0, 0x11]),
            [0xb0, 5, 0, 9, 0, 0, 0x11]
        );
    }

    #[test]
    fn mqtt5_qos2_vectors_keep_packet_identifiers_and_empty_properties() {
        assert!(matches!(
            decode_for(0x82, &[0, 3, 0, 0, 1, b'x', 2], true).unwrap(),
            Packet::Subscribe { filters, .. } if filters[0].1 == Qos::ExactlyOnce
        ));
        assert!(matches!(
            decode_for(0x34, &[0, 1, b'x', 0, 7, 0, b'y'], true).unwrap(),
            Packet::Publish {
                qos: Qos::ExactlyOnce,
                packet_id: Some(7),
                ..
            }
        ));
        assert!(matches!(
            decode_for(0x50, &[0, 7], true),
            Ok(Packet::PubRec(7))
        ));
        assert!(matches!(
            decode_for(0x62, &[0, 7], true),
            Ok(Packet::PubRel(7))
        ));
        assert!(matches!(
            decode_for(0x70, &[0, 7], true),
            Ok(Packet::PubComp(7))
        ));
        assert_eq!(
            encode_publish_for("x", b"y", Qos::ExactlyOnce, false, false, Some(7), true).unwrap(),
            [0x34, 7, 0, 1, b'x', 0, 7, 0, b'y']
        );
        assert_eq!(
            encode_mqtt5_pubrec_reason(7, 0x87),
            [0x50, 4, 0, 7, 0x87, 0]
        );
    }

    #[test]
    fn mqtt5_accepts_only_success_ack_and_normal_disconnect_forms() {
        for header in [0x40, 0x50, 0x62, 0x70] {
            for body in [&[0, 7][..], &[0, 7, 0][..], &[0, 7, 0, 0][..]] {
                assert!(decode_for(header, body, true).is_ok(), "header {header:#x}");
            }
            for body in [
                &[0, 0][..],
                &[0, 7, 0x80][..],
                &[0, 7, 0, 1][..],
                &[0, 7, 0, 0, 0][..],
            ] {
                assert!(
                    decode_for(header, body, true).is_err(),
                    "header {header:#x}"
                );
            }
            assert!(decode_for(header, &[0, 7, 0], false).is_err());
        }
        for body in [&[][..], &[0][..], &[0, 0][..]] {
            assert!(matches!(
                decode_for(0xe0, body, true),
                Ok(Packet::Disconnect {
                    expiry_interval: None
                })
            ));
        }
        for body in [&[4][..], &[0, 1][..], &[0, 0, 0][..]] {
            assert!(decode_for(0xe0, body, true).is_err());
        }
        assert!(decode_for(0xe0, &[0], false).is_err());
    }

    #[test]
    fn mqtt5_disconnect_session_expiry_property_is_strict() {
        assert!(matches!(
            decode_for(0xe0, &[0, 5, 0x11, 0, 0, 0, 2], true).unwrap(),
            Packet::Disconnect {
                expiry_interval: Some(2)
            }
        ));
        assert!(matches!(
            decode_for(0xe0, &[0, 5, 0x11, 0xff, 0xff, 0xff, 0xff], true).unwrap(),
            Packet::Disconnect {
                expiry_interval: Some(u32::MAX)
            }
        ));
        for invalid in [
            &[4][..],
            &[0, 5, 0x11, 0, 0][..],
            &[0, 5, 0x26, 0, 0, 0, 2][..],
            &[0, 10, 0x11, 0, 0, 0, 1, 0x11, 0, 0, 0, 2][..],
        ] {
            assert!(decode_for(0xe0, invalid, true).is_err(), "{invalid:?}");
        }
        assert!(decode_for(0xe0, &[0, 0], false).is_err());
    }

    #[test]
    fn mqtt5_rejects_unsupported_properties_without_decoding_as_v311() {
        let connect = [
            0, 4, b'M', b'Q', b'T', b'T', 5, 2, 0, 30, 5, 0x11, 0, 0, 0, 0, 0, 1, b'a',
        ];
        assert!(matches!(
            decode(0x10, &connect).unwrap(),
            Packet::Connect { mqtt5: true, .. }
        ));
        let mut nonzero_expiry = connect;
        nonzero_expiry[15] = 1;
        assert!(matches!(
            decode(0x10, &nonzero_expiry).unwrap(),
            Packet::Connect {
                session_expiry: 1,
                ..
            }
        ));
        let mosquitto = [
            0, 4, b'M', b'Q', b'T', b'T', 5, 2, 0, 60, 3, 0x21, 0, 20, 0, 1, b'a',
        ];
        assert!(matches!(
            decode(0x10, &mosquitto).unwrap(),
            Packet::Connect {
                mqtt5: true,
                receive_maximum: 20,
                ..
            }
        ));
        assert!(matches!(
            mqtt5_connect_properties_supported(&[0x21, 0, 20, 0x11, 0, 0, 0, 0]).unwrap(),
            Mqtt5ConnectProperties::Supported {
                expiry: 0,
                receive_maximum: 20,
                maximum_packet_size: None,
                topic_alias_maximum: 0
            }
        ));
        assert!(matches!(
            mqtt5_connect_properties_supported(&[0x11, 255, 255, 255, 255]).unwrap(),
            Mqtt5ConnectProperties::Supported {
                expiry: u32::MAX,
                receive_maximum: u16::MAX,
                maximum_packet_size: None,
                topic_alias_maximum: 0
            }
        ));
        assert!(matches!(
            mqtt5_connect_properties_supported(&[0x11, 0, 0, 0, 1]).unwrap(),
            Mqtt5ConnectProperties::Supported {
                expiry: 1,
                receive_maximum: u16::MAX,
                maximum_packet_size: None,
                topic_alias_maximum: 0
            }
        ));
        assert!(mqtt5_connect_properties_supported(&[0x21, 0, 0]).is_err());
        assert!(mqtt5_connect_properties_supported(&[0x21, 0, 20, 0x21, 0, 5]).is_err());
        assert!(matches!(
            mqtt5_connect_properties_supported(&[
                0x17, 0, 0x19, 1, 0x22, 0, 4, 0x26, 0, 1, b'a', 0, 1, b'b', 0x26, 0, 1, b'a', 0, 1,
                b'c',
            ])
            .unwrap(),
            Mqtt5ConnectProperties::Supported {
                topic_alias_maximum: 4,
                ..
            }
        ));
        for invalid in [
            &[0x17, 2][..],
            &[0x17, 0, 0x17, 1][..],
            &[0x19, 2][..],
            &[0x19, 0, 0x19, 1][..],
            &[0x22, 0, 0, 0x22, 0, 1][..],
            &[0x22, 0][..],
            &[0x26, 0, 1, 0xff, 0, 1, b'b'][..],
            &[0x26, 0, 1, b'a', 0, 2, b'b'][..],
        ] {
            assert!(mqtt5_connect_properties_supported(invalid).is_err());
        }
        assert!(decode_for(0x32, &[0, 1, b'a', 0, 1, 1, 0x23, b'x'], true).is_err());
        assert!(matches!(
            decode_for(0x34, &[0, 1, b'a', 0, 1, 0, b'x'], true).unwrap(),
            Packet::Publish {
                qos: Qos::ExactlyOnce,
                packet_id: Some(1),
                ..
            }
        ));
        assert!(decode_for(0x82, &[0, 1, 0, 1, b'a', 0], true).is_err());
    }

    #[test]
    fn mqtt5_maximum_packet_size_connect_property_is_unique_and_nonzero() {
        assert!(matches!(
            mqtt5_connect_properties_supported(&[0x27, 0, 0, 0, 10]).unwrap(),
            Mqtt5ConnectProperties::Supported {
                expiry: 0,
                receive_maximum: u16::MAX,
                maximum_packet_size: Some(10),
                topic_alias_maximum: 0
            }
        ));
        assert_eq!(
            mqtt5_connect_properties_supported(&[0x27, 0, 0, 0, 1, 0x15]).unwrap(),
            Mqtt5ConnectProperties::Unsupported {
                maximum_packet_size: Some(1)
            }
        );
        assert!(mqtt5_connect_properties_supported(&[0x27, 0, 0, 0, 0]).is_err());
        assert!(mqtt5_connect_properties_supported(&[0x27, 0, 0, 0]).is_err());
        assert!(
            mqtt5_connect_properties_supported(&[0x27, 0, 0, 0, 10, 0x27, 0, 0, 0, 5]).is_err()
        );
    }

    #[test]
    fn packet_quota_counts_complete_header_before_waiting_for_body() {
        // OASIS §2.2.3: Remaining Length excludes its bytes. 64 KiB is local.
        // Independent wire vectors: body 65532 + four-byte fixed header.
        assert_eq!(
            frame_header(&[0x10, 0xfc, 0xff, 0x03]).unwrap(),
            Some((4, 65532))
        );
        assert!(frame_header(&[0x10, 0xfd, 0xff, 0x03]).is_err());
        assert!(frame_header(&[0x10, 0x80, 0x80, 0x04]).is_err());
        // Count the actual encoded bytes, including a non-minimal fourth digit.
        assert_eq!(
            frame_header(&[0x10, 0xfb, 0xff, 0x83, 0]).unwrap(),
            Some((5, 65531))
        );
        assert!(frame_header(&[0x10, 0xfc, 0xff, 0x83, 0]).is_err());
        for partial in [&[0x10][..], &[0x10, 0xfc], &[0x10, 0xfc, 0xff]] {
            assert!(frame_header(partial).unwrap().is_none());
        }
    }

    #[test]
    fn complete_packet_boundary_survives_fragmentation_and_concatenation() {
        // MQTT §3.1.3.5 allows binary passwords; no payload quota applies to them.
        // Build fields independently, without the production encoder.
        fn connect(password_len: u16, last_digit: u8) -> Vec<u8> {
            let mut frame = vec![
                0x10, last_digit, 0xff, 0x03, 0, 4, b'M', b'Q', b'T', b'T', 4, 0xc2, 0, 30, 0, 1,
                b'x', 0, 1, b'u',
            ];
            frame.extend_from_slice(&password_len.to_be_bytes());
            frame.resize(frame.len() + usize::from(password_len), 0xff);
            frame
        }
        let accepted = connect(65514, 0xfc);
        assert_eq!(accepted.len(), MAX_PACKET);
        let mut reader = FrameReader::new(accepted[..3].to_vec());
        assert!(reader.try_take_packet().unwrap().is_none());
        reader.buffer.extend_from_slice(&accepted[3..]);
        reader.buffer.extend_from_slice(&[0xc0, 0]);
        assert!(
            matches!(reader.try_take_packet().unwrap(), Some(Packet::Connect {
            password: Some(password), ..
        }) if password.len() == 65514)
        );
        assert!(matches!(
            reader.try_take_packet().unwrap(),
            Some(Packet::PingReq)
        ));
        assert!(reader.try_take_packet().unwrap().is_none());
        let rejected = connect(65515, 0xfd);
        assert_eq!(rejected.len(), MAX_PACKET + 1);
        assert!(FrameReader::new(rejected).try_take_packet().is_err());
        assert!(
            FrameReader::new(vec![0x10, 0xfd, 0xff, 0x03])
                .try_take_packet()
                .is_err()
        );
    }

    #[test]
    fn publish_payload_boundary_is_preserved_for_all_qos() {
        // Independent MQTT §3.3 bodies exercise both decode and outbound quota.
        for qos in 0..=2 {
            for size in [4096, 4097] {
                let mut body = vec![0, 1, b'a'];
                if qos != 0 {
                    body.extend_from_slice(&[0, 1]);
                }
                body.resize(body.len() + size, 0xff);
                assert_eq!(decode(0x30 | (qos << 1), &body).is_ok(), size == 4096);
                assert_eq!(
                    encode_publish(
                        "a",
                        &vec![0xff; size],
                        Qos::from_u8(qos).unwrap(),
                        false,
                        false,
                        (qos != 0).then_some(1)
                    )
                    .is_ok(),
                    size == 4096
                );
            }
        }
    }

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
            Some(Packet::Disconnect {
                expiry_interval: None
            })
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
            Packet::Subscribe { filters, .. }
                if filters.len() == 1
                    && filters[0].0.as_str() == "a"
                    && filters[0].1 == Qos::ExactlyOnce
        ));
        assert!(matches!(
            decode(0x82, &[0, 2, 0, 7, b's', b'p', b'o', b'r', b't', b'/', b'#', 1]).unwrap(),
            Packet::Subscribe { filters, .. }
                if filters[0].0.as_str() == "sport/#"
        ));
        assert!(decode(0x82, &[0, 2, 0, 6, b's', b'p', b'o', b'r', b't', b'#', 1]).is_err());
        assert!(decode(0x82, &[0, 1, 0, 1, b'a', 3]).is_err());
        assert!(decode(0x82, &[0, 1, 0, 1, b'a', 0x80]).is_err());
        assert!(matches!(
            decode(0xa2, &[0, 4, 0, 1, b'a']).unwrap(),
            Packet::Unsubscribe { packet_id: 4, filters }
                if filters.len() == 1 && filters[0].as_str() == "a"
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

    #[test]
    fn wire_topic_and_filter_boundaries_are_utf8_bytes() {
        // Independent wire bodies exercise PUBLISH, SUBSCRIBE and UNSUBSCRIBE.
        // MQTT-4.7.3-3/4; 1024 bytes is XMQR's local quota.
        for accepted in [
            "a".repeat(1024),
            "é".repeat(512),
            format!("{}/x", "é".repeat(511)),
        ] {
            for value in [accepted.clone(), format!("{accepted}a")] {
                let allowed = value.len() == 1024;
                let mut field = u16::try_from(value.len()).unwrap().to_be_bytes().to_vec();
                field.extend_from_slice(value.as_bytes());
                let mut publish = field.clone();
                publish.push(b'x');
                assert_eq!(decode(0x30, &publish).is_ok(), allowed);
                assert_eq!(
                    encode_publish(&value, b"x", Qos::AtMostOnce, false, false, None).is_ok(),
                    allowed
                );
                let mut unsubscribe = vec![0, 1];
                unsubscribe.extend_from_slice(&field);
                assert_eq!(decode(0xa2, &unsubscribe).is_ok(), allowed);
                let mut subscribe = unsubscribe;
                subscribe.push(1);
                assert_eq!(decode(0x82, &subscribe).is_ok(), allowed);
            }
        }
        let filter = format!("{}/+", "é".repeat(511));
        let mut subscribe = vec![0, 1, 4, 0];
        subscribe.extend_from_slice(filter.as_bytes());
        subscribe.push(1);
        assert!(decode(0x82, &subscribe).is_ok());
        assert!(encode_publish(&filter, b"x", Qos::AtMostOnce, false, false, None).is_err());
    }

    #[test]
    fn will_wire_flags_binary_payload_and_utf8_limits() {
        // Independent CONNECT fields: MQTT-3.1.2-8..17, MQTT-3.1.3-1.
        fn connect(flags: u8, topic: &str, payload: &[u8]) -> Vec<u8> {
            let mut body = vec![0, 4, b'M', b'Q', b'T', b'T', 4, flags, 0, 1, 0, 1, b'x'];
            let raw = topic.as_bytes();
            body.extend_from_slice(&u16::try_from(raw.len()).unwrap().to_be_bytes());
            body.extend_from_slice(raw);
            body.extend_from_slice(&u16::try_from(payload.len()).unwrap().to_be_bytes());
            body.extend_from_slice(payload);
            body
        }
        for qos in 0..=2 {
            let bytes = connect(0x06 | (qos << 3) | 0x20, &"é".repeat(512), &[0, 255]);
            let Packet::Connect {
                will: Some(will), ..
            } = decode(0x10, &bytes).unwrap()
            else {
                panic!("Will missing")
            };
            assert_eq!(will.qos, qos);
            assert!(will.retain);
            assert_eq!(will.payload, [0, 255]);
        }
        for flags in [0x1e, 0x0a, 0x22, 0x07] {
            assert!(decode(0x10, &connect(flags, "test/state", b"bye")).is_err());
        }
        assert!(decode(0x10, &connect(0x06, &("é".repeat(512) + "x"), b"bye")).is_err());
        assert!(decode(0x10, &connect(0x06, "test/+", b"bye")).is_err());
        assert!(decode(0x10, &connect(0x06, "test/state", &vec![0; 4096])).is_ok());
        assert!(decode(0x10, &connect(0x06, "test/state", &vec![0; 4097])).is_err());
        let mut truncated = connect(0x06, "test/state", b"bye");
        truncated.pop();
        assert!(decode(0x10, &truncated).is_err());
    }
}
