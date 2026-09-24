//! Single-owner MQTT session actor. A candidate state is fsynced before ACKs
//! or fan-out, so no async mutex is held across storage I/O.

use std::{collections::BTreeMap, path::Path};

use thiserror::Error;
use tokio::sync::{mpsc, oneshot, watch};

use crate::auth::AccessPolicy;
use crate::transport::HandlerError;

use super::store::{
    DurableSession, DurableState, InboundQos2, MqttStore, OutboundInflight, OutboundStage,
    StateError, StoredMessage,
};

const COMMAND_CAPACITY: usize = 256;
const DELIVERY_CAPACITY: usize = 64;
const MAX_INFLIGHT: usize = 32;

#[derive(Debug, Error)]
pub(super) enum RouterError {
    #[error(transparent)]
    Store(#[from] StateError),
    #[error("session identity does not match the stored owner")]
    PrincipalMismatch,
    #[error("stale or disconnected MQTT session")]
    Stale,
    #[error("session actor unavailable")]
    Unavailable,
}

/// A packet to send to a connected subscriber after the durable transition.
#[derive(Clone, Debug)]
pub(super) enum Delivery {
    Publish {
        message: StoredMessage,
        packet_id: Option<u16>,
        dup: bool,
    },
    PubRel(u16),
}

type SubscribeResult = Result<(Vec<u8>, Vec<Delivery>), RouterError>;

pub(super) struct Session {
    pub client_id: String,
    pub generation: u64,
    pub resumed: bool,
    pub outbound: mpsc::Receiver<Delivery>,
    pub closed: watch::Receiver<bool>,
    pub replay: Vec<Delivery>,
}

struct Live {
    generation: u64,
    sender: mpsc::Sender<Delivery>,
    close: watch::Sender<bool>,
}

struct Actor {
    store: MqttStore,
    state: DurableState,
    live: BTreeMap<String, Live>,
    next_generation: u64,
    fatal: bool,
    commits_since_snapshot: u64,
}

enum Command {
    Register {
        client_id: String,
        principal: String,
        clean: bool,
        reply: oneshot::Sender<Result<Session, RouterError>>,
    },
    Subscribe {
        client_id: String,
        generation: u64,
        filters: Vec<(String, Option<u8>)>,
        reply: oneshot::Sender<SubscribeResult>,
    },
    Unsubscribe {
        client_id: String,
        generation: u64,
        filters: Vec<String>,
        reply: oneshot::Sender<Result<(), RouterError>>,
    },
    Publish {
        client_id: String,
        generation: u64,
        message: StoredMessage,
        packet_id: Option<u16>,
        reply: oneshot::Sender<Result<(), RouterError>>,
    },
    PubRel {
        client_id: String,
        generation: u64,
        packet_id: u16,
        reply: oneshot::Sender<Result<(), RouterError>>,
    },
    Ack {
        client_id: String,
        generation: u64,
        kind: AckKind,
        packet_id: u16,
        reply: oneshot::Sender<Result<Vec<Delivery>, RouterError>>,
    },
    Unregister {
        client_id: String,
        generation: u64,
    },
}

#[derive(Clone, Copy)]
pub(super) enum AckKind {
    Ack,
    Rec,
    Comp,
}

/// Bounded command mailbox for one durable session owner. No caller accesses
/// the state map directly, and every mutation is serialized by the actor.
#[derive(Clone)]
pub struct Router {
    sender: mpsc::Sender<Command>,
}

impl Router {
    /// Recover durable state and start the session actor before binding TCP.
    ///
    /// # Errors
    /// Returns a storage error for corruption, incompatible version or an
    /// unavailable persistence directory. Clean-session images are purged.
    pub async fn start(
        directory: &Path,
        auth: std::sync::Arc<AccessPolicy>,
    ) -> Result<Self, HandlerError> {
        let (store, mut state) = MqttStore::open(directory).await?;
        let before = state.clone();
        state
            .sessions
            .retain(|_, session| session.persistent && auth.contains_principal(&session.principal));
        for session in state.sessions.values_mut() {
            session
                .subscriptions
                .retain(|topic, _| auth.allowed_subscribe(&session.principal, topic));
            session
                .offline
                .retain(|message| auth.allowed_subscribe(&session.principal, &message.topic));
            session
                .outbound
                .retain(|entry| auth.allowed_subscribe(&session.principal, &entry.message.topic));
            // MQTT-4.3.3-2: PUBREC means the broker has accepted ownership of
            // the Application Message. A later ACL change cannot discard this
            // pending QoS 2 transition; PUBREL finishes under that decision.
            // New PUBLISH packets are checked against the current ACL in the
            // connection handler. Removed principals still lose the session.
        }
        if state != before {
            store.commit(&state).await?;
        }
        let (sender, mut receiver) = mpsc::channel(COMMAND_CAPACITY);
        tokio::spawn(async move {
            let mut actor = Actor {
                store,
                state,
                live: BTreeMap::new(),
                next_generation: 1,
                fatal: false,
                commits_since_snapshot: 0,
            };
            while let Some(command) = receiver.recv().await {
                actor.handle(command).await;
                if actor.fatal {
                    break;
                }
            }
        });
        Ok(Self { sender })
    }

    pub(super) async fn register(
        &self,
        client_id: String,
        principal: String,
        clean: bool,
    ) -> Result<Session, RouterError> {
        let (reply, result) = oneshot::channel();
        self.send(Command::Register {
            client_id,
            principal,
            clean,
            reply,
        })
        .await?;
        result.await.map_err(|_| RouterError::Unavailable)?
    }

    pub(super) async fn subscribe(
        &self,
        session: &Session,
        filters: Vec<(String, Option<u8>)>,
    ) -> Result<(Vec<u8>, Vec<Delivery>), RouterError> {
        let (reply, result) = oneshot::channel();
        self.send(Command::Subscribe {
            client_id: session.client_id.clone(),
            generation: session.generation,
            filters,
            reply,
        })
        .await?;
        result.await.map_err(|_| RouterError::Unavailable)?
    }

    pub(super) async fn unsubscribe(
        &self,
        session: &Session,
        filters: Vec<String>,
    ) -> Result<(), RouterError> {
        let (reply, result) = oneshot::channel();
        self.send(Command::Unsubscribe {
            client_id: session.client_id.clone(),
            generation: session.generation,
            filters,
            reply,
        })
        .await?;
        result.await.map_err(|_| RouterError::Unavailable)?
    }

    pub(super) async fn publish(
        &self,
        session: &Session,
        message: StoredMessage,
        packet_id: Option<u16>,
    ) -> Result<(), RouterError> {
        let (reply, result) = oneshot::channel();
        self.send(Command::Publish {
            client_id: session.client_id.clone(),
            generation: session.generation,
            message,
            packet_id,
            reply,
        })
        .await?;
        result.await.map_err(|_| RouterError::Unavailable)?
    }

    pub(super) async fn pubrel(
        &self,
        session: &Session,
        packet_id: u16,
    ) -> Result<(), RouterError> {
        let (reply, result) = oneshot::channel();
        self.send(Command::PubRel {
            client_id: session.client_id.clone(),
            generation: session.generation,
            packet_id,
            reply,
        })
        .await?;
        result.await.map_err(|_| RouterError::Unavailable)?
    }

    pub(super) async fn ack(
        &self,
        session: &Session,
        kind: AckKind,
        packet_id: u16,
    ) -> Result<Vec<Delivery>, RouterError> {
        let (reply, result) = oneshot::channel();
        self.send(Command::Ack {
            client_id: session.client_id.clone(),
            generation: session.generation,
            kind,
            packet_id,
            reply,
        })
        .await?;
        result.await.map_err(|_| RouterError::Unavailable)?
    }

    pub(super) async fn unregister(&self, session: &Session) {
        let _ = self
            .send(Command::Unregister {
                client_id: session.client_id.clone(),
                generation: session.generation,
            })
            .await;
    }

    async fn send(&self, command: Command) -> Result<(), RouterError> {
        self.sender
            .send(command)
            .await
            .map_err(|_| RouterError::Unavailable)
    }
}

impl Actor {
    async fn handle(&mut self, command: Command) {
        match command {
            Command::Register {
                client_id,
                principal,
                clean,
                reply,
            } => {
                let _ = reply.send(self.register(client_id, principal, clean).await);
            }
            Command::Subscribe {
                client_id,
                generation,
                filters,
                reply,
            } => {
                let _ = reply.send(self.subscribe(&client_id, generation, filters).await);
            }
            Command::Unsubscribe {
                client_id,
                generation,
                filters,
                reply,
            } => {
                let _ = reply.send(self.unsubscribe(&client_id, generation, filters).await);
            }
            Command::Publish {
                client_id,
                generation,
                message,
                packet_id,
                reply,
            } => {
                let _ = reply.send(
                    self.publish(&client_id, generation, message, packet_id)
                        .await,
                );
            }
            Command::PubRel {
                client_id,
                generation,
                packet_id,
                reply,
            } => {
                let _ = reply.send(self.pubrel(&client_id, generation, packet_id).await);
            }
            Command::Ack {
                client_id,
                generation,
                kind,
                packet_id,
                reply,
            } => {
                let _ = reply.send(self.ack(&client_id, generation, kind, packet_id).await);
            }
            Command::Unregister {
                client_id,
                generation,
            } => {
                let _ = self.unregister(&client_id, generation).await;
            }
        }
    }

    async fn commit(&mut self, candidate: DurableState) -> Result<(), RouterError> {
        if let Err(error) = self.store.commit(&candidate).await {
            // The WAL outcome can be uncertain after an I/O error or a cancelled
            // reply. Never continue from stale in-memory state; reopen on restart.
            if !matches!(
                error,
                StateError::Limit(_) | StateError::Malformed | StateError::UnsupportedVersion(_)
            ) {
                self.fail_closed();
            }
            return Err(error.into());
        }
        self.state = candidate;
        self.commits_since_snapshot += 1;
        if self.commits_since_snapshot >= 128 {
            if let Err(error) = self.store.snapshot().await {
                self.fail_closed();
                return Err(error.into());
            }
            self.commits_since_snapshot = 0;
        }
        Ok(())
    }

    fn fail_closed(&mut self) {
        self.fatal = true;
        for live in self.live.values() {
            let _ = live.close.send(true);
        }
    }

    fn current(&self, client_id: &str, generation: u64) -> Result<(), RouterError> {
        match self.live.get(client_id) {
            Some(live) if live.generation == generation => Ok(()),
            _ => Err(RouterError::Stale),
        }
    }

    async fn register(
        &mut self,
        client_id: String,
        principal: String,
        clean: bool,
    ) -> Result<Session, RouterError> {
        let old = self.state.sessions.get(&client_id);
        // A ClientId belongs to its authenticated principal even when the new
        // CONNECT requests a clean session. Never let another principal erase
        // durable state or take over a live connection by reusing that ID.
        if old.is_some_and(|session| session.principal != principal) {
            return Err(RouterError::PrincipalMismatch);
        }
        let session_present = !clean && old.is_some_and(|session| session.persistent);
        let mut candidate = self.state.clone();
        if !session_present {
            candidate
                .sessions
                .insert(client_id.clone(), DurableSession::new(principal, !clean));
        }
        let mut replay = Vec::new();
        if session_present {
            let session = candidate
                .sessions
                .get_mut(&client_id)
                .ok_or(RouterError::Stale)?;
            for record in &session.outbound {
                replay.push(match record.stage {
                    OutboundStage::AwaitPubComp => Delivery::PubRel(record.packet_id),
                    OutboundStage::AwaitPubAck | OutboundStage::AwaitPubRec => Delivery::Publish {
                        message: record.message.clone(),
                        packet_id: Some(record.packet_id),
                        dup: true,
                    },
                });
            }
            drain_offline(session, &mut replay)?;
        }
        self.commit(candidate).await?;
        if let Some(old) = self.live.remove(&client_id) {
            let _ = old.close.send(true);
        }
        let generation = self.next_generation;
        self.next_generation = self.next_generation.wrapping_add(1).max(1);
        let (sender, outbound) = mpsc::channel(DELIVERY_CAPACITY);
        let (close, closed) = watch::channel(false);
        self.live.insert(
            client_id.clone(),
            Live {
                generation,
                sender,
                close,
            },
        );
        Ok(Session {
            client_id,
            generation,
            resumed: session_present,
            outbound,
            closed,
            replay,
        })
    }

    async fn subscribe(
        &mut self,
        client_id: &str,
        generation: u64,
        filters: Vec<(String, Option<u8>)>,
    ) -> Result<(Vec<u8>, Vec<Delivery>), RouterError> {
        self.current(client_id, generation)?;
        let mut candidate = self.state.clone();
        let mut codes = Vec::with_capacity(filters.len());
        let mut deliveries = Vec::new();
        for (topic, granted) in filters {
            let Some(qos) = granted else {
                codes.push(0x80);
                continue;
            };
            candidate
                .sessions
                .get_mut(client_id)
                .ok_or(RouterError::Stale)?
                .subscriptions
                .insert(topic.clone(), qos);
            codes.push(qos);
            if let Some(retained) = candidate.retained.get(&topic).cloned() {
                let mut delivered = retained;
                delivered.qos = delivered.qos.min(qos);
                let session = candidate
                    .sessions
                    .get_mut(client_id)
                    .ok_or(RouterError::Stale)?;
                deliveries.push(prepare_delivery(session, delivered)?);
            }
        }
        self.commit(candidate).await?;
        Ok((codes, deliveries))
    }

    async fn unsubscribe(
        &mut self,
        client_id: &str,
        generation: u64,
        filters: Vec<String>,
    ) -> Result<(), RouterError> {
        self.current(client_id, generation)?;
        let mut candidate = self.state.clone();
        let session = candidate
            .sessions
            .get_mut(client_id)
            .ok_or(RouterError::Stale)?;
        for topic in filters {
            session.subscriptions.remove(&topic);
        }
        self.commit(candidate).await
    }

    async fn publish(
        &mut self,
        client_id: &str,
        generation: u64,
        message: StoredMessage,
        packet_id: Option<u16>,
    ) -> Result<(), RouterError> {
        self.current(client_id, generation)?;
        let mut candidate = self.state.clone();
        if message.qos == 2 {
            let packet_id = packet_id.ok_or(RouterError::Stale)?;
            let session = candidate
                .sessions
                .get_mut(client_id)
                .ok_or(RouterError::Stale)?;
            if session
                .inbound_qos2
                .iter()
                .any(|item| item.packet_id == packet_id)
            {
                return Ok(());
            }
            session
                .inbound_qos2
                .push(InboundQos2 { packet_id, message });
            return self.commit(candidate).await;
        }
        let deliveries = apply_message(&mut candidate, &self.live, &message)?;
        self.commit(candidate).await?;
        self.deliver(deliveries);
        Ok(())
    }

    async fn pubrel(
        &mut self,
        client_id: &str,
        generation: u64,
        packet_id: u16,
    ) -> Result<(), RouterError> {
        self.current(client_id, generation)?;
        let mut candidate = self.state.clone();
        let session = candidate
            .sessions
            .get_mut(client_id)
            .ok_or(RouterError::Stale)?;
        let Some(index) = session
            .inbound_qos2
            .iter()
            .position(|item| item.packet_id == packet_id)
        else {
            return Ok(());
        };
        let pending = session.inbound_qos2.remove(index);
        let deliveries = apply_message(&mut candidate, &self.live, &pending.message)?;
        self.commit(candidate).await?;
        self.deliver(deliveries);
        Ok(())
    }

    async fn ack(
        &mut self,
        client_id: &str,
        generation: u64,
        kind: AckKind,
        packet_id: u16,
    ) -> Result<Vec<Delivery>, RouterError> {
        self.current(client_id, generation)?;
        let mut candidate = self.state.clone();
        let session = candidate
            .sessions
            .get_mut(client_id)
            .ok_or(RouterError::Stale)?;
        let Some(index) = session
            .outbound
            .iter()
            .position(|item| item.packet_id == packet_id)
        else {
            return Ok(Vec::new());
        };
        let stage = session.outbound[index].stage;
        let mut actions = Vec::new();
        match (kind, stage) {
            (AckKind::Ack, OutboundStage::AwaitPubAck)
            | (AckKind::Comp, OutboundStage::AwaitPubComp) => {
                session.outbound.remove(index);
                drain_offline(session, &mut actions)?;
                self.commit(candidate).await?;
                // Earlier publications may already be waiting in this session's
                // mailbox. Append drained offline messages there, not to the
                // ACK caller's direct-write path, preserving publication order.
                self.deliver(
                    actions
                        .into_iter()
                        .map(|delivery| (client_id.to_owned(), delivery))
                        .collect(),
                );
                return Ok(Vec::new());
            }
            (AckKind::Rec, OutboundStage::AwaitPubRec) => {
                // MQTT-4.6.0-4: persist PUBREL replay in PUBREC arrival order.
                // Pending PUBLISH records retain their relative send order.
                let mut record = session.outbound.remove(index);
                record.stage = OutboundStage::AwaitPubComp;
                session.outbound.push(record);
                self.commit(candidate).await?;
                actions.push(Delivery::PubRel(packet_id));
            }
            (AckKind::Rec, OutboundStage::AwaitPubComp) => {
                actions.push(Delivery::PubRel(packet_id));
            }
            _ => return Err(RouterError::Stale),
        }
        Ok(actions)
    }

    async fn unregister(&mut self, client_id: &str, generation: u64) -> Result<(), RouterError> {
        self.current(client_id, generation)?;
        let persistent = self
            .state
            .sessions
            .get(client_id)
            .is_some_and(|session| session.persistent);
        if !persistent {
            let mut candidate = self.state.clone();
            candidate.sessions.remove(client_id);
            self.commit(candidate).await?;
        }
        self.live.remove(client_id);
        Ok(())
    }

    fn deliver(&mut self, deliveries: Vec<(String, Delivery)>) {
        for (client_id, delivery) in deliveries {
            if let Some(live) = self.live.get(&client_id)
                && live.sender.try_send(delivery).is_err()
            {
                let _ = live.close.send(true);
            }
        }
    }
}

fn apply_message(
    state: &mut DurableState,
    live: &BTreeMap<String, Live>,
    message: &StoredMessage,
) -> Result<Vec<(String, Delivery)>, RouterError> {
    if message.retain {
        if message.payload.is_empty() {
            state.retained.remove(&message.topic);
        } else {
            state
                .retained
                .insert(message.topic.clone(), message.clone());
        }
    }
    let mut deliveries = Vec::new();
    for (client_id, session) in &mut state.sessions {
        let Some(&maximum) = session.subscriptions.get(&message.topic) else {
            continue;
        };
        let mut outbound = message.clone();
        outbound.qos = outbound.qos.min(maximum);
        outbound.retain = false;
        if live.contains_key(client_id) {
            if outbound.qos > 0 && session.outbound.len() >= MAX_INFLIGHT {
                session.offline.push_back(outbound);
            } else {
                let delivery = prepare_delivery(session, outbound)?;
                deliveries.push((client_id.clone(), delivery));
            }
        } else if session.persistent && outbound.qos > 0 {
            session.offline.push_back(outbound);
        }
    }
    Ok(deliveries)
}

fn prepare_delivery(
    session: &mut DurableSession,
    message: StoredMessage,
) -> Result<Delivery, RouterError> {
    if message.qos == 0 {
        return Ok(Delivery::Publish {
            message,
            packet_id: None,
            dup: false,
        });
    }
    if session.outbound.len() >= MAX_INFLIGHT {
        return Err(StateError::Limit("outbound inflight").into());
    }
    let packet_id = allocate_packet_id(session)?;
    let stage = if message.qos == 1 {
        OutboundStage::AwaitPubAck
    } else {
        OutboundStage::AwaitPubRec
    };
    session.outbound.push(OutboundInflight {
        packet_id,
        message: message.clone(),
        stage,
    });
    Ok(Delivery::Publish {
        message,
        packet_id: Some(packet_id),
        dup: false,
    })
}

fn drain_offline(
    session: &mut DurableSession,
    actions: &mut Vec<Delivery>,
) -> Result<(), RouterError> {
    while session.outbound.len() < MAX_INFLIGHT {
        let Some(message) = session.offline.pop_front() else {
            break;
        };
        actions.push(prepare_delivery(session, message)?);
    }
    Ok(())
}

fn allocate_packet_id(session: &mut DurableSession) -> Result<u16, RouterError> {
    for _ in 0..=u16::MAX {
        let value = session.next_packet_id;
        session.next_packet_id = value.wrapping_add(1).max(1);
        if value != 0 && !session.outbound.iter().any(|item| item.packet_id == value) {
            return Ok(value);
        }
    }
    Err(StateError::Limit("packet identifiers").into())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::auth::AuthPolicy;
    use argon2::{
        Algorithm, Argon2, Params, Version,
        password_hash::{PasswordHasher, SaltString},
    };
    use sha2::{Digest, Sha256};
    use std::{fmt::Write as _, fs, sync::Arc};
    use tempfile::TempDir;

    async fn actor() -> (TempDir, Actor) {
        let directory = tempfile::tempdir().unwrap();
        let (store, state) = MqttStore::open(directory.path()).await.unwrap();
        (
            directory,
            Actor {
                store,
                state,
                live: BTreeMap::new(),
                next_generation: 1,
                fatal: false,
                commits_since_snapshot: 0,
            },
        )
    }

    fn message(topic: &str, qos: u8, retain: bool, payload: &[u8]) -> StoredMessage {
        StoredMessage {
            topic: topic.into(),
            payload: payload.to_vec(),
            qos,
            retain,
        }
    }

    fn policy(directory: &Path, publish_allowed: bool) -> AuthPolicy {
        let fingerprint = Sha256::digest(b"test-client-cert");
        let mut fingerprint_hex = String::new();
        for byte in fingerprint {
            write!(&mut fingerprint_hex, "{byte:02x}").unwrap();
        }
        let salt = SaltString::encode_b64(b"sixteen-byte-salt").unwrap();
        let params = Params::new(19_456, 2, 1, None).unwrap();
        let hash = Argon2::new(Algorithm::Argon2id, Version::V0x13, params)
            .hash_password(b"test-password", &salt)
            .unwrap()
            .to_string();
        fs::write(
            directory.join("users.toml"),
            format!("[[users]]\nusername = 'user'\ncert_sha256 = 'sha256:{fingerprint_hex}'\npassword_hash = '{hash}'\n"),
        )
        .unwrap();
        let publish = if publish_allowed {
            "['test/state']"
        } else {
            "[]"
        };
        fs::write(
            directory.join("acl.toml"),
            format!(
                "[[rules]]\nusername = 'user'\npublish = {publish}\nsubscribe = ['test/state']\n"
            ),
        )
        .unwrap();
        AuthPolicy::load(&directory.join("users.toml"), &directory.join("acl.toml")).unwrap()
    }

    #[tokio::test]
    async fn accepted_qos2_survives_acl_revocation_after_pubrec_and_restart() {
        // MQTT-4.3.3-2: PUBREC transfers ownership. Revalidating a current ACL
        // must not erase the earlier accepted QoS 2 message before PUBREL.
        let (directory, mut actor) = actor().await;
        let granted = policy(directory.path(), true);
        assert!(granted.allowed_publish("user", "test/state"));
        let subscriber = actor
            .register("sub".into(), "user".into(), false)
            .await
            .unwrap();
        actor
            .subscribe(
                "sub",
                subscriber.generation,
                vec![("test/state".into(), Some(2))],
            )
            .await
            .unwrap();
        actor
            .unregister("sub", subscriber.generation)
            .await
            .unwrap();
        let publisher = actor
            .register("pub".into(), "user".into(), false)
            .await
            .unwrap();
        actor
            .publish(
                "pub",
                publisher.generation,
                message("test/state", 2, false, b"accepted-before-revocation"),
                Some(41),
            )
            .await
            .unwrap();
        assert_eq!(actor.state.sessions["pub"].inbound_qos2.len(), 1);
        actor.store.shutdown().await.unwrap();

        let revoked = policy(directory.path(), false);
        assert!(!revoked.allowed_publish("user", "test/state"));
        let router = Router::start(directory.path(), Arc::new(AccessPolicy::secure(revoked)))
            .await
            .unwrap();
        let mut subscriber_after_restart = router
            .register("sub".into(), "user".into(), false)
            .await
            .unwrap();
        let sender_after_restart = router
            .register("pub".into(), "user".into(), false)
            .await
            .unwrap();
        assert!(sender_after_restart.resumed);
        router.pubrel(&sender_after_restart, 41).await.unwrap();
        let Delivery::Publish { message, .. } =
            subscriber_after_restart.outbound.try_recv().unwrap()
        else {
            panic!("accepted QoS 2 publication was not routed");
        };
        assert_eq!(message.payload, b"accepted-before-revocation");
        router.pubrel(&sender_after_restart, 41).await.unwrap();
        assert!(subscriber_after_restart.outbound.try_recv().is_err());
    }

    #[tokio::test]
    async fn qos2_routes_once_after_pubrel_and_retained_delete_is_durable() {
        let (directory, mut actor) = actor().await;
        let mut subscriber = actor
            .register("sub".into(), "user".into(), false)
            .await
            .unwrap();
        let publisher = actor
            .register("pub".into(), "user".into(), false)
            .await
            .unwrap();
        let (codes, _) = actor
            .subscribe(
                "sub",
                subscriber.generation,
                vec![("test/state".into(), Some(2))],
            )
            .await
            .unwrap();
        assert_eq!(codes, [2]);
        let retained = message("test/state", 2, true, b"on");
        actor
            .publish("pub", publisher.generation, retained.clone(), Some(7))
            .await
            .unwrap();
        actor
            .publish("pub", publisher.generation, retained, Some(7))
            .await
            .unwrap();
        assert!(subscriber.outbound.try_recv().is_err());
        assert!(actor.state.retained.is_empty());
        actor.pubrel("pub", publisher.generation, 7).await.unwrap();
        assert!(matches!(
            subscriber.outbound.try_recv(),
            Ok(Delivery::Publish {
                packet_id: Some(_),
                ..
            })
        ));
        actor.pubrel("pub", publisher.generation, 7).await.unwrap();
        assert!(subscriber.outbound.try_recv().is_err());
        assert_eq!(actor.state.retained["test/state"].payload, b"on");
        actor
            .publish(
                "pub",
                publisher.generation,
                message("test/state", 1, true, b""),
                Some(8),
            )
            .await
            .unwrap();
        assert!(!actor.state.retained.contains_key("test/state"));
        actor.store.shutdown().await.unwrap();
        let (reopened, state) = MqttStore::open(directory.path()).await.unwrap();
        assert!(!state.retained.contains_key("test/state"));
        reopened.shutdown().await.unwrap();
    }

    #[tokio::test]
    async fn ack_drain_preserves_publication_order_across_inflight_limit() {
        // MQTT-4.6.0-6: an ordered topic stream cannot be overtaken by the
        // 33rd publication when the first of 32 inflight messages is ACKed.
        let (_directory, mut actor) = actor().await;
        let mut subscriber = actor
            .register("ordered-sub".into(), "user".into(), false)
            .await
            .unwrap();
        let publisher = actor
            .register("ordered-pub".into(), "user".into(), true)
            .await
            .unwrap();
        actor
            .subscribe(
                "ordered-sub",
                subscriber.generation,
                vec![("test/ordered".into(), Some(1))],
            )
            .await
            .unwrap();
        for sequence in 0_u8..33 {
            actor
                .publish(
                    "ordered-pub",
                    publisher.generation,
                    message("test/ordered", 1, false, &[sequence]),
                    Some(u16::from(sequence) + 1),
                )
                .await
                .unwrap();
        }
        assert_eq!(actor.state.sessions["ordered-sub"].offline.len(), 1);
        let first_id = actor.state.sessions["ordered-sub"].outbound[0].packet_id;
        assert!(
            actor
                .ack("ordered-sub", subscriber.generation, AckKind::Ack, first_id)
                .await
                .unwrap()
                .is_empty()
        );
        let mut received = Vec::new();
        for _ in 0..33 {
            let Delivery::Publish { message, .. } = subscriber.outbound.try_recv().unwrap() else {
                panic!("unexpected PUBREL");
            };
            received.push(message.payload[0]);
        }
        assert_eq!(received, (0_u8..33).collect::<Vec<_>>());
        assert!(subscriber.outbound.try_recv().is_err());
        actor.store.shutdown().await.unwrap();
    }

    #[tokio::test]
    async fn qos2_pubrel_replay_follows_pubrec_arrival_order_after_reopen() {
        // MQTT-4.6.0-4: PUBREL order follows PUBREC order, even after restart.
        let (directory, mut actor) = actor().await;
        let subscriber = actor
            .register("qos2-sub".into(), "user".into(), false)
            .await
            .unwrap();
        let publisher = actor
            .register("qos2-pub".into(), "user".into(), true)
            .await
            .unwrap();
        actor
            .subscribe(
                "qos2-sub",
                subscriber.generation,
                vec![("test/qos2-order".into(), Some(2))],
            )
            .await
            .unwrap();
        for sequence in 0_u8..2 {
            let packet_id = u16::from(sequence) + 1;
            actor
                .publish(
                    "qos2-pub",
                    publisher.generation,
                    message("test/qos2-order", 2, false, &[sequence]),
                    Some(packet_id),
                )
                .await
                .unwrap();
            actor
                .pubrel("qos2-pub", publisher.generation, packet_id)
                .await
                .unwrap();
        }
        let outbound = &actor.state.sessions["qos2-sub"].outbound;
        let first_id = outbound[0].packet_id;
        let second_id = outbound[1].packet_id;
        actor
            .ack("qos2-sub", subscriber.generation, AckKind::Rec, second_id)
            .await
            .unwrap();
        actor
            .ack("qos2-sub", subscriber.generation, AckKind::Rec, first_id)
            .await
            .unwrap();
        actor.store.shutdown().await.unwrap();

        let (store, state) = MqttStore::open(directory.path()).await.unwrap();
        let mut reopened = Actor {
            store,
            state,
            live: BTreeMap::new(),
            next_generation: 1,
            fatal: false,
            commits_since_snapshot: 0,
        };
        let resumed = reopened
            .register("qos2-sub".into(), "user".into(), false)
            .await
            .unwrap();
        assert!(resumed.resumed);
        assert!(
            matches!(resumed.replay.as_slice(), [Delivery::PubRel(a), Delivery::PubRel(b)] if *a == second_id && *b == first_id)
        );
        reopened.store.shutdown().await.unwrap();
    }

    #[tokio::test]
    async fn persistent_subscription_and_offline_qos_survive_reopen() {
        let (directory, mut actor) = actor().await;
        let subscriber = actor
            .register("sub".into(), "user".into(), false)
            .await
            .unwrap();
        actor
            .subscribe(
                "sub",
                subscriber.generation,
                vec![("test/offline".into(), Some(2))],
            )
            .await
            .unwrap();
        actor
            .unregister("sub", subscriber.generation)
            .await
            .unwrap();
        let publisher = actor
            .register("pub".into(), "user".into(), true)
            .await
            .unwrap();
        actor
            .publish(
                "pub",
                publisher.generation,
                message("test/offline", 1, false, b"queued"),
                Some(9),
            )
            .await
            .unwrap();
        assert_eq!(actor.state.sessions["sub"].offline.len(), 1);
        actor.store.shutdown().await.unwrap();
        let (store, state) = MqttStore::open(directory.path()).await.unwrap();
        let mut reopened = Actor {
            store,
            state,
            live: BTreeMap::new(),
            next_generation: 1,
            fatal: false,
            commits_since_snapshot: 0,
        };
        let resumed = reopened
            .register("sub".into(), "user".into(), false)
            .await
            .unwrap();
        assert!(resumed.resumed);
        assert_eq!(resumed.replay.len(), 1);
        assert!(
            matches!(&resumed.replay[0], Delivery::Publish { message, packet_id: Some(_), dup: false } if message.payload == b"queued")
        );
        reopened.store.shutdown().await.unwrap();
    }

    #[tokio::test]
    async fn clean_session_removed_and_denied_filter_not_persisted() {
        let (_directory, mut actor) = actor().await;
        let client = actor
            .register("clean".into(), "user".into(), true)
            .await
            .unwrap();
        let (codes, _) = actor
            .subscribe(
                "clean",
                client.generation,
                vec![("test/secret".into(), None)],
            )
            .await
            .unwrap();
        assert_eq!(codes, [0x80]);
        assert!(actor.state.sessions["clean"].subscriptions.is_empty());
        actor.unregister("clean", client.generation).await.unwrap();
        assert!(!actor.state.sessions.contains_key("clean"));
        actor.store.shutdown().await.unwrap();
    }

    #[tokio::test]
    async fn clean_connect_cannot_erase_another_principals_session() {
        let (_directory, mut actor) = actor().await;
        let victim = actor
            .register("shared-id".into(), "victim".into(), false)
            .await
            .unwrap();
        actor
            .subscribe(
                "shared-id",
                victim.generation,
                vec![("test/private".into(), Some(1))],
            )
            .await
            .unwrap();
        assert!(matches!(
            actor
                .register("shared-id".into(), "attacker".into(), true)
                .await,
            Err(RouterError::PrincipalMismatch)
        ));
        assert_eq!(actor.state.sessions["shared-id"].principal, "victim");
        assert_eq!(actor.state.sessions["shared-id"].subscriptions.len(), 1);
        assert!(actor.current("shared-id", victim.generation).is_ok());
        actor.store.shutdown().await.unwrap();
    }
}
