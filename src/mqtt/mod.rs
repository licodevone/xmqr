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

use std::{sync::Arc, time::Duration};

use tokio::time::{Instant, sleep_until};
use tracing::{debug, warn};

use crate::monitoring::{Metrics, Rejection};
use crate::{
    auth::AccessPolicy,
    transport::{BrokerConnection, HandlerError},
};
use codec::{
    FrameReader, Packet, Qos, encode_connack, encode_connack_with_session, encode_pingresp,
    encode_puback, encode_pubcomp, encode_pubrec, encode_pubrel, encode_suback, encode_unsuback,
};
use router::{AckKind, Delivery, RouterError};
use std::sync::atomic::Ordering;
use store::StoredMessage;

const CONNECT_TIMEOUT: Duration = Duration::from_secs(3);
const WRITE_TIMEOUT: Duration = Duration::from_secs(3);

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
    if matches!(connect, Packet::UnsupportedConnect5) {
        connection
            .write_all_with_deadline(&codec::encode_mqtt5_connack(0x83), WRITE_TIMEOUT)
            .await?;
        return Ok(());
    }
    let Packet::Connect {
        mqtt5,
        client_id,
        clean_session,
        keep_alive,
        will,
        username,
        password,
    } = connect
    else {
        return Err("first MQTT packet must be CONNECT".into());
    };
    let refusal = |legacy: u8, v5: u8| -> Vec<u8> {
        if mqtt5 {
            codec::encode_mqtt5_connack(v5).to_vec()
        } else {
            encode_connack(legacy).to_vec()
        }
    };

    // MQTT-3.1.3-8/9: XMQR refuses empty IDs rather than assigning one.
    // The 256-byte ceiling is a local quota shared with durable validation.
    // Validate before authentication/actor registration: a refused CONNECT
    // cannot mutate state or process a pipelined publication (3.1.4-5).
    if client_id.is_empty() || client_id.len() > store::MAX_CLIENT_ID_BYTES {
        metrics.reject(Rejection::Quota);
        connection
            .write_all_with_deadline(&refusal(2, 0x85), WRITE_TIMEOUT)
            .await?;
        return Ok(());
    }
    let Some(client_id) = auth.scoped_client_id(&client_id) else {
        metrics.reject(Rejection::Quota);
        connection
            .write_all_with_deadline(&refusal(2, 0x85), WRITE_TIMEOUT)
            .await?;
        return Ok(());
    };

    let security_generation = auth.security_generation();
    let cert = connection.peer_certificates().first();
    let principal = auth
        .authenticate(
            cert.map(AsRef::as_ref),
            username.as_deref(),
            password.as_deref(),
        )
        .await?;
    let Some(principal) = principal else {
        metrics.reject(Rejection::Authentication);
        connection
            .write_all_with_deadline(&refusal(5, 0x86), WRITE_TIMEOUT)
            .await?;
        return Ok(());
    };
    let mut session = match router
        .register_with_epoch(
            client_id,
            principal.clone(),
            clean_session,
            will,
            Some(security_generation),
        )
        .await
    {
        Ok(session) => session,
        Err(RouterError::PrincipalMismatch | RouterError::WillDenied | RouterError::Security) => {
            connection
                .write_all_with_deadline(&refusal(5, 0x87), WRITE_TIMEOUT)
                .await?;
            return Ok(());
        }
        Err(error) => return Err(error.into()),
    };
    let mut guard = router.connection_guard(&session);
    let connack = if mqtt5 {
        codec::encode_mqtt5_success_connack().to_vec()
    } else {
        encode_connack_with_session(0, session.resumed)?.to_vec()
    };
    if let Err(error) = connection
        .write_all_with_deadline(&connack, WRITE_TIMEOUT)
        .await
    {
        let _ = router.unregister(&session, false).await;
        guard.disarm();
        return Err(error.into());
    }
    debug!(
        connection_id = connection.id(),
        "MQTT client accepted by access policy"
    );
    if mqtt5 {
        reader.set_mqtt5();
    }

    let mut graceful = false;
    let mut last_inbound = Instant::now();
    let result: Result<(), HandlerError> = async {
        for delivery in session.replay.drain(..) {
            send_delivery(connection, delivery, &metrics, &auth, &principal, security_generation, mqtt5).await?;
        }
        loop {
            // MQTT-3.1.2-24: disconnect after 1.5 times the advertised keep-alive.
            // Zero disables MQTT keep-alive; a server idle cap remains.
            let idle = if keep_alive == 0 {
                Duration::from_secs(300)
            } else {
                Duration::from_millis(u64::from(keep_alive) * 1500)
            };
            let deadline = last_inbound + idle;
            tokio::select! {
                biased;
                _ = session.closed.changed() => break,
                () = sleep_until(deadline) => break,
                incoming = reader.read_packet(connection, deadline) => {
                    last_inbound = Instant::now();
                    match incoming? {
                        Packet::Subscribe { packet_id, filters } => {
                            let requested = filters.into_iter().map(|(filter,qos)| {
                                let granted = auth.allowed_subscribe(&principal, filter.as_str()).then_some(qos.as_u8());
                                (filter, granted)
                            }).collect();
                            let (mut codes, retained) = router.subscribe(&session, requested).await?;
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
                            connection.write_all_with_deadline(&ack, WRITE_TIMEOUT).await?;
                            for delivery in retained { send_delivery(connection, delivery, &metrics, &auth, &principal, security_generation, mqtt5).await?; }
                        }
                        Packet::Unsubscribe { packet_id, filters } => {
                            router.unsubscribe(&session, filters).await?;
                            connection.write_all_with_deadline(&encode_unsuback(packet_id), WRITE_TIMEOUT).await?;
                        }
                        Packet::Publish { topic, payload, qos, retain, dup, packet_id } => {
                            // DUP is a PUBLISH retransmission hint, not an application dedup key.
                            let _ = dup;
                            if !auth.allowed_publish(&principal, topic.as_str()) {
                                metrics.reject(Rejection::Authorization);
                                if mqtt5 && qos == Qos::AtLeastOnce {
                                    let id = packet_id.ok_or("QoS 1 PUBLISH without identifier")?;
                                    connection.write_all_with_deadline(&codec::encode_mqtt5_puback_reason(id, 0x87), WRITE_TIMEOUT).await?;
                                    continue;
                                }
                                warn!(connection_id=connection.id(), "unauthorized publish; closing client");
                                break;
                            }
                            let message = StoredMessage { topic, payload, qos: qos.as_u8(), retain };
                            router.publish(&session, message, packet_id).await?;
                            match (qos, packet_id) {
                                (Qos::AtLeastOnce, Some(id)) => connection.write_all_with_deadline(&encode_puback(id), WRITE_TIMEOUT).await?,
                                (Qos::ExactlyOnce, Some(id)) => connection.write_all_with_deadline(&encode_pubrec(id), WRITE_TIMEOUT).await?,
                                (Qos::AtMostOnce, None) => {},
                                _ => return Err("invalid PUBLISH identifier".into()),
                            }
                        }
                        Packet::PubRel(id) => {
                            router.pubrel(&session, id).await?;
                            connection.write_all_with_deadline(&encode_pubcomp(id), WRITE_TIMEOUT).await?;
                        }
                        Packet::PubAck(id) => {
                            for delivery in router.ack(&session, AckKind::Ack, id).await? {
                                send_delivery(connection, delivery, &metrics, &auth, &principal, security_generation, mqtt5).await?;
                            }
                        }
                        Packet::PubRec(id) => {
                            for delivery in router.ack(&session, AckKind::Rec, id).await? {
                                send_delivery(connection, delivery, &metrics, &auth, &principal, security_generation, mqtt5).await?;
                            }
                        }
                        Packet::PubComp(id) => {
                            for delivery in router.ack(&session, AckKind::Comp, id).await? {
                                send_delivery(connection, delivery, &metrics, &auth, &principal, security_generation, mqtt5).await?;
                            }
                        }
                        Packet::PingReq => connection.write_all_with_deadline(&encode_pingresp(), WRITE_TIMEOUT).await?,
                        Packet::Disconnect => { graceful = true; break; },
                        Packet::Connect { .. } | Packet::UnsupportedConnect5 => return Err("duplicate CONNECT".into()),
                    }
                }
                outbound = session.outbound.recv() => {
                    let Some(delivery) = outbound else { break; };
                    send_delivery(connection, delivery, &metrics, &auth, &principal, security_generation, mqtt5).await?;
                }
            }
        }
        Ok(())
    }.await;
    let cleanup = router.unregister(&session, graceful).await;
    guard.disarm();
    // A stale generation was already closed and its Will handled by takeover.
    if let Err(error) = cleanup
        && !matches!(error, RouterError::Stale)
    {
        return Err(error.into());
    }
    result
}

async fn send_delivery(
    connection: &mut BrokerConnection,
    delivery: Delivery,
    metrics: &Metrics,
    auth: &AccessPolicy,
    principal: &str,
    security_generation: u64,
    mqtt5: bool,
) -> Result<(), HandlerError> {
    if auth.security_generation() != security_generation {
        return Err("security generation changed".into());
    }
    if let Delivery::Publish { message, .. } = &delivery
        && !auth.allowed_delivery(principal, message.topic.as_str())
    {
        return Err("delivery authorization revoked".into());
    }

    let bytes = match delivery {
        Delivery::Publish {
            message,
            packet_id,
            dup,
        } => codec::encode_publish_for(
            message.topic.as_str(),
            &message.payload,
            Qos::from_u8(message.qos)?,
            message.retain,
            dup,
            packet_id,
            mqtt5,
        )?,
        Delivery::PubRel(id) => encode_pubrel(id).to_vec(),
    };
    connection
        .write_all_with_deadline(&bytes, WRITE_TIMEOUT)
        .await?;
    if bytes[0] >> 4 == 3 {
        metrics.sent[usize::from((bytes[0] >> 1) & 3)].fetch_add(1, Ordering::Relaxed);
    }
    Ok(())
}
