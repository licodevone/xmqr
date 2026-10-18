//! MQTT 3.1.1 session handler with bounded `QoS` 0/1/2, retained messages
//! and durable CleanSession=0 state. Topic filters support MQTT 3.1.1 `+` and
//! `#`, with durable Last Will. MQTT 5 has an initial pub/sub subset.

mod codec;
#[cfg(all(test, unix))]
mod connect_contract_tests;
mod limits;
mod router;
#[cfg(all(test, unix))]
mod storage_fault_tests;
mod store;
pub(crate) mod topic;

pub use limits::StateLimits;
pub use router::Router;
pub(crate) use router::{AdminError, AdminListKind};

/// Maximum UTF-8 byte length of a topic name or filter accepted by XMQR.
///
/// This project quota is narrower than MQTT's 65,535-byte string ceiling.
pub const MAX_TOPIC_BYTES: usize = 1024;

use std::{collections::HashMap, fmt::Write as _, sync::Arc, time::Duration};

use rand_core::{OsRng, RngCore};
use tokio::time::{Instant, sleep_until};
use tracing::{debug, warn};
use zeroize::Zeroizing;

use crate::monitoring::{Metrics, Rejection};
use crate::{
    auth::AccessPolicy,
    transport::{BrokerConnection, HandlerError},
};
use codec::{
    FrameReader, Packet, Qos, TopicAliasMode, encode_connack, encode_connack_with_session,
    encode_pingresp, encode_puback, encode_pubcomp, encode_pubrec, encode_pubrel, encode_suback,
    encode_unsuback,
};
use router::{AckKind, Delivery, RouterError, SessionPolicy};
use std::sync::atomic::Ordering;
use store::StoredMessage;

const CONNECT_TIMEOUT: Duration = Duration::from_secs(3);
const WRITE_TIMEOUT: Duration = Duration::from_secs(3);

fn new_assigned_client_id() -> String {
    let mut random = [0u8; 16];
    OsRng.fill_bytes(&mut random);
    let mut id = String::from("xmqr-");
    for byte in random {
        write!(&mut id, "{byte:02x}").expect("writing to String cannot fail");
    }
    id
}

fn plain_credentials(data: &[u8]) -> Option<(&str, &[u8])> {
    let mut fields = data.split(|byte| *byte == 0);
    let authorization = fields.next()?;
    let identity = fields.next()?;
    let password = fields.next()?;
    if !authorization.is_empty()
        || identity.is_empty()
        || password.is_empty()
        || fields.next().is_some()
    {
        return None;
    }
    let identity = std::str::from_utf8(identity).ok()?;
    let _ = std::str::from_utf8(password).ok()?;
    Some((identity, password))
}

struct OutboundAliases {
    maximum: u16,
    topics: HashMap<String, u16>,
}

impl OutboundAliases {
    fn candidate(&self, topic: &str) -> TopicAliasMode {
        if let Some(&alias) = self.topics.get(topic) {
            return TopicAliasMode::Use(alias);
        }
        if self.topics.len() < usize::from(self.maximum) {
            return TopicAliasMode::Establish(
                u16::try_from(self.topics.len() + 1).expect("at most 16 aliases"),
            );
        }
        TopicAliasMode::None
    }
}

/// Serve one transport connection under the startup-selected access policy.
///
/// # Errors
///
/// Malformed packets, ACL violations, I/O failures and uncertain durable
/// commits close the connection. Unsupported MQTT 5 options emit `0x83`;
/// other unsupported protocol levels emit `CONNACK 0x01`,
/// refused client identifiers `0x02`, and authentication failures `0x05`.
pub async fn serve_connection(
    mut connection: BrokerConnection,
    auth: Arc<AccessPolicy>,
    router: Arc<Router>,
) -> Result<(), HandlerError> {
    // Close remains inside the admitted task, even after a CONNECT refusal or
    // actor cleanup error. Preserve the MQTT error ahead of a later close error.
    let _connection_metric = router.metrics().connection();
    let result = serve_mqtt(&mut connection, auth, router).await;
    let closed = connection.shutdown().await;
    result?;
    closed.map_err(Into::into)
}

#[allow(clippy::too_many_lines)] // Explicit packet-state dispatch is auditable against OASIS.
async fn serve_mqtt(
    connection: &mut BrokerConnection,
    auth: Arc<AccessPolicy>,
    router: Arc<Router>,
) -> Result<(), HandlerError> {
    let metrics = router.metrics();
    let mut reader = FrameReader::new(connection.take_initial_mqtt_bytes());
    let connect = match reader
        .read_packet(connection, Instant::now() + CONNECT_TIMEOUT)
        .await
    {
        Ok(packet) => packet,
        Err(error) if error.is::<codec::UnsupportedProtocolLevel>() => {
            let level = error
                .downcast_ref::<codec::UnsupportedProtocolLevel>()
                .expect("checked unsupported protocol error")
                .0;
            // Unknown levels keep the 3.1.1 refusal established by P93.
            let _ = level;
            connection
                .write_all_with_deadline(&encode_connack(1), WRITE_TIMEOUT)
                .await?;
            return Ok(());
        }
        Err(error) => return Err(error),
    };
    if let Packet::UnsupportedConnect5 {
        maximum_packet_size,
        reason_code,
    } = connect
    {
        if maximum_packet_size.is_none_or(|size| size >= 5) {
            connection
                .write_all_with_deadline(&codec::encode_mqtt5_connack(reason_code), WRITE_TIMEOUT)
                .await?;
        }
        return Ok(());
    }
    let Packet::Connect {
        mqtt5,
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
    } = connect
    else {
        return Err("first MQTT packet must be CONNECT".into());
    };
    let outbound_maximum = maximum_packet_size.map_or(usize::MAX, |value| value as usize);
    let plain_authentication = plain_authentication.map(Zeroizing::new);
    let plain_requested = plain_authentication.is_some();
    let server_keep_alive = if mqtt5 {
        router
            .server_keep_alive_seconds()
            .filter(|limit| keep_alive == 0 || keep_alive > *limit)
    } else {
        None
    };
    if mqtt5 && outbound_maximum < 5 {
        // Even the minimal MQTT 5 CONNACK cannot fit. No session was created.
        return Ok(());
    }
    if plain_requested && !connection.is_tls() {
        write_limited(
            connection,
            &codec::encode_mqtt5_connack(0x8c),
            outbound_maximum,
        )
        .await?;
        return Ok(());
    }
    if plain_requested && (username.is_some() || password.is_some()) {
        write_limited(
            connection,
            &codec::encode_mqtt5_connack(0x82),
            outbound_maximum,
        )
        .await?;
        return Ok(());
    }
    if plain_requested && outbound_maximum < 15 {
        write_limited(
            connection,
            &codec::encode_mqtt5_connack(0x95),
            outbound_maximum,
        )
        .await?;
        return Ok(());
    }
    if mqtt5 && outbound_maximum < 7 {
        // The negotiated Shared Subscription Available property must fit.
        write_limited(
            connection,
            &codec::encode_mqtt5_connack(0x95),
            outbound_maximum,
        )
        .await?;
        return Ok(());
    }
    if server_keep_alive.is_some() && outbound_maximum < 10 + usize::from(plain_requested) * 8 {
        // Server Keep Alive must fit when it replaces CONNECT Keep Alive.
        write_limited(
            connection,
            &codec::encode_mqtt5_connack(0x95),
            outbound_maximum,
        )
        .await?;
        return Ok(());
    }
    let refusal = |legacy: u8, v5: u8| -> Vec<u8> {
        if mqtt5 {
            codec::encode_mqtt5_connack(v5).to_vec()
        } else {
            encode_connack(legacy).to_vec()
        }
    };

    // MQTT 5 allows the server to assign an ID; MQTT 3.1.1 retains its
    // earlier refusal. The 256-byte ceiling is shared with durable state.
    // Validate before authentication/actor registration: a refused CONNECT
    // cannot mutate state or process a pipelined publication (3.1.4-5).
    if (!mqtt5 && client_id.is_empty()) || client_id.len() > store::MAX_CLIENT_ID_BYTES {
        metrics.reject(Rejection::Quota);
        write_limited(connection, &refusal(2, 0x85), outbound_maximum).await?;
        return Ok(());
    }
    let assigned_id = mqtt5 && client_id.is_empty();
    let mut client_id = if assigned_id {
        new_assigned_client_id()
    } else {
        client_id
    };
    let assigned_property_size = if assigned_id { 3 + client_id.len() } else { 0 };
    if assigned_id
        && outbound_maximum
            < 7 + assigned_property_size
                + usize::from(plain_requested) * 8
                + usize::from(server_keep_alive.is_some()) * 3
    {
        // The Assigned Client Identifier property is mandatory on success.
        write_limited(connection, &refusal(2, 0x95), outbound_maximum).await?;
        return Ok(());
    }
    let Some(mut scoped_client_id) = auth.scoped_client_id(&client_id) else {
        metrics.reject(Rejection::Quota);
        write_limited(connection, &refusal(2, 0x85), outbound_maximum).await?;
        return Ok(());
    };

    let security_generation = auth.security_generation();
    let cert_der = connection
        .peer_certificates()
        .first()
        .map(|cert| cert.as_ref().to_vec());
    let principal = if let Some(data) = plain_authentication.as_ref() {
        let Some((identity, secret)) = plain_credentials(data) else {
            metrics.reject(Rejection::Authentication);
            write_limited(connection, &refusal(5, 0x86), outbound_maximum).await?;
            return Ok(());
        };
        auth.authenticate(cert_der.as_deref(), Some(identity), Some(secret))
            .await?
    } else {
        auth.authenticate(
            cert_der.as_deref(),
            username.as_deref(),
            password.as_deref(),
        )
        .await?
    };
    drop(plain_authentication);
    let Some(principal) = principal else {
        metrics.reject(Rejection::Authentication);
        write_limited(connection, &refusal(5, 0x86), outbound_maximum).await?;
        return Ok(());
    };
    let mut attempts = 0;
    let mut session = loop {
        attempts += 1;
        let policy = SessionPolicy {
            clean: clean_session,
            persistent: if mqtt5 {
                session_expiry != 0
            } else {
                !clean_session
            },
            expiry_interval_seconds: if mqtt5 && (1..u32::MAX).contains(&session_expiry) {
                Some(session_expiry)
            } else {
                None
            },
            will_delay_seconds,
            will_message_expiry_seconds,
            receive_maximum,
        };
        let result = if assigned_id {
            router
                .register_assigned_with_policy(
                    scoped_client_id.clone(),
                    principal.clone(),
                    policy,
                    will.clone(),
                    Some(security_generation),
                )
                .await
        } else {
            router
                .register_with_policy(
                    scoped_client_id.clone(),
                    principal.clone(),
                    policy,
                    will.clone(),
                    Some(security_generation),
                )
                .await
        };
        match result {
            Ok(session) => break session,
            Err(RouterError::AssignedIdCollision) if assigned_id && attempts < 4 => {
                client_id = new_assigned_client_id();
                scoped_client_id = auth
                    .scoped_client_id(&client_id)
                    .ok_or("generated Client Identifier exceeds listener quota")?;
            }
            Err(RouterError::AssignedIdCollision) => {
                metrics.reject(Rejection::Quota);
                write_limited(connection, &refusal(2, 0x97), outbound_maximum).await?;
                return Ok(());
            }
            Err(
                RouterError::PrincipalMismatch | RouterError::WillDenied | RouterError::Security,
            ) => {
                write_limited(connection, &refusal(5, 0x87), outbound_maximum).await?;
                return Ok(());
            }
            Err(error) => return Err(error.into()),
        }
    };
    let mut guard = router.connection_guard(&session);
    let connack_base_budget = outbound_maximum.saturating_sub(
        usize::from(plain_requested) * 8
            + usize::from(server_keep_alive.is_some()) * 3
            + assigned_property_size,
    );
    let advertised_alias_maximum = if mqtt5 && connack_base_budget >= 15 {
        u16::from(codec::MAX_TOPIC_ALIAS)
    } else {
        0
    };
    let mut connack = if advertised_alias_maximum != 0 {
        codec::encode_mqtt5_alias_connack(session.resumed).to_vec()
    } else if mqtt5 && connack_base_budget >= 12 {
        codec::encode_mqtt5_success_connack(session.resumed).to_vec()
    } else if mqtt5 {
        codec::encode_mqtt5_shared_available_connack(session.resumed).to_vec()
    } else {
        encode_connack_with_session(0, session.resumed)?.to_vec()
    };
    if plain_requested {
        connack = codec::append_mqtt5_plain_method(connack);
    }
    if let Some(seconds) = server_keep_alive {
        connack = codec::append_mqtt5_server_keep_alive(connack, seconds);
    }
    if assigned_id {
        connack = codec::append_mqtt5_assigned_client_id(connack, &client_id);
    }
    // Preserve P136/P138's previously negotiated Maximum Packet Size and
    // Topic Alias properties; omit Receive Maximum only when it cannot fit.
    if mqtt5 && connack.len() + 3 <= outbound_maximum {
        connack = codec::append_mqtt5_receive_maximum(connack, router.inbound_receive_maximum());
    }
    if let Err(error) = write_limited(connection, &connack, outbound_maximum).await {
        let _ = router.unregister(&session, false).await;
        guard.disarm();
        return Err(error);
    }
    debug!(
        connection_id = connection.id(),
        "MQTT client accepted by access policy"
    );
    if mqtt5 {
        reader.set_mqtt5(advertised_alias_maximum);
    }

    let mut graceful = false;
    let mut outbound_aliases = OutboundAliases {
        maximum: if mqtt5 {
            topic_alias_maximum.min(u16::from(codec::MAX_TOPIC_ALIAS))
        } else {
            0
        },
        topics: HashMap::new(),
    };
    let mut disconnect_expiry = None;
    let mut last_inbound = Instant::now();
    let result: Result<(), HandlerError> = async {
        for delivery in std::mem::take(&mut session.replay) {
            send_delivery(connection, delivery, &metrics, &auth, &principal, security_generation, mqtt5, outbound_maximum, &mut outbound_aliases, &router, &session).await?;
        }
        loop {
            // MQTT-3.1.2-24: disconnect after 1.5 times the advertised keep-alive.
            // Zero disables MQTT keep-alive; a server idle cap remains.
            let effective_keep_alive = server_keep_alive.unwrap_or(keep_alive);
            let idle = if effective_keep_alive == 0 {
                Duration::from_secs(300)
            } else {
                Duration::from_millis(u64::from(effective_keep_alive) * 1500)
            };
            let deadline = last_inbound + idle;
            tokio::select! {
                biased;
                _ = session.closed.changed() => break,
                () = sleep_until(deadline) => break,
                incoming = reader.read_packet(connection, deadline) => {
                    last_inbound = Instant::now();
                    let packet = match incoming {
                        Ok(packet) => packet,
                        Err(error) if mqtt5 && error.is::<codec::PacketTooLarge>() => {
                            let _ = write_limited(connection, &[0xe0, 2, 0x95, 0], outbound_maximum).await;
                            return Err(error);
                        }
                        Err(error) if mqtt5 && error.is::<codec::TopicAliasInvalid>() => {
                            let _ = write_limited(connection, &[0xe0, 2, 0x94, 0], outbound_maximum).await;
                            return Err(error);
                        }
                        Err(error) if mqtt5 && error.is::<codec::MalformedRemainingLength>() => {
                            let _ = write_limited(connection, &[0xe0, 2, 0x81, 0], outbound_maximum).await;
                            return Err(error);
                        }
                        Err(error) if mqtt5 && error.is::<codec::FixedHeaderFlagsInvalid>() => {
                            let _ = write_limited(connection, &[0xe0, 2, 0x82, 0], outbound_maximum).await;
                            return Err(error);
                        }
                        Err(error) if mqtt5 && error.is::<codec::SubscriptionPropertyMalformed>() => {
                            let _ = write_limited(connection, &[0xe0, 2, 0x81, 0], outbound_maximum).await;
                            return Err(error);
                        }
                        Err(error) if mqtt5 && error.is::<codec::SubscriptionIdentifierDuplicate>() => {
                            let _ = write_limited(connection, &[0xe0, 2, 0x82, 0], outbound_maximum).await;
                            return Err(error);
                        }
                        Err(error) if mqtt5 && error.is::<codec::PublishPropertyMalformed>() => {
                            let _ = write_limited(connection, &[0xe0, 2, 0x81, 0], outbound_maximum).await;
                            return Err(error);
                        }
                        Err(error) if mqtt5 && error.is::<codec::PublishPropertyProtocol>() => {
                            let _ = write_limited(connection, &[0xe0, 2, 0x82, 0], outbound_maximum).await;
                            return Err(error);
                        }
                        Err(error) if mqtt5 && error.is::<codec::ControlPropertyMalformed>() => {
                            let _ = write_limited(connection, &[0xe0, 2, 0x81, 0], outbound_maximum).await;
                            return Err(error);
                        }
                        Err(error) if mqtt5 && error.is::<codec::ControlPropertyDuplicate>() => {
                            let _ = write_limited(connection, &[0xe0, 2, 0x82, 0], outbound_maximum).await;
                            return Err(error);
                        }
                        Err(error) if mqtt5 && error.is::<codec::AckPropertyMalformed>() => {
                            let _ = write_limited(connection, &[0xe0, 2, 0x81, 0], outbound_maximum).await;
                            return Err(error);
                        }
                        Err(error) if mqtt5 && error.is::<codec::AckPacketIdentifierZero>() => {
                            let _ = write_limited(connection, &[0xe0, 2, 0x82, 0], outbound_maximum).await;
                            return Err(error);
                        }
                        Err(error) if mqtt5 && error.is::<codec::AckPropertyDuplicate>() => {
                            let _ = write_limited(connection, &[0xe0, 2, 0x82, 0], outbound_maximum).await;
                            return Err(error);
                        }
                        Err(error) => return Err(error),
                    };
                    match packet {
                        Packet::Subscribe { packet_id, filters, subscription_identifier } => {
                            let requested = filters.into_iter().map(|(filter,qos,retain_handling,subscription_flags)| {
                                let inner = if mqtt5 { topic::shared_inner(filter.as_str()) } else { None };
                                let granted = auth.allowed_subscribe(&principal, inner.unwrap_or(filter.as_str())).then_some(qos.as_u8());
                                (filter, granted, retain_handling, subscription_flags)
                            }).collect();
                            let (mut codes, retained) = router.subscribe_with_shared(&session, requested, subscription_identifier, mqtt5).await?;
                            if mqtt5 {
                                // The router uses the MQTT 3.1.1 failure code for ACL denial.
                                // MQTT 5 can report the precise reason to each filter.
                                for code in &mut codes {
                                    if *code == 0x80 {
                                        *code = 0x87;
                                    }
                                }
                            }
                            let ack = if mqtt5 { codec::encode_mqtt5_suback(packet_id, &codes) } else { encode_suback(packet_id, &codes) };
                            write_limited(connection, &ack, outbound_maximum).await?;
                            for delivery in retained { send_delivery(connection, delivery, &metrics, &auth, &principal, security_generation, mqtt5, outbound_maximum, &mut outbound_aliases, &router, &session).await?; }
                        }
                        Packet::Unsubscribe { packet_id, filters } => {
                            let codes = router.unsubscribe(&session, filters).await?;
                            let ack = if mqtt5 { codec::encode_mqtt5_unsuback(packet_id, &codes) } else { encode_unsuback(packet_id).to_vec() };
                            write_limited(connection, &ack, outbound_maximum).await?;
                        }
                        Packet::Publish { topic, topic_alias: _, payload, qos, retain, dup, packet_id, expiry_interval, payload_format_indicator, content_type, response_topic, correlation_data, user_properties } => {
                            let topic = topic.ok_or("unresolved MQTT 5 Topic Alias")?;
                            // DUP is a PUBLISH retransmission hint, not an application dedup key.
                            let _ = dup;
                            if !auth.allowed_publish(&principal, topic.as_str()) {
                                metrics.reject(Rejection::Authorization);
                                if mqtt5 && qos != Qos::AtMostOnce {
                                    let id = packet_id.ok_or("QoS 1/2 PUBLISH without identifier")?;
                                    let ack = if qos == Qos::AtLeastOnce { codec::encode_mqtt5_puback_reason(id, 0x87) } else { codec::encode_mqtt5_pubrec_reason(id, 0x87) };
                                    write_limited(connection, &ack, outbound_maximum).await?;
                                    continue;
                                }
                                warn!(connection_id=connection.id(), "unauthorized publish; closing client");
                                break;
                            }
                            let expiry_at_unix_ms = expiry_interval.map(router::message_expiry_deadline).transpose()?;
                            let message = StoredMessage { topic, payload, qos: qos.as_u8(), retain, expiry_at_unix_ms, payload_format_indicator, content_type, response_topic, correlation_data, user_properties, subscription_identifiers: Vec::new(), shared_origin: None };
                            match router.publish(&session, message, packet_id).await {
                                Err(RouterError::InboundQos2Quota) if mqtt5 && qos == Qos::ExactlyOnce => {
                                    let id = packet_id.ok_or("QoS 2 PUBLISH without identifier")?;
                                    write_limited(connection, &codec::encode_mqtt5_pubrec_reason(id, 0x97), outbound_maximum).await?;
                                    continue;
                                }
                                result => result?,
                            }
                            match (qos, packet_id) {
                                (Qos::AtLeastOnce, Some(id)) => write_limited(connection, &encode_puback(id), outbound_maximum).await?,
                                (Qos::ExactlyOnce, Some(id)) => write_limited(connection, &encode_pubrec(id), outbound_maximum).await?,
                                (Qos::AtMostOnce, None) => {},
                                _ => return Err("invalid PUBLISH identifier".into()),
                            }
                        }
                        Packet::PubRel { packet_id, reason_code } => {
                            if reason_code == 0x92 {
                                warn!(connection_id=connection.id(), reason_code, "MQTT 5 publisher reported unknown QoS2 identifier in PUBREL");
                            }
                            router.pubrel(&session, packet_id).await?;
                            write_limited(connection, &encode_pubcomp(packet_id), outbound_maximum).await?;
                        }
                        Packet::PubAck { packet_id, reason_code } => {
                            if reason_code >= 0x80 {
                                warn!(connection_id=connection.id(), reason_code, "MQTT 5 subscriber rejected QoS1 delivery");
                            }
                            for delivery in router.ack(&session, AckKind::Ack, packet_id).await? {
                                send_delivery(connection, delivery, &metrics, &auth, &principal, security_generation, mqtt5, outbound_maximum, &mut outbound_aliases, &router, &session).await?;
                            }
                        }
                        Packet::PubRec { packet_id, reason_code } => {
                            let kind = if reason_code >= 0x80 {
                                warn!(connection_id=connection.id(), reason_code, "MQTT 5 subscriber rejected QoS2 delivery");
                                AckKind::RecRejected
                            } else {
                                AckKind::Rec
                            };
                            for delivery in router.ack(&session, kind, packet_id).await? {
                                send_delivery(connection, delivery, &metrics, &auth, &principal, security_generation, mqtt5, outbound_maximum, &mut outbound_aliases, &router, &session).await?;
                            }
                        }
                        Packet::PubComp { packet_id, reason_code } => {
                            if reason_code == 0x92 {
                                warn!(connection_id=connection.id(), reason_code, "MQTT 5 subscriber reported unknown QoS2 identifier in PUBCOMP");
                            }
                            for delivery in router.ack(&session, AckKind::Comp, packet_id).await? {
                                send_delivery(connection, delivery, &metrics, &auth, &principal, security_generation, mqtt5, outbound_maximum, &mut outbound_aliases, &router, &session).await?;
                            }
                        }
                        Packet::PingReq => write_limited(connection, &encode_pingresp(), outbound_maximum).await?,
                        Packet::Auth { method, data } => {
                            let data = Zeroizing::new(data);
                            if !plain_requested || method != "PLAIN" {
                                return Err("MQTT 5 AUTH method differs from CONNECT".into());
                            }
                            let Some((identity, secret)) = plain_credentials(&data) else {
                                return Err("invalid MQTT 5 PLAIN AUTH data".into());
                            };
                            let verified = if auth.security_generation() == security_generation {
                                auth.authenticate(cert_der.as_deref(), Some(identity), Some(secret)).await?
                            } else {
                                None
                            };
                            if verified.as_deref() != Some(principal.as_str()) {
                                metrics.reject(Rejection::Authentication);
                                let denial = codec::encode_mqtt5_auth_failure_disconnect();
                                if denial.len() <= outbound_maximum {
                                    write_limited(connection, &denial, outbound_maximum).await?;
                                }
                                break;
                            }
                            write_limited(connection, &codec::encode_mqtt5_plain_auth_success(), outbound_maximum).await?;
                        }
                        Packet::Disconnect { reason_code, expiry_interval } => {
                            if session_expiry == 0 && expiry_interval.is_some_and(|seconds| seconds != 0) {
                                return Err("DISCONNECT cannot extend zero Session Expiry".into());
                            }
                            disconnect_expiry = expiry_interval;
                            if reason_code != 0 {
                                warn!(connection_id=connection.id(), reason_code, "MQTT 5 client disconnected with reason");
                            }
                            graceful = reason_code == 0;
                            break;
                        },
                        Packet::Connect { .. } | Packet::UnsupportedConnect5 { .. } => return Err("duplicate CONNECT".into()),
                    }
                }
                outbound = session.outbound.recv() => {
                    let Some(delivery) = outbound else { break; };
                    send_delivery(connection, delivery, &metrics, &auth, &principal, security_generation, mqtt5, outbound_maximum, &mut outbound_aliases, &router, &session).await?;
                }
            }
        }
        Ok(())
    }.await;
    let cleanup = router
        .unregister_with_expiry(&session, graceful, disconnect_expiry)
        .await;
    guard.disarm();
    // A stale generation was already closed and its Will handled by takeover.
    if let Err(error) = cleanup
        && !matches!(error, RouterError::Stale)
    {
        return Err(error.into());
    }
    result
}

#[allow(clippy::too_many_arguments, clippy::too_many_lines)] // Delivery keeps authorization, MQTT 5 projection and negotiated size together.
async fn send_delivery(
    connection: &mut BrokerConnection,
    delivery: Delivery,
    metrics: &Metrics,
    auth: &AccessPolicy,
    principal: &str,
    security_generation: u64,
    mqtt5: bool,
    outbound_maximum: usize,
    aliases: &mut OutboundAliases,
    router: &Router,
    session: &router::Session,
) -> Result<(), HandlerError> {
    if auth.security_generation() != security_generation {
        return Err("security generation changed".into());
    }
    if let Delivery::Publish { message, .. } = &delivery
        && !auth.allowed_delivery(principal, message.topic.as_str())
    {
        return Err("delivery authorization revoked".into());
    }

    let packet_id_to_discard = match &delivery {
        Delivery::Publish { packet_id, .. } => *packet_id,
        Delivery::PubRel(_) => None,
    };
    let mut pending_alias = None;
    let bytes = match delivery {
        Delivery::Publish {
            message,
            packet_id,
            dup,
        } => {
            let expiry = if mqtt5 {
                message
                    .expiry_at_unix_ms
                    .map(router::remaining_message_expiry)
                    .transpose()?
            } else {
                None
            };
            let topic = message.topic.as_str();
            let payload_format_indicator = if mqtt5 {
                message.payload_format_indicator
            } else {
                None
            };
            let content_type = if mqtt5 {
                message.content_type.as_deref()
            } else {
                None
            };
            let response_topic = if mqtt5 {
                message
                    .response_topic
                    .as_ref()
                    .map(topic::TopicName::as_str)
            } else {
                None
            };
            let correlation_data = if mqtt5 {
                message.correlation_data.as_deref()
            } else {
                None
            };
            let user_properties = if mqtt5 {
                message.user_properties.as_slice()
            } else {
                &[]
            };
            let subscription_identifiers = if mqtt5 {
                message.subscription_identifiers.as_slice()
            } else {
                &[]
            };
            let alias_mode = aliases.candidate(topic);
            let mut encoded = codec::encode_publish_with_subscription_ids(
                topic,
                &message.payload,
                Qos::from_u8(message.qos)?,
                message.retain,
                dup,
                packet_id,
                mqtt5,
                expiry,
                alias_mode,
                payload_format_indicator,
                content_type,
                response_topic,
                correlation_data,
                user_properties,
                subscription_identifiers,
            )?;
            if matches!(alias_mode, TopicAliasMode::Establish(_))
                && encoded.len() > outbound_maximum
            {
                // Do not establish an alias with a packet the peer cannot receive.
                encoded = codec::encode_publish_with_subscription_ids(
                    topic,
                    &message.payload,
                    Qos::from_u8(message.qos)?,
                    message.retain,
                    dup,
                    packet_id,
                    mqtt5,
                    expiry,
                    TopicAliasMode::None,
                    payload_format_indicator,
                    content_type,
                    response_topic,
                    correlation_data,
                    user_properties,
                    subscription_identifiers,
                )?;
            } else if let TopicAliasMode::Establish(alias) = alias_mode {
                pending_alias = Some((topic.to_owned(), alias));
            }
            encoded
        }
        Delivery::PubRel(id) => encode_pubrel(id).to_vec(),
    };
    if bytes.len() > outbound_maximum {
        if bytes[0] >> 4 != 3 {
            return Err("essential MQTT packet exceeds client Maximum Packet Size".into());
        }
        if let Some(packet_id) = packet_id_to_discard {
            router.discard_outbound(session, packet_id).await?;
        }
        return Ok(());
    }
    write_limited(connection, &bytes, outbound_maximum).await?;
    if let Some((topic, alias)) = pending_alias {
        aliases.topics.insert(topic, alias);
    }
    if bytes[0] >> 4 == 3 {
        metrics.sent[usize::from((bytes[0] >> 1) & 3)].fetch_add(1, Ordering::Relaxed);
    }
    Ok(())
}

async fn write_limited(
    connection: &mut BrokerConnection,
    bytes: &[u8],
    outbound_maximum: usize,
) -> Result<(), HandlerError> {
    if bytes.len() > outbound_maximum {
        return Err("MQTT packet exceeds client Maximum Packet Size".into());
    }
    connection
        .write_all_with_deadline(bytes, WRITE_TIMEOUT)
        .await?;
    Ok(())
}

#[cfg(test)]
mod plain_auth_tests {
    use super::plain_credentials;

    #[test]
    fn requires_empty_authorization_id_and_exact_utf8_fields() {
        assert_eq!(
            plain_credentials(b"\0device\0secret"),
            Some(("device", b"secret".as_slice()))
        );
        for invalid in [
            b"device\0secret".as_slice(),
            b"other\0device\0secret",
            b"\0\0secret",
            b"\0device\0",
            b"\0device\0secret\0extra",
            b"\0\xff\0secret",
            b"\0device\0\xff",
        ] {
            assert!(plain_credentials(invalid).is_none());
        }
    }
}
