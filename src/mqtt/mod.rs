//! MQTT 3.1.1 session handler with bounded `QoS` 0/1/2, retained messages
//! and durable CleanSession=0 state. Exact topic names only; Will is not yet
//! accepted, so this is not a full MQTT 3.1.1 implementation.

mod codec;
mod router;
mod store;

pub use router::Router;

use std::{sync::Arc, time::Duration};

use tokio::time::{Instant, sleep_until};
use tracing::{debug, warn};

use crate::{
    auth::AccessPolicy,
    transport::{BrokerConnection, HandlerError},
};
use codec::{
    FrameReader, Packet, Qos, encode_connack, encode_connack_with_session, encode_pingresp,
    encode_puback, encode_pubcomp, encode_publish, encode_pubrec, encode_pubrel, encode_suback,
    encode_unsuback, valid_exact_topic,
};
use router::{AckKind, Delivery, RouterError};
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
    let mut reader = FrameReader::new(connection.take_initial_mqtt_bytes());
    let connect = reader
        .read_packet(&mut connection, Instant::now() + CONNECT_TIMEOUT)
        .await?;
    let Packet::Connect {
        client_id,
        clean_session,
        keep_alive,
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
        connection
            .write_all_with_deadline(&encode_connack(5), WRITE_TIMEOUT)
            .await?;
        return Ok(());
    };
    let mut session = match router
        .register(client_id, principal.clone(), clean_session)
        .await
    {
        Ok(session) => session,
        Err(RouterError::PrincipalMismatch) => {
            connection
                .write_all_with_deadline(&encode_connack(5), WRITE_TIMEOUT)
                .await?;
            return Ok(());
        }
        Err(error) => return Err(error.into()),
    };
    let connack = encode_connack_with_session(0, session.resumed)?;
    if let Err(error) = connection
        .write_all_with_deadline(&connack, WRITE_TIMEOUT)
        .await
    {
        router.unregister(&session).await;
        return Err(error.into());
    }
    debug!(
        connection_id = connection.id(),
        "MQTT client accepted by access policy"
    );

    let mut last_inbound = Instant::now();
    let result: Result<(), HandlerError> = async {
        for delivery in session.replay.drain(..) {
            send_delivery(&mut connection, delivery).await?;
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
                            let requested = filters.into_iter().map(|(topic,qos)| {
                                let granted = (valid_exact_topic(&topic) && auth.allowed_subscribe(&principal, &topic)).then_some(qos.as_u8());
                                (topic, granted)
                            }).collect();
                            let (codes, retained) = router.subscribe(&session, requested).await?;
                            connection.write_all_with_deadline(&encode_suback(packet_id, &codes), WRITE_TIMEOUT).await?;
                            for delivery in retained { send_delivery(&mut connection, delivery).await?; }
                        }
                        Packet::Unsubscribe { packet_id, filters } => {
                            router.unsubscribe(&session, filters).await?;
                            connection.write_all_with_deadline(&encode_unsuback(packet_id), WRITE_TIMEOUT).await?;
                        }
                        Packet::Publish { topic, payload, qos, retain, dup, packet_id } => {
                            // DUP is a PUBLISH retransmission hint, not an application dedup key.
                            let _ = dup;
                            if !auth.allowed_publish(&principal, &topic) {
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
                                send_delivery(&mut connection, delivery).await?;
                            }
                        }
                        Packet::PubRec(id) => {
                            for delivery in router.ack(&session, AckKind::Rec, id).await? {
                                send_delivery(&mut connection, delivery).await?;
                            }
                        }
                        Packet::PubComp(id) => {
                            for delivery in router.ack(&session, AckKind::Comp, id).await? {
                                send_delivery(&mut connection, delivery).await?;
                            }
                        }
                        Packet::PingReq => connection.write_all_with_deadline(&encode_pingresp(), WRITE_TIMEOUT).await?,
                        Packet::Disconnect => break,
                        Packet::Connect { .. } => return Err("duplicate CONNECT".into()),
                    }
                }
                outbound = session.outbound.recv() => {
                    let Some(delivery) = outbound else { break; };
                    send_delivery(&mut connection, delivery).await?;
                }
            }
        }
        Ok(())
    }.await;
    router.unregister(&session).await;
    let _ = connection.shutdown().await;
    result
}

async fn send_delivery(
    connection: &mut BrokerConnection,
    delivery: Delivery,
) -> Result<(), HandlerError> {
    let bytes = match delivery {
        Delivery::Publish {
            message,
            packet_id,
            dup,
        } => encode_publish(
            &message.topic,
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
    Ok(())
}
