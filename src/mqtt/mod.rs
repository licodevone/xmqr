//! MQTT 3.1.1 session handler with bounded `QoS` 0/1/2, retained messages
//! and durable CleanSession=0 state. Topic filters support MQTT 3.1.1 `+` and
//! `#`, with durable Last Will; full conformance remains a separate gate.

mod codec;
mod router;
mod store;
pub(crate) mod topic;

pub use router::Router;

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
    encode_puback, encode_pubcomp, encode_publish, encode_pubrec, encode_pubrel, encode_suback,
    encode_unsuback,
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
/// commits close the connection. Authentication failure emits `CONNACK 0x05`.
#[allow(clippy::too_many_lines)] // Explicit packet-state dispatch is auditable against OASIS.
pub async fn serve_connection(
    mut connection: BrokerConnection,
    auth: Arc<AccessPolicy>,
    router: Arc<Router>,
) -> Result<(), HandlerError> {
    let metrics = router.metrics();
    let _connection_metric = metrics.connection();
    let mut reader = FrameReader::new(connection.take_initial_mqtt_bytes());
    let connect = reader
        .read_packet(&mut connection, Instant::now() + CONNECT_TIMEOUT)
        .await?;
    let Packet::Connect {
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
            .write_all_with_deadline(&encode_connack(5), WRITE_TIMEOUT)
            .await?;
        return Ok(());
    };
    let mut session = match router
        .register_with_will(client_id, principal.clone(), clean_session, will)
        .await
    {
        Ok(session) => session,
        Err(RouterError::PrincipalMismatch | RouterError::WillDenied) => {
            connection
                .write_all_with_deadline(&encode_connack(5), WRITE_TIMEOUT)
                .await?;
            return Ok(());
        }
        Err(error) => return Err(error.into()),
    };
    let mut guard = router.connection_guard(&session);
    let connack = encode_connack_with_session(0, session.resumed)?;
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

    let mut graceful = false;
    let mut last_inbound = Instant::now();
    let result: Result<(), HandlerError> = async {
        for delivery in session.replay.drain(..) {
            send_delivery(&mut connection, delivery, &metrics).await?;
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
                incoming = reader.read_packet(&mut connection, deadline) => {
                    last_inbound = Instant::now();
                    match incoming? {
                        Packet::Subscribe { packet_id, filters } => {
                            let requested = filters.into_iter().map(|(filter,qos)| {
                                let granted = auth.allowed_subscribe(&principal, filter.as_str()).then_some(qos.as_u8());
                                (filter, granted)
                            }).collect();
                            let (codes, retained) = router.subscribe(&session, requested).await?;
                            connection.write_all_with_deadline(&encode_suback(packet_id, &codes), WRITE_TIMEOUT).await?;
                            for delivery in retained { send_delivery(&mut connection, delivery, &metrics).await?; }
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
                                send_delivery(&mut connection, delivery, &metrics).await?;
                            }
                        }
                        Packet::PubRec(id) => {
                            for delivery in router.ack(&session, AckKind::Rec, id).await? {
                                send_delivery(&mut connection, delivery, &metrics).await?;
                            }
                        }
                        Packet::PubComp(id) => {
                            for delivery in router.ack(&session, AckKind::Comp, id).await? {
                                send_delivery(&mut connection, delivery, &metrics).await?;
                            }
                        }
                        Packet::PingReq => connection.write_all_with_deadline(&encode_pingresp(), WRITE_TIMEOUT).await?,
                        Packet::Disconnect => { graceful = true; break; },
                        Packet::Connect { .. } => return Err("duplicate CONNECT".into()),
                    }
                }
                outbound = session.outbound.recv() => {
                    let Some(delivery) = outbound else { break; };
                    send_delivery(&mut connection, delivery, &metrics).await?;
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
    let _ = connection.shutdown().await;
    result
}

async fn send_delivery(
    connection: &mut BrokerConnection,
    delivery: Delivery,
    metrics: &Metrics,
) -> Result<(), HandlerError> {
    let bytes = match delivery {
        Delivery::Publish {
            message,
            packet_id,
            dup,
        } => encode_publish(
            message.topic.as_str(),
            &message.payload,
            Qos::from_u8(message.qos)?,
            message.retain,
            dup,
            packet_id,
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
