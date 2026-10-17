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

#[derive(Debug, thiserror::Error)]
#[error("MQTT packet exceeds local size limit")]
pub(super) struct PacketTooLarge;

#[derive(Debug, thiserror::Error)]
#[error("invalid MQTT 5 Topic Alias")]
pub(super) struct TopicAliasInvalid;

#[derive(Debug, thiserror::Error)]
#[error("malformed MQTT Remaining Length")]
pub(super) struct MalformedRemainingLength;

#[derive(Debug, thiserror::Error)]
#[error("invalid MQTT fixed header flags")]
pub(super) struct FixedHeaderFlagsInvalid;

#[derive(Debug, thiserror::Error)]
#[error("MQTT 5 subscription property is invalid for this packet")]
pub(super) struct SubscriptionPropertyMalformed;

#[derive(Debug, thiserror::Error)]
#[error("duplicate MQTT 5 Subscription Identifier")]
pub(super) struct SubscriptionIdentifierDuplicate;

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
        will_message_expiry_seconds: Option<u32>,
        username: Option<String>,
        password: Option<Vec<u8>>,
        plain_authentication: Option<Vec<u8>>,
    },
    Subscribe {
        packet_id: u16,
        filters: Vec<(TopicFilter, Qos, u8, u8)>,
        subscription_identifier: Option<u32>,
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
    PubAck {
        packet_id: u16,
        reason_code: u8,
    },
    PubRec {
        packet_id: u16,
        reason_code: u8,
    },
    PubRel {
        packet_id: u16,
        reason_code: u8,
    },
    PubComp {
        packet_id: u16,
        reason_code: u8,
    },
    PingReq,
    Auth {
        method: String,
        data: Vec<u8>,
    },
    Disconnect {
        reason_code: u8,
        expiry_interval: Option<u32>,
    },
    UnsupportedConnect5 {
        maximum_packet_size: Option<u32>,
        reason_code: u8,
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
                return Err(PacketTooLarge.into());
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
                                .ok_or(TopicAliasInvalid)?
                                .clone(),
                        );
                    }
                    (Some(_), _) => return Err(TopicAliasInvalid.into()),
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
            return Err(PacketTooLarge.into());
        }
        if byte & 0x80 == 0 {
            return Ok(Some((index + 1, value)));
        }
        multiplier *= 128;
    }
    Err(MalformedRemainingLength.into())
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
        plain_authentication: Option<Vec<u8>>,
    },
    Unsupported {
        maximum_packet_size: Option<u32>,
        reason_code: u8,
    },
}

fn rejected_connect_property(
    maximum_packet_size: Option<u32>,
    reason_code: u8,
) -> Mqtt5ConnectProperties {
    Mqtt5ConnectProperties::Unsupported {
        maximum_packet_size,
        reason_code,
    }
}

#[expect(
    clippy::too_many_lines,
    reason = "CONNECT property validation must classify unsupported AUTH before session creation"
)]
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
    let mut auth_method = None;
    let mut auth_data = None;
    while properties.pos < raw.len() {
        match properties.byte()? {
            0x11 => {
                if expiry_seen {
                    return Ok(rejected_connect_property(maximum_packet_size, 0x82));
                }
                expiry_seen = true;
                expiry = u32::from_be_bytes(properties.bytes(4)?.try_into().unwrap());
            }
            0x21 => {
                if receive_seen {
                    return Ok(rejected_connect_property(maximum_packet_size, 0x82));
                }
                receive_seen = true;
                receive_maximum = properties.word()?;
                if receive_maximum == 0 {
                    return Ok(rejected_connect_property(maximum_packet_size, 0x82));
                }
            }
            0x27 => {
                if maximum_packet_size.is_some() {
                    return Ok(rejected_connect_property(maximum_packet_size, 0x82));
                }
                let maximum = u32::from_be_bytes(properties.bytes(4)?.try_into().unwrap());
                if maximum == 0 {
                    return Ok(rejected_connect_property(maximum_packet_size, 0x82));
                }
                maximum_packet_size = Some(maximum);
            }
            0x17 => {
                if problem_seen || properties.byte()? > 1 {
                    return Ok(rejected_connect_property(maximum_packet_size, 0x82));
                }
                problem_seen = true;
            }
            0x19 => {
                if response_seen || properties.byte()? > 1 {
                    return Ok(rejected_connect_property(maximum_packet_size, 0x82));
                }
                response_seen = true;
            }
            0x22 => {
                if alias_seen {
                    return Ok(rejected_connect_property(maximum_packet_size, 0x82));
                }
                alias_seen = true;
                topic_alias_maximum = properties.word()?;
            }
            0x26 => {
                let _ = properties.text()?;
                let _ = properties.text()?;
            }
            0x15 => {
                if auth_method.is_some() {
                    return Ok(rejected_connect_property(maximum_packet_size, 0x82));
                }
                auth_method = Some(properties.text()?);
            }
            0x16 => {
                if auth_data.is_some() {
                    return Ok(rejected_connect_property(maximum_packet_size, 0x82));
                }
                auth_data = Some(properties.binary()?);
            }
            _ => {
                return Ok(Mqtt5ConnectProperties::Unsupported {
                    maximum_packet_size,
                    reason_code: 0x81,
                });
            }
        }
    }
    if auth_data.is_some() && auth_method.is_none() {
        return Ok(rejected_connect_property(maximum_packet_size, 0x82));
    }
    let plain_authentication = match (auth_method.as_deref(), auth_data) {
        (Some("PLAIN"), Some(data)) => Some(data.to_vec()),
        (Some("PLAIN"), None) => {
            return Ok(Mqtt5ConnectProperties::Unsupported {
                maximum_packet_size,
                reason_code: 0x86,
            });
        }
        (Some(_), _) => {
            return Ok(Mqtt5ConnectProperties::Unsupported {
                maximum_packet_size,
                reason_code: 0x8c,
            });
        }
        _ => None,
    };
    Ok(Mqtt5ConnectProperties::Supported {
        expiry,
        receive_maximum,
        maximum_packet_size,
        topic_alias_maximum,
        plain_authentication,
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
    if mqtt5 && matches!(header >> 4, 12 | 14) && header & 0x0f != 0 {
        return Err(FixedHeaderFlagsInvalid.into());
    }
    if mqtt5
        && !matches!(
            header,
            0x30..=0x3f | 0x40 | 0x50 | 0x62 | 0x70 | 0x82 | 0xa2 | 0xc0 | 0xe0 | 0xf0
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
            let mut plain_authentication = None;
            if level == 5 {
                let property_length = c.variable_integer()?;
                let properties = c.bytes(property_length)?;
                match mqtt5_connect_properties_supported(properties)? {
                    Mqtt5ConnectProperties::Supported {
                        expiry,
                        receive_maximum: receive,
                        maximum_packet_size: maximum,
                        topic_alias_maximum: aliases,
                        plain_authentication: plain,
                    } => {
                        session_expiry = expiry;
                        receive_maximum = receive;
                        maximum_packet_size = maximum;
                        topic_alias_maximum = aliases;
                        plain_authentication = plain;
                    }
                    Mqtt5ConnectProperties::Unsupported {
                        maximum_packet_size,
                        reason_code,
                    } => {
                        return Ok(Packet::UnsupportedConnect5 {
                            maximum_packet_size,
                            reason_code,
                        });
                    }
                }
            }
            let client_id = c.text()?;
            let mut will_delay_seconds = 0;
            let mut will_message_expiry_seconds = None;
            // MQTT-3.1.3-1: Will precedes username/password. Message is binary.
            let will = if has_will {
                let mut payload_format_indicator = None;
                let mut content_type = None;
                let mut response_topic = None;
                let mut correlation_data = None;
                let mut user_properties = Vec::new();
                if level == 5 {
                    let property_length = c.variable_integer()?;
                    let raw = c.bytes(property_length)?;
                    let mut properties = Cursor::new(raw);
                    let mut delay_seen = false;
                    let mut user_property_bytes = 0usize;
                    while properties.pos < raw.len() {
                        match properties.byte()? {
                            0x18 if !delay_seen => {
                                delay_seen = true;
                                will_delay_seconds =
                                    u32::from_be_bytes(properties.bytes(4)?.try_into().unwrap());
                            }
                            0x02 if will_message_expiry_seconds.is_none() => {
                                will_message_expiry_seconds = Some(u32::from_be_bytes(
                                    properties.bytes(4)?.try_into().unwrap(),
                                ));
                            }
                            0x01 if payload_format_indicator.is_none() => {
                                let value = properties.byte()?;
                                if value > 1 {
                                    return Ok(Packet::UnsupportedConnect5 {
                                        maximum_packet_size,
                                        reason_code: 0x82,
                                    });
                                }
                                payload_format_indicator = Some(value);
                            }
                            0x03 if content_type.is_none() => {
                                let value = properties.text()?;
                                if value.len() > 256 {
                                    return Err("MQTT 5 Will Content Type too long".into());
                                }
                                content_type = Some(value);
                            }
                            0x08 if response_topic.is_none() => {
                                response_topic = Some(TopicName::try_from(properties.text()?)?);
                            }
                            0x09 if correlation_data.is_none() => {
                                let value = properties.binary()?;
                                if value.len() > 256 {
                                    return Err("MQTT 5 Will Correlation Data too long".into());
                                }
                                correlation_data = Some(value.to_vec());
                            }
                            0x26 => {
                                let key = properties.text()?;
                                let value = properties.text()?;
                                if key.len() > 256 || value.len() > 256 {
                                    return Err("MQTT 5 Will User Property field too long".into());
                                }
                                user_property_bytes =
                                    user_property_bytes.saturating_add(5 + key.len() + value.len());
                                if user_properties.len() >= 16 || user_property_bytes > 2048 {
                                    return Err("MQTT 5 Will User Properties exceed limits".into());
                                }
                                user_properties.push((key, value));
                            }
                            0x18 | 0x02 | 0x01 | 0x03 | 0x08 | 0x09 => {
                                return Ok(Packet::UnsupportedConnect5 {
                                    maximum_packet_size,
                                    reason_code: 0x82,
                                });
                            }
                            _ => {
                                return Ok(Packet::UnsupportedConnect5 {
                                    maximum_packet_size,
                                    reason_code: 0x81,
                                });
                            }
                        }
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
                    payload_format_indicator,
                    content_type,
                    response_topic,
                    correlation_data,
                    user_properties,
                    subscription_identifiers: Vec::new(),
                    shared_origin: None,
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
                will_message_expiry_seconds,
                username,
                password,
                plain_authentication,
            }
        }
        0x82 => {
            let packet_id = c.word()?;
            if packet_id == 0 {
                return Err("zero SUBSCRIBE packet id".into());
            }
            let mut subscription_identifier = None;
            if mqtt5 {
                let property_length = c.variable_integer()?;
                let raw = c.bytes(property_length)?;
                let mut properties = Cursor::new(raw);
                let mut user_property_count = 0;
                let mut user_property_bytes = 0;
                while properties.pos < raw.len() {
                    match properties.byte()? {
                        0x0b if subscription_identifier.is_none() => {
                            let value = properties.variable_integer()?;
                            if value == 0 {
                                return Err("zero MQTT 5 Subscription Identifier".into());
                            }
                            subscription_identifier = Some(
                                u32::try_from(value)
                                    .map_err(|_| "invalid MQTT 5 Subscription Identifier")?,
                            );
                        }
                        0x26 => parse_subscription_user_property(
                            &mut properties,
                            &mut user_property_count,
                            &mut user_property_bytes,
                        )?,
                        0x0b => return Err(SubscriptionIdentifierDuplicate.into()),
                        _ => {
                            return Err(SubscriptionPropertyMalformed.into());
                        }
                    }
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
                    if topic.as_str().starts_with("$share/")
                        && super::topic::shared_inner(topic.as_str()).is_none()
                    {
                        return Err("invalid MQTT 5 shared subscription filter".into());
                    }
                    if options & 0xc0 != 0 {
                        return Err("reserved MQTT 5 SUBSCRIBE option bit".into());
                    }
                    let handling = (options >> 4) & 0x03;
                    if handling == 3 {
                        return Err("invalid MQTT 5 Retain Handling value".into());
                    }
                    if options & 0x04 != 0 && topic.as_str().starts_with("$share/") {
                        return Err("No Local invalid on shared subscription".into());
                    }
                    handling
                } else {
                    0
                };
                // MQTT-3-8.3-4: QoS 3 and reserved option bits are malformed.
                let qos = Qos::from_u8(if mqtt5 { options & 0x03 } else { options })?;
                filters.push((topic, qos, retain_handling, options & 0x0c));
            }
            if filters.is_empty() {
                return Err("empty SUBSCRIBE".into());
            }
            Packet::Subscribe {
                packet_id,
                filters,
                subscription_identifier,
            }
        }
        0xa2 => {
            let packet_id = c.word()?;
            if packet_id == 0 {
                return Err("zero UNSUBSCRIBE packet id".into());
            }
            if mqtt5 {
                let property_length = c.variable_integer()?;
                let raw = c.bytes(property_length)?;
                let mut properties = Cursor::new(raw);
                let mut user_property_count = 0;
                let mut user_property_bytes = 0;
                while properties.pos < raw.len() {
                    match properties.byte()? {
                        0x26 => parse_subscription_user_property(
                            &mut properties,
                            &mut user_property_count,
                            &mut user_property_bytes,
                        )?,
                        _ => return Err(SubscriptionPropertyMalformed.into()),
                    }
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
                                return Err(TopicAliasInvalid.into());
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
        0x40 => {
            let (packet_id, reason_code) = decode_client_publish_ack(&mut c, mqtt5)?;
            Packet::PubAck {
                packet_id,
                reason_code,
            }
        }
        0x50 => {
            let (packet_id, reason_code) = decode_client_publish_ack(&mut c, mqtt5)?;
            Packet::PubRec {
                packet_id,
                reason_code,
            }
        }
        // MQTT-3.6.1-1: PUBREL low nibble must be 0010.
        0x62 => {
            let (packet_id, reason_code) = decode_qos2_completion_ack(&mut c, mqtt5)?;
            Packet::PubRel {
                packet_id,
                reason_code,
            }
        }
        0x70 => {
            let (packet_id, reason_code) = decode_qos2_completion_ack(&mut c, mqtt5)?;
            Packet::PubComp {
                packet_id,
                reason_code,
            }
        }
        0xc0 if body.is_empty() => Packet::PingReq,
        0xf0 if mqtt5 => {
            if c.byte()? != 0x19 {
                return Err("unsupported MQTT 5 AUTH reason code".into());
            }
            let property_length = c.variable_integer()?;
            let mut properties = Cursor::new(c.bytes(property_length)?);
            let mut method = None;
            let mut data = None;
            let mut reason_seen = false;
            while properties.pos < properties.input.len() {
                match properties.byte()? {
                    0x15 if method.is_none() => method = Some(properties.text()?),
                    0x16 if data.is_none() => data = Some(properties.binary()?.to_vec()),
                    0x1f if !reason_seen => {
                        let _ = properties.text()?;
                        reason_seen = true;
                    }
                    0x26 => {
                        let _ = properties.text()?;
                        let _ = properties.text()?;
                    }
                    _ => return Err("duplicate or unsupported MQTT 5 AUTH property".into()),
                }
            }
            let method = method.ok_or("MQTT 5 AUTH missing Authentication Method")?;
            let data = data.ok_or("MQTT 5 AUTH missing Authentication Data")?;
            Packet::Auth { method, data }
        }
        0xe0 => {
            let reason_code = if mqtt5 && c.pos < c.input.len() {
                c.byte()?
            } else {
                0
            };
            if !matches!(reason_code, 0x00 | 0x04 | 0x80..=0x83 | 0x90 | 0x93..=0x99) {
                return Err("MQTT 5 DISCONNECT reason outside supported subset".into());
            }
            let mut expiry_interval = None;
            if mqtt5 && c.pos < c.input.len() {
                let length = c.variable_integer()?;
                let mut properties = Cursor::new(c.bytes(length)?);
                let mut reason_seen = false;
                while properties.pos < properties.input.len() {
                    match properties.byte()? {
                        0x11 if expiry_interval.is_none() => {
                            expiry_interval =
                                Some(u32::from_be_bytes(properties.bytes(4)?.try_into().unwrap()));
                        }
                        0x1f if !reason_seen => {
                            let _ = properties.text()?;
                            reason_seen = true;
                        }
                        0x26 => {
                            let _ = properties.text()?;
                            let _ = properties.text()?;
                        }
                        _ => {
                            return Err(
                                "duplicate or unsupported MQTT 5 DISCONNECT property".into()
                            );
                        }
                    }
                }
            }
            Packet::Disconnect {
                reason_code,
                expiry_interval,
            }
        }
        _ => return Err("unsupported MQTT packet type or flags".into()),
    };
    c.end()?;
    Ok(packet)
}

fn parse_subscription_user_property(
    properties: &mut Cursor<'_>,
    count: &mut usize,
    bytes: &mut usize,
) -> Result<(), &'static str> {
    let key = properties.text()?;
    let value = properties.text()?;
    if key.len() > 256 || value.len() > 256 {
        return Err("MQTT 5 subscription User Property field too long");
    }
    *count += 1;
    *bytes = bytes.saturating_add(5 + key.len() + value.len());
    if *count > 16 || *bytes > 2048 {
        return Err("MQTT 5 subscription User Properties exceed limits");
    }
    Ok(())
}

fn nonzero_ack_id(c: &mut Cursor<'_>) -> Result<u16, &'static str> {
    let id = c.word()?;
    if id == 0 {
        return Err("zero acknowledgment packet id");
    }
    Ok(id)
}

fn decode_client_publish_ack(c: &mut Cursor<'_>, mqtt5: bool) -> Result<(u16, u8), &'static str> {
    let packet_id = nonzero_ack_id(c)?;
    let reason_code = if mqtt5 && c.pos < c.input.len() {
        c.byte()?
    } else {
        0
    };
    if !matches!(
        reason_code,
        0x00 | 0x80 | 0x83 | 0x87 | 0x90 | 0x91 | 0x97 | 0x99
    ) {
        return Err("invalid client PUBLISH acknowledgment reason code");
    }
    if mqtt5 && c.pos < c.input.len() {
        let property_length = c.variable_integer()?;
        let mut properties = Cursor::new(c.bytes(property_length)?);
        let mut reason_seen = false;
        while properties.pos < properties.input.len() {
            match properties.byte()? {
                0x1f if !reason_seen => {
                    let _ = properties.text()?;
                    reason_seen = true;
                }
                0x26 => {
                    let _ = properties.text()?;
                    let _ = properties.text()?;
                }
                _ => return Err("duplicate or unsupported MQTT 5 PUBLISH acknowledgment property"),
            }
        }
    }
    Ok((packet_id, reason_code))
}

fn decode_qos2_completion_ack(c: &mut Cursor<'_>, mqtt5: bool) -> Result<(u16, u8), &'static str> {
    let packet_id = nonzero_ack_id(c)?;
    let reason_code = if mqtt5 && c.pos < c.input.len() {
        c.byte()?
    } else {
        0
    };
    if !matches!(reason_code, 0x00 | 0x92) {
        return Err("invalid MQTT 5 QoS 2 completion reason code");
    }
    if mqtt5 && c.pos < c.input.len() {
        let property_length = c.variable_integer()?;
        let mut properties = Cursor::new(c.bytes(property_length)?);
        let mut reason_seen = false;
        while properties.pos < properties.input.len() {
            match properties.byte()? {
                0x1f if !reason_seen => {
                    let _ = properties.text()?;
                    reason_seen = true;
                }
                0x26 => {
                    let _ = properties.text()?;
                    let _ = properties.text()?;
                }
                _ => return Err("duplicate or unsupported MQTT 5 QoS 2 completion property"),
            }
        }
    }
    Ok((packet_id, reason_code))
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
pub(super) fn encode_mqtt5_plain_auth_success() -> [u8; 12] {
    [
        0xf0, 0x0a, 0x00, 0x08, 0x15, 0x00, 0x05, b'P', b'L', b'A', b'I', b'N',
    ]
}
pub(super) fn encode_mqtt5_auth_failure_disconnect() -> [u8; 4] {
    [0xe0, 0x02, 0x86, 0x00]
}
pub(super) fn encode_mqtt5_shared_available_connack(session_present: bool) -> [u8; 7] {
    [0x20, 0x05, u8::from(session_present), 0, 2, 0x2a, 1]
}
pub(super) fn encode_mqtt5_success_connack(session_present: bool) -> [u8; 12] {
    // Maximum QoS absent means 2; Maximum Packet Size=65536 (0x27).
    [
        0x20,
        0x0a,
        u8::from(session_present),
        0x00,
        0x07,
        0x27,
        0,
        1,
        0,
        0,
        0x2a,
        1,
    ]
}
pub(super) fn encode_mqtt5_alias_connack(session_present: bool) -> [u8; 15] {
    // The server accepts only inbound aliases 1..=16 for this connection.
    [
        0x20,
        0x0d,
        u8::from(session_present),
        0,
        0x0a,
        0x27,
        0,
        1,
        0,
        0,
        0x22,
        0,
        MAX_TOPIC_ALIAS,
        0x2a,
        1,
    ]
}

pub(super) fn append_mqtt5_plain_method(mut connack: Vec<u8>) -> Vec<u8> {
    // All success CONNACK variants in this subset use one-byte lengths.
    connack[1] += 8;
    connack[4] += 8;
    connack.extend_from_slice(&[0x15, 0, 5, b'P', b'L', b'A', b'I', b'N']);
    connack
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

pub(super) fn append_mqtt5_server_keep_alive(mut connack: Vec<u8>, seconds: u16) -> Vec<u8> {
    // Success CONNACKs in this subset have one-byte Remaining/Property Lengths.
    debug_assert_eq!(connack[0], 0x20);
    debug_assert_ne!(seconds, 0);
    connack[1] += 3;
    connack[4] += 3;
    connack.push(0x13);
    connack.extend_from_slice(&seconds.to_be_bytes());
    connack
}

pub(super) fn append_mqtt5_assigned_client_id(mut connack: Vec<u8>, id: &str) -> Vec<u8> {
    // Generated IDs are fixed-length ASCII; the resulting CONNACK lengths
    // remain one-byte Variable Byte Integers in this bounded subset.
    debug_assert!(!id.is_empty() && id.len() <= 37);
    let added = 3 + id.len();
    connack[1] += u8::try_from(added).expect("bounded assigned ID");
    connack[4] += u8::try_from(added).expect("bounded assigned ID");
    connack.push(0x12);
    connack.extend_from_slice(
        &u16::try_from(id.len())
            .expect("bounded assigned ID")
            .to_be_bytes(),
    );
    connack.extend_from_slice(id.as_bytes());
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

#[cfg(test)]
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
    encode_publish_with_subscription_ids(
        topic,
        payload,
        qos,
        retain,
        dup,
        packet_id,
        mqtt5,
        expiry_interval,
        alias_mode,
        payload_format_indicator,
        content_type,
        response_topic,
        correlation_data,
        user_properties,
        &[],
    )
}

#[allow(clippy::too_many_arguments, clippy::too_many_lines)] // One packet boundary validates all MQTT 5 PUBLISH properties and size limits.
pub(super) fn encode_publish_with_subscription_ids(
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
    subscription_identifiers: &[u32],
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
        || !user_properties.is_empty()
        || !subscription_identifiers.is_empty())
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
    if subscription_identifiers.len() > MAX_SUBSCRIPTIONS
        || subscription_identifiers
            .iter()
            .any(|id| !(1..=268_435_455).contains(id))
    {
        return Err("invalid outbound MQTT 5 Subscription Identifier");
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
        + user_property_bytes
        + subscription_identifiers
            .iter()
            .map(|id| {
                let mut encoded = Vec::new();
                encode_length(*id as usize, &mut encoded);
                1 + encoded.len()
            })
            .sum::<usize>();
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
        for id in subscription_identifiers {
            out.push(0x0b);
            encode_length(*id as usize, &mut out);
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
        assert!(
            decode_for(0x30, &[0, 1, b'a', 3, 0x23, 0, 0, b'x'], true)
                .unwrap_err()
                .is::<TopicAliasInvalid>()
        );
        assert!(publish(&[0, 1, b'a', 6, 0x23, 0, 1, 0x23, 0, 1]).is_err());
        assert!(publish(&[0, 0, 0, b'x']).is_err());
        drop(publish);
        reader.set_mqtt5(u16::from(MAX_TOPIC_ALIAS));
        reader
            .buffer
            .extend_from_slice(&[0x30, 7, 0, 0, 3, 0x23, 0, 1, b'y']);
        assert!(
            reader
                .try_take_packet()
                .unwrap_err()
                .is::<TopicAliasInvalid>()
        );
        assert_eq!(
            encode_mqtt5_alias_connack(false),
            [0x20, 0x0d, 0, 0, 10, 0x27, 0, 1, 0, 0, 0x22, 0, 16, 0x2a, 1]
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
        assert!(matches!(
            decode(0x10, &duplicate).unwrap(),
            Packet::UnsupportedConnect5 {
                reason_code: 0x82,
                maximum_packet_size: None,
            }
        ));
        let mut truncated = body;
        truncated[14] = 4;
        assert!(decode(0x10, &truncated).is_err());
    }

    #[test]
    fn mqtt5_will_metadata_preserves_order_and_rejects_invalid_properties() {
        let make_connect = |properties: &[u8]| {
            let mut body = vec![
                0,
                4,
                b'M',
                b'Q',
                b'T',
                b'T',
                5,
                6,
                0,
                30,
                0,
                0,
                1,
                b'a',
                u8::try_from(properties.len()).unwrap(),
            ];
            body.extend_from_slice(properties);
            body.extend([0, 1, b't', 0, 1, b'x']);
            body
        };
        let properties = [
            0x26, 0, 1, b'k', 0, 1, b'1', 0x09, 0, 2, 0, 0xff, 0x18, 0, 0, 0, 2, 0x03, 0, 4, b't',
            b'e', b'x', b't', 0x26, 0, 1, b'k', 0, 1, b'2', 0x08, 0, 7, b'r', b'e', b'p', b'l',
            b'y', b'/', b't', 0x01, 1,
        ];
        assert!(matches!(
            decode(0x10, &make_connect(&properties)).unwrap(),
            Packet::Connect { will_delay_seconds: 2, will: Some(will), .. }
                if will.payload_format_indicator == Some(1)
                    && will.content_type.as_deref() == Some("text")
                    && will.response_topic.as_ref().map(TopicName::as_str) == Some("reply/t")
                    && will.correlation_data.as_deref() == Some(&[0, 0xff][..])
                    && will.user_properties == [("k".to_owned(), "1".to_owned()),
                                                ("k".to_owned(), "2".to_owned())]
        ));
        assert!(matches!(
            decode(0x10, &make_connect(&[0x21])).unwrap(),
            Packet::UnsupportedConnect5 {
                reason_code: 0x81,
                maximum_packet_size: None,
            }
        ));
        for invalid in [
            vec![0x01, 2],
            vec![0x01, 1, 0x01, 0],
            vec![0x18, 0, 0, 0, 1, 0x18, 0, 0, 0, 2],
            vec![0x02, 0, 0, 0, 1, 0x02, 0, 0, 0, 2],
            vec![0x03, 0, 1, b'a', 0x03, 0, 1, b'b'],
            vec![0x08, 0, 1, b'a', 0x08, 0, 1, b'b'],
            vec![0x09, 0, 1, b'a', 0x09, 0, 1, b'b'],
        ] {
            assert!(matches!(
                decode(0x10, &make_connect(&invalid)).unwrap(),
                Packet::UnsupportedConnect5 {
                    reason_code: 0x82,
                    maximum_packet_size: None,
                }
            ));
        }
        for malformed in [
            vec![0x02, 0, 0, 0],
            vec![0x08, 0, 1, b'#'],
            vec![0x09, 0, 2, 0],
        ] {
            assert!(
                decode(0x10, &make_connect(&malformed)).is_err(),
                "{malformed:?}"
            );
        }
        assert!(matches!(
            decode(0x10, &make_connect(&[0x02, 0, 0, 0, 1])).unwrap(),
            Packet::Connect {
                will_message_expiry_seconds: Some(1),
                ..
            }
        ));
        assert!(matches!(
            decode(0x10, &make_connect(&[0x02, 0, 0, 0, 0])).unwrap(),
            Packet::Connect {
                will_message_expiry_seconds: Some(0),
                ..
            }
        ));
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
            encode_mqtt5_shared_available_connack(false),
            [0x20, 5, 0, 0, 2, 0x2a, 1]
        );
        assert_eq!(
            encode_mqtt5_success_connack(false),
            [0x20, 10, 0, 0, 7, 0x27, 0, 1, 0, 0, 0x2a, 1]
        );
        assert_eq!(encode_mqtt5_success_connack(true)[2], 1);
        assert_eq!(
            append_mqtt5_receive_maximum(encode_mqtt5_alias_connack(true).to_vec(), 1),
            [
                0x20, 0x10, 1, 0, 0x0d, 0x27, 0, 1, 0, 0, 0x22, 0, 16, 0x2a, 1, 0x21, 0, 1
            ]
        );
        assert_eq!(
            append_mqtt5_receive_maximum(encode_mqtt5_connack(0).to_vec(), 32),
            [0x20, 6, 0, 0, 3, 0x21, 0, 32]
        );
        assert_eq!(
            append_mqtt5_server_keep_alive(
                encode_mqtt5_shared_available_connack(false).to_vec(),
                60
            ),
            [0x20, 8, 0, 0, 5, 0x2a, 1, 0x13, 0, 60]
        );
    }

    #[test]
    fn mqtt5_assigned_client_id_is_mandatory_connack_property() {
        assert_eq!(
            append_mqtt5_assigned_client_id(
                encode_mqtt5_shared_available_connack(false).to_vec(),
                "xmqr-ab"
            ),
            [
                0x20, 15, 0, 0, 12, 0x2a, 1, 0x12, 0, 7, b'x', b'm', b'q', b'r', b'-', b'a', b'b'
            ]
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
            &[0, 1, 0][..],                      // No filters.
        ] {
            assert!(decode_for(0x82, body, true).is_err());
        }
    }

    #[test]
    fn mqtt5_subscription_identifier_codec_accepts_one_and_rejects_invalid_properties() {
        assert!(matches!(
            decode_for(0x82, &[0, 1, 2, 0x0b, 17, 0, 1, b'x', 1], true).unwrap(),
            Packet::Subscribe {
                subscription_identifier: Some(17),
                ..
            }
        ));
        for properties in [&[0x0b, 0][..], &[0x0b, 17, 0x0b, 18][..], &[0x0b][..]] {
            let mut body = vec![0, 1, u8::try_from(properties.len()).unwrap()];
            body.extend_from_slice(properties);
            body.extend_from_slice(&[0, 1, b'x', 0]);
            assert!(decode_for(0x82, &body, true).is_err());
        }
        assert!(decode_for(0x30, &[0, 1, b'x', 2, 0x0b, 17, b'y'], true).is_err());
        let encoded = encode_publish_with_subscription_ids(
            "x",
            b"y",
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
            &[],
            &[17, 17],
        )
        .unwrap();
        assert_eq!(encoded, [0x30, 9, 0, 1, b'x', 4, 0x0b, 17, 0x0b, 17, b'y']);
        assert!(
            encode_publish_with_subscription_ids(
                "x",
                b"y",
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
                &[],
                &[0],
            )
            .is_err()
        );
        assert!(
            encode_publish_with_subscription_ids(
                "x",
                b"y",
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
                &[],
                &vec![17; MAX_SUBSCRIPTIONS + 1],
            )
            .is_err()
        );
        assert!(
            encode_publish_with_subscription_ids(
                "x",
                b"y",
                Qos::AtMostOnce,
                false,
                false,
                None,
                false,
                None,
                TopicAliasMode::None,
                None,
                None,
                None,
                None,
                &[],
                &[17],
            )
            .is_err()
        );
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
        for flags in [0x04, 0x08, 0x0c] {
            assert!(matches!(
                decode_for(0x82, &[0, 1, 0, 0, 1, b'x', flags], true).unwrap(),
                Packet::Subscribe { filters, .. } if filters[0].3 == flags
            ));
        }
        for invalid in [0x30, 0x40, 0x80] {
            assert!(decode_for(0x82, &[0, 1, 0, 0, 1, b'x', invalid], true).is_err());
        }
        assert!(
            decode_for(
                0x82,
                &[
                    0, 1, 0, 0, 8, b'$', b's', b'h', b'a', b'r', b'e', b'/', b'x', 4
                ],
                true
            )
            .is_err()
        );
        assert!(decode_for(0x82, &[0, 1, 0, 1, b'x', 0x20], false).is_err());
    }

    #[test]
    fn mqtt5_shared_filter_requires_group_inner_filter_and_no_local_clear() {
        for valid in ["$share/g/test/#", "$share/grupo/+/value"] {
            let mut body = vec![0, 1, 0];
            body.extend_from_slice(&u16::try_from(valid.len()).unwrap().to_be_bytes());
            body.extend_from_slice(valid.as_bytes());
            body.push(2);
            assert!(matches!(
                decode_for(0x82, &body, true),
                Ok(Packet::Subscribe { .. })
            ));
            *body.last_mut().unwrap() = 0x06;
            assert!(decode_for(0x82, &body, true).is_err());
        }
        for invalid in [
            "$share//test/#",
            "$share/g/",
            "$share/+/test",
            "$share/g/test/#/tail",
        ] {
            let mut body = vec![0, 1, 0];
            body.extend_from_slice(&u16::try_from(invalid.len()).unwrap().to_be_bytes());
            body.extend_from_slice(invalid.as_bytes());
            body.push(0);
            assert!(decode_for(0x82, &body, true).is_err(), "{invalid}");
        }
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
    fn mqtt5_subscription_user_properties_are_contextual_bounded_and_repeatable() {
        fn body(properties: &[u8], subscribe: bool) -> Vec<u8> {
            let mut out = vec![0, 7];
            encode_length(properties.len(), &mut out);
            out.extend_from_slice(properties);
            out.extend_from_slice(&[0, 1, b'x']);
            if subscribe {
                out.push(1);
            }
            out
        }
        let pair = [0x26, 0, 1, b'k', 0, 1, b'v'];
        let mut repeated = Vec::new();
        repeated.extend_from_slice(&pair);
        repeated.extend_from_slice(&[0x0b, 3]);
        repeated.extend_from_slice(&pair);
        assert!(matches!(
            decode_for(0x82, &body(&repeated, true), true).unwrap(),
            Packet::Subscribe {
                subscription_identifier: Some(3),
                ..
            }
        ));
        assert!(matches!(
            decode_for(0xa2, &body(&repeated[..7], false), true).unwrap(),
            Packet::Unsubscribe { .. }
        ));
        for (header, subscribe) in [(0x82, true), (0xa2, false)] {
            assert!(decode_for(header, &body(&pair, subscribe), false).is_err());
            for invalid in [
                vec![0x26, 0, 1, b'k', 0, 2, b'v'],
                vec![0x26, 0, 1, 0xff, 0, 0],
                vec![0x1f, 0, 0],
                pair.repeat(17),
            ] {
                assert!(decode_for(header, &body(&invalid, subscribe), true).is_err());
            }
            let mut too_long = vec![0x26, 1, 1];
            too_long.extend_from_slice(&vec![b'k'; 257]);
            too_long.extend_from_slice(&[0, 0]);
            assert!(decode_for(header, &body(&too_long, subscribe), true).is_err());
            let mut large_pair = vec![0x26, 0, 128];
            large_pair.extend_from_slice(&[b'k'; 128]);
            large_pair.extend_from_slice(&[0, 128]);
            large_pair.extend_from_slice(&[b'v'; 128]);
            assert!(decode_for(header, &body(&large_pair.repeat(8), subscribe), true).is_err());
        }
    }

    #[test]
    fn mqtt5_subscription_property_errors_have_distinct_reason_classes() {
        for (header, body) in [
            (0x82, &[0, 1, 1, 0x09, 0, 1, b'x', 0][..]),
            (0xa2, &[0, 1, 1, 0x0b, 0, 1, b'x'][..]),
        ] {
            assert!(
                decode_for(header, body, true)
                    .unwrap_err()
                    .is::<SubscriptionPropertyMalformed>()
            );
        }
        assert!(
            decode_for(0x82, &[0, 1, 4, 0x0b, 1, 0x0b, 2, 0, 1, b'x', 0], true)
                .unwrap_err()
                .is::<SubscriptionIdentifierDuplicate>()
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
            Ok(Packet::PubRec {
                packet_id: 7,
                reason_code: 0
            })
        ));
        assert!(matches!(
            decode_for(0x62, &[0, 7], true),
            Ok(Packet::PubRel {
                packet_id: 7,
                reason_code: 0
            })
        ));
        assert!(matches!(
            decode_for(0x70, &[0, 7], true),
            Ok(Packet::PubComp {
                packet_id: 7,
                reason_code: 0
            })
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
    fn mqtt5_accepts_qos2_completion_reasons_and_diagnostics() {
        for header in [0x62, 0x70] {
            let diagnostic = [
                0, 7, 0x92, 12, 0x1f, 0, 2, b'n', b'o', 0x26, 0, 1, b'k', 0, 1, b'v',
            ];
            for body in [
                &[0, 7][..],
                &[0, 7, 0][..],
                &[0, 7, 0, 0][..],
                &[0, 7, 0x92][..],
                &[0, 7, 0x92, 0][..],
                &diagnostic[..],
            ] {
                assert!(decode_for(header, body, true).is_ok(), "header {header:#x}");
            }
            for body in [
                &[0, 0][..],
                &[0, 7, 0x80][..],
                &[0, 7, 0, 1][..],
                &[0, 7, 0, 0, 0][..],
                &[0, 7, 0x92, 1, 0x11][..],
                &[0, 7, 0x92, 1, 0x1f][..],
                &[0, 7, 0x92, 8, 0x1f, 0, 1, b'a', 0x1f, 0, 1, b'b'][..],
            ] {
                assert!(
                    decode_for(header, body, true).is_err(),
                    "header {header:#x}"
                );
            }
            assert!(decode_for(header, &[0, 7, 0], false).is_err());
        }
        assert!(matches!(
            decode_for(0x62, &[0, 7, 0x92], true),
            Ok(Packet::PubRel {
                packet_id: 7,
                reason_code: 0x92
            })
        ));
        assert!(matches!(
            decode_for(0x70, &[0, 7, 0x92], true),
            Ok(Packet::PubComp {
                packet_id: 7,
                reason_code: 0x92
            })
        ));
        for body in [&[][..], &[0][..], &[0, 0][..]] {
            assert!(matches!(
                decode_for(0xe0, body, true),
                Ok(Packet::Disconnect {
                    expiry_interval: None,
                    ..
                })
            ));
        }
        for body in [&[0x87][..], &[0, 1][..], &[0, 0, 0][..]] {
            assert!(decode_for(0xe0, body, true).is_err());
        }
        assert!(decode_for(0xe0, &[0], false).is_err());
    }

    #[test]
    fn mqtt5_puback_accepts_client_rejections_and_strict_diagnostic_properties() {
        for reason in [0, 0x80, 0x83, 0x87, 0x90, 0x91, 0x97, 0x99] {
            assert!(matches!(
                decode_for(0x40, &[0, 7, reason], true),
                Ok(Packet::PubAck { packet_id: 7, reason_code }) if reason_code == reason
            ));
        }
        for body in [&[0, 7][..], &[0, 7, 0][..], &[0, 7, 0, 0][..]] {
            assert!(matches!(
                decode_for(0x40, body, true),
                Ok(Packet::PubAck {
                    packet_id: 7,
                    reason_code: 0
                })
            ));
        }
        assert!(matches!(
            decode_for(0x40, &[0, 7, 0x80, 5, 0x1f, 0, 2, b'n', b'o'], true),
            Ok(Packet::PubAck {
                packet_id: 7,
                reason_code: 0x80
            })
        ));
        assert!(matches!(
            decode_for(0x40, &[0, 7, 0x87, 7, 0x26, 0, 1, b'k', 0, 1, b'v'], true),
            Ok(Packet::PubAck {
                packet_id: 7,
                reason_code: 0x87
            })
        ));
        for body in [
            &[0, 0][..],
            &[0, 7, 0x10][..],
            &[0, 7, 0x81][..],
            &[0, 7, 0x80, 1, 0x11][..],
            &[0, 7, 0x80, 1, 0x1f][..],
            &[0, 7, 0x80, 6, 0x1f, 0, 0, 0x1f, 0, 0][..],
            &[0, 7, 0x80, 0, 0][..],
        ] {
            assert!(decode_for(0x40, body, true).is_err(), "{body:?}");
        }
        assert!(decode_for(0x40, &[0, 7, 0x80], false).is_err());
    }

    #[test]
    fn mqtt5_pubrec_accepts_client_rejections_and_strict_diagnostic_properties() {
        for reason in [0, 0x80, 0x83, 0x87, 0x90, 0x91, 0x97, 0x99] {
            assert!(matches!(
                decode_for(0x50, &[0, 7, reason], true),
                Ok(Packet::PubRec { packet_id: 7, reason_code }) if reason_code == reason
            ));
        }
        for body in [&[0, 7][..], &[0, 7, 0][..], &[0, 7, 0, 0][..]] {
            assert!(matches!(
                decode_for(0x50, body, true),
                Ok(Packet::PubRec {
                    packet_id: 7,
                    reason_code: 0
                })
            ));
        }
        assert!(matches!(
            decode_for(0x50, &[0, 7, 0x80, 5, 0x1f, 0, 2, b'n', b'o'], true),
            Ok(Packet::PubRec {
                packet_id: 7,
                reason_code: 0x80
            })
        ));
        assert!(matches!(
            decode_for(0x50, &[0, 7, 0x87, 7, 0x26, 0, 1, b'k', 0, 1, b'v'], true),
            Ok(Packet::PubRec {
                packet_id: 7,
                reason_code: 0x87
            })
        ));
        for body in [
            &[0, 0][..],
            &[0, 7, 0x10][..],
            &[0, 7, 0x81][..],
            &[0, 7, 0x80, 1, 0x11][..],
            &[0, 7, 0x80, 1, 0x1f][..],
            &[0, 7, 0x80, 6, 0x1f, 0, 0, 0x1f, 0, 0][..],
            &[0, 7, 0x80, 0, 0][..],
        ] {
            assert!(decode_for(0x50, body, true).is_err(), "{body:?}");
        }
        assert!(decode_for(0x50, &[0, 7, 0x80], false).is_err());
    }

    #[test]
    fn mqtt5_disconnect_session_expiry_property_is_strict() {
        assert!(matches!(
            decode_for(0xe0, &[4], true),
            Ok(Packet::Disconnect {
                reason_code: 4,
                expiry_interval: None
            })
        ));
        let diagnostics = [4, 12, 0x1f, 0, 2, b'n', b'o', 0x26, 0, 1, b'k', 0, 1, b'v'];
        assert!(matches!(
            decode_for(0xe0, &diagnostics, true),
            Ok(Packet::Disconnect {
                reason_code: 4,
                expiry_interval: None
            })
        ));
        let mut with_expiry = vec![4, 17, 0x11, 0, 0, 0, 2];
        with_expiry.extend_from_slice(&diagnostics[2..]);
        assert!(matches!(
            decode_for(0xe0, &with_expiry, true),
            Ok(Packet::Disconnect {
                reason_code: 4,
                expiry_interval: Some(2)
            })
        ));
        assert!(matches!(
            decode_for(0xe0, &[0, 5, 0x11, 0, 0, 0, 2], true).unwrap(),
            Packet::Disconnect {
                expiry_interval: Some(2),
                ..
            }
        ));
        assert!(matches!(
            decode_for(0xe0, &[0, 5, 0x11, 0xff, 0xff, 0xff, 0xff], true).unwrap(),
            Packet::Disconnect {
                expiry_interval: Some(u32::MAX),
                ..
            }
        ));
        for invalid in [
            &[0x87][..],
            &[0, 5, 0x11, 0, 0][..],
            &[0, 1, 0x26][..],
            &[0, 10, 0x11, 0, 0, 0, 1, 0x11, 0, 0, 0, 2][..],
            &[4, 8, 0x1f, 0, 1, b'a', 0x1f, 0, 1, b'b'][..],
            &[4, 2, 0x26, 0][..],
        ] {
            assert!(decode_for(0xe0, invalid, true).is_err(), "{invalid:?}");
        }
        assert!(decode_for(0xe0, &[0, 0], false).is_err());
    }

    #[test]
    fn mqtt5_disconnect_accepts_client_reasons_only() {
        for reason in [
            0x00, 0x04, 0x80, 0x81, 0x82, 0x83, 0x90, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99,
        ] {
            assert!(
                matches!(decode_for(0xe0, &[reason], true), Ok(Packet::Disconnect { reason_code, expiry_interval: None }) if reason_code == reason)
            );
            assert!(
                matches!(decode_for(0xe0, &[reason, 0], true), Ok(Packet::Disconnect { reason_code, expiry_interval: None }) if reason_code == reason)
            );
        }
        for reason in [
            0x01, 0x10, 0x84, 0x87, 0x89, 0x8b, 0x8d, 0x8e, 0x8f, 0x9a, 0x9b, 0x9c, 0x9d, 0x9e,
            0x9f, 0xa0, 0xa1, 0xa2, 0xff,
        ] {
            assert!(decode_for(0xe0, &[reason], true).is_err(), "{reason:#x}");
        }
        assert!(decode_for(0xe0, &[0x80], false).is_err());
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
                topic_alias_maximum: 0,
                ..
            }
        ));
        assert!(matches!(
            mqtt5_connect_properties_supported(&[0x11, 255, 255, 255, 255]).unwrap(),
            Mqtt5ConnectProperties::Supported {
                expiry: u32::MAX,
                receive_maximum: u16::MAX,
                maximum_packet_size: None,
                topic_alias_maximum: 0,
                ..
            }
        ));
        assert!(matches!(
            mqtt5_connect_properties_supported(&[0x11, 0, 0, 0, 1]).unwrap(),
            Mqtt5ConnectProperties::Supported {
                expiry: 1,
                receive_maximum: u16::MAX,
                maximum_packet_size: None,
                topic_alias_maximum: 0,
                ..
            }
        ));
        for semantic in [&[0x21, 0, 0][..], &[0x21, 0, 20, 0x21, 0, 5][..]] {
            assert_eq!(
                mqtt5_connect_properties_supported(semantic).unwrap(),
                rejected_connect_property(None, 0x82)
            );
        }
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
        for semantic in [
            &[0x17, 2][..],
            &[0x17, 0, 0x17, 1][..],
            &[0x19, 2][..],
            &[0x19, 0, 0x19, 1][..],
            &[0x22, 0, 0, 0x22, 0, 1][..],
        ] {
            assert_eq!(
                mqtt5_connect_properties_supported(semantic).unwrap(),
                rejected_connect_property(None, 0x82)
            );
        }
        for malformed in [
            &[0x22, 0][..],
            &[0x26, 0, 1, 0xff, 0, 1, b'b'][..],
            &[0x26, 0, 1, b'a', 0, 2, b'b'][..],
        ] {
            assert!(mqtt5_connect_properties_supported(malformed).is_err());
        }
    }

    #[test]
    fn mqtt5_publish_and_subscribe_property_contexts_are_separate() {
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
        assert_eq!(
            mqtt5_connect_properties_supported(&[0x0b, 1]).unwrap(),
            Mqtt5ConnectProperties::Unsupported {
                maximum_packet_size: None,
                reason_code: 0x81,
            }
        );
        assert!(matches!(
            mqtt5_connect_properties_supported(&[0x27, 0, 0, 0, 10]).unwrap(),
            Mqtt5ConnectProperties::Supported {
                expiry: 0,
                receive_maximum: u16::MAX,
                maximum_packet_size: Some(10),
                topic_alias_maximum: 0,
                ..
            }
        ));
        assert_eq!(
            mqtt5_connect_properties_supported(&[0x27, 0, 0, 0, 1, 0x99]).unwrap(),
            Mqtt5ConnectProperties::Unsupported {
                maximum_packet_size: Some(1),
                reason_code: 0x81
            }
        );
        assert_eq!(
            mqtt5_connect_properties_supported(&[0x27, 0, 0, 0, 0]).unwrap(),
            rejected_connect_property(None, 0x82)
        );
        assert!(mqtt5_connect_properties_supported(&[0x27, 0, 0, 0]).is_err());
        assert_eq!(
            mqtt5_connect_properties_supported(&[0x27, 0, 0, 0, 10, 0x27, 0, 0, 0, 5]).unwrap(),
            rejected_connect_property(Some(10), 0x82)
        );
    }

    #[test]
    fn mqtt5_auth_method_is_refused_distinctly_after_validating_properties() {
        for properties in [
            vec![0x15, 0, 1, b'x'],
            vec![0x16, 0, 2, 0, 255, 0x15, 0, 1, b'x', 0x27, 0, 0, 0, 5],
        ] {
            let expected_maximum = if properties.len() > 4 { Some(5) } else { None };
            assert_eq!(
                mqtt5_connect_properties_supported(&properties).unwrap(),
                Mqtt5ConnectProperties::Unsupported {
                    maximum_packet_size: expected_maximum,
                    reason_code: 0x8c,
                }
            );
        }
        for semantic in [
            vec![0x16, 0, 1, 42],
            vec![0x15, 0, 1, b'x', 0x15, 0, 1, b'y'],
            vec![0x15, 0, 1, b'x', 0x16, 0, 0, 0x16, 0, 0],
        ] {
            assert_eq!(
                mqtt5_connect_properties_supported(&semantic).unwrap(),
                rejected_connect_property(None, 0x82)
            );
        }
        for malformed in [vec![0x15, 0, 2, b'x'], vec![0x15, 0, 1, 0xff]] {
            assert!(mqtt5_connect_properties_supported(&malformed).is_err());
        }
    }

    #[test]
    fn mqtt5_connect_semantic_property_errors_have_protocol_reason() {
        for invalid in [
            &[0x11, 0, 0, 0, 1, 0x11, 0, 0, 0, 2][..],
            &[0x21, 0, 0][..],
            &[0x21, 0, 1, 0x21, 0, 2][..],
            &[0x27, 0, 0, 0, 0][..],
            &[0x27, 0, 0, 0, 5, 0x27, 0, 0, 0, 6][..],
            &[0x17, 2][..],
            &[0x17, 0, 0x17, 1][..],
            &[0x19, 2][..],
            &[0x19, 0, 0x19, 1][..],
            &[0x22, 0, 1, 0x22, 0, 2][..],
            &[0x15, 0, 1, b'a', 0x15, 0, 1, b'b'][..],
            &[0x16, 0, 1, b'a', 0x16, 0, 1, b'b'][..],
            &[0x16, 0, 1, b'a'][..],
        ] {
            assert!(
                matches!(
                    mqtt5_connect_properties_supported(invalid).unwrap(),
                    Mqtt5ConnectProperties::Unsupported {
                        reason_code: 0x82,
                        ..
                    }
                ),
                "{invalid:?}"
            );
        }
    }

    #[test]
    fn mqtt5_plain_connect_requires_initial_data_and_echoes_method_on_success() {
        let properties = [
            0x15, 0, 5, b'P', b'L', b'A', b'I', b'N', 0x16, 0, 4, 0, b'u', 0, b'p',
        ];
        assert!(matches!(
            mqtt5_connect_properties_supported(&properties).unwrap(),
            Mqtt5ConnectProperties::Supported {
                plain_authentication: Some(data),
                ..
            } if data == b"\0u\0p"
        ));
        assert_eq!(
            mqtt5_connect_properties_supported(&[0x15, 0, 5, b'P', b'L', b'A', b'I', b'N'])
                .unwrap(),
            Mqtt5ConnectProperties::Unsupported {
                maximum_packet_size: None,
                reason_code: 0x86,
            }
        );
        assert_eq!(
            append_mqtt5_plain_method(encode_mqtt5_shared_available_connack(false).to_vec()),
            [
                0x20, 13, 0, 0, 10, 0x2a, 1, 0x15, 0, 5, b'P', b'L', b'A', b'I', b'N'
            ]
        );
    }

    #[test]
    fn mqtt5_reauthentication_auth_requires_method_data_and_valid_reason() {
        let properties = [
            0x15, 0, 5, b'P', b'L', b'A', b'I', b'N', 0x16, 0, 4, 0, b'u', 0, b'p',
        ];
        let mut body = vec![0x19, 15];
        body.extend_from_slice(&properties);
        assert!(matches!(
            decode_for(0xf0, &body, true).unwrap(),
            Packet::Auth { method, data } if method == "PLAIN" && data == b"\0u\0p"
        ));
        assert_eq!(
            encode_mqtt5_plain_auth_success(),
            [0xf0, 10, 0, 8, 0x15, 0, 5, b'P', b'L', b'A', b'I', b'N']
        );
        assert_eq!(encode_mqtt5_auth_failure_disconnect(), [0xe0, 2, 0x86, 0]);
        for invalid in [
            vec![0x18, 15, *properties.first().unwrap()],
            vec![0x19, 8, 0x15, 0, 5, b'P', b'L', b'A', b'I', b'N'],
            vec![0x19, 7, 0x16, 0, 4, 0, b'u', 0, b'p'],
            vec![0x19, 0x80],
            vec![0x19, 1, 0xff],
        ] {
            assert!(decode_for(0xf0, &invalid, true).is_err(), "{invalid:?}");
        }
        let mut duplicate = body.clone();
        duplicate[1] += 8;
        duplicate.extend_from_slice(&properties[..8]);
        assert!(decode_for(0xf0, &duplicate, true).is_err());
        assert!(decode_for(0xf1, &body, true).is_err());
        assert!(decode_for(0xf0, &body, false).is_err());
        for index in 0..body.len() {
            for value in 0..=u8::MAX {
                let mut mutated = body.clone();
                mutated[index] = value;
                let _ = decode_for(0xf0, &mutated, true);
            }
        }
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
        assert!(
            frame_header(&[0x10, 0xfd, 0xff, 0x03])
                .unwrap_err()
                .is::<PacketTooLarge>()
        );
        assert!(frame_header(&[0x10, 0x80, 0x80, 0x04]).is_err());
        assert!(frame_header(&[0x30, 0x80, 0x80, 0x80]).unwrap().is_none());
        assert!(
            frame_header(&[0x30, 0x80, 0x80, 0x80, 0x80])
                .unwrap_err()
                .is::<MalformedRemainingLength>()
        );
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
                expiry_interval: None,
                ..
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
        for header in [0xc1, 0xe1] {
            assert!(
                decode_for(header, &[], true)
                    .unwrap_err()
                    .is::<FixedHeaderFlagsInvalid>()
            );
            assert!(decode_for(header, &[], false).is_err());
        }
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
        assert!(matches!(
            decode(0x40, &[0, 1]).unwrap(),
            Packet::PubAck {
                packet_id: 1,
                reason_code: 0
            }
        ));
        assert!(matches!(
            decode(0x50, &[0, 2]).unwrap(),
            Packet::PubRec {
                packet_id: 2,
                reason_code: 0
            }
        ));
        assert!(matches!(
            decode(0x62, &[0, 2]).unwrap(),
            Packet::PubRel {
                packet_id: 2,
                reason_code: 0
            }
        ));
        assert!(matches!(
            decode(0x70, &[0, 2]).unwrap(),
            Packet::PubComp {
                packet_id: 2,
                reason_code: 0
            }
        ));
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
