//! Single-owner MQTT session actor. A candidate state is fsynced before ACKs
//! or fan-out, so no async mutex is held across storage I/O.

use std::{collections::BTreeMap, path::Path};

use thiserror::Error;
use tokio::sync::{mpsc, oneshot, watch};

use crate::auth::{AccessPolicy, AuthPolicy};
use crate::monitoring::{Metrics, Rejection};
use crate::transport::HandlerError;
use std::sync::{Arc, atomic::Ordering};

use super::store::{
    DurableSession, DurableState, InboundQos2, MqttStore, OutboundInflight, OutboundStage,
    PendingWill, StateError, StoredMessage,
};
use super::topic::TopicFilter;

const COMMAND_CAPACITY: usize = 256;
const DELIVERY_CAPACITY: usize = 64;
const MAX_INFLIGHT: usize = 32;

#[derive(Debug, Error)]
pub(super) enum RouterError {
    #[error(transparent)]
    Store(#[from] StateError),
    #[error("security generation changed or reload unavailable")]
    Security,
    #[error("session identity does not match the stored owner")]
    PrincipalMismatch,
    #[error("Will publication denied by access policy")]
    WillDenied,
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

#[derive(Clone)]
struct Live {
    generation: u64,
    sender: mpsc::Sender<Delivery>,
    close: watch::Sender<bool>,
}

struct Actor {
    metrics: Arc<Metrics>,
    store: MqttStore,
    state: DurableState,
    auth: std::sync::Arc<AccessPolicy>,
    live: BTreeMap<String, Live>,
    next_generation: u64,
    fatal: bool,
    commits_since_snapshot: u64,
}

enum Command {
    Shutdown {
        reply: oneshot::Sender<Result<(), RouterError>>,
    },
    #[cfg_attr(not(unix), allow(dead_code))]
    SecurityReload {
        candidate: AuthPolicy,
        reply: oneshot::Sender<Result<u64, RouterError>>,
    },
    Probe {
        reply: oneshot::Sender<bool>,
    },
    #[cfg(test)]
    Stop,
    Register {
        security_generation: Option<u64>,
        client_id: String,
        principal: String,
        clean: bool,
        will: Option<StoredMessage>,
        reply: oneshot::Sender<Result<Session, RouterError>>,
    },
    Subscribe {
        client_id: String,
        generation: u64,
        filters: Vec<(TopicFilter, Option<u8>)>,
        reply: oneshot::Sender<SubscribeResult>,
    },
    Unsubscribe {
        client_id: String,
        generation: u64,
        filters: Vec<TopicFilter>,
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
        graceful: bool,
        reply: oneshot::Sender<Result<(), RouterError>>,
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
    metrics: Arc<Metrics>,
    sender: mpsc::Sender<Command>,
}

/// Ensures handler cancellation/panic also closes its accepted connection.
/// If the runtime itself disappears, the durable pending Will survives restart.
pub(super) struct ConnectionGuard {
    router: Router,
    client_id: String,
    generation: u64,
    armed: bool,
}

impl ConnectionGuard {
    pub(super) fn disarm(&mut self) {
        self.armed = false;
    }
}

impl Drop for ConnectionGuard {
    fn drop(&mut self) {
        if !self.armed {
            return;
        }
        let router = self.router.clone();
        let client_id = self.client_id.clone();
        let generation = self.generation;
        if let Ok(runtime) = tokio::runtime::Handle::try_current() {
            runtime.spawn(async move {
                let (reply, result) = oneshot::channel();
                let _ = router
                    .send(Command::Unregister {
                        client_id,
                        generation,
                        graceful: false,
                        reply,
                    })
                    .await;
                let _ = result.await;
            });
        }
    }
}

impl Router {
    /// Drain prior commands, preserve sessions, publish Wills and stop storage.
    /// # Errors
    /// Returns an error when the actor or durable storage cannot complete shutdown.
    pub async fn shutdown(&self) -> Result<(), HandlerError> {
        let (reply, result) = oneshot::channel();
        self.send(Command::Shutdown { reply }).await?;
        result
            .await
            .map_err(|_| RouterError::Unavailable)?
            .map_err(Into::into)
    }

    pub(super) fn connection_guard(&self, session: &Session) -> ConnectionGuard {
        ConnectionGuard {
            router: self.clone(),
            client_id: session.client_id.clone(),
            generation: session.generation,
            armed: true,
        }
    }
    /// Recover durable state and start the session actor before binding TCP.
    ///
    /// # Errors
    /// Returns a storage error for corruption, incompatible version or an
    /// unavailable persistence directory. Clean-session images are purged.
    pub async fn start(directory: &Path, auth: Arc<AccessPolicy>) -> Result<Self, HandlerError> {
        Self::start_observed(directory, auth, Arc::default()).await
    }

    /// Recover and start the actor with shared, bounded process metrics.
    /// # Errors
    /// Returns corruption, recovery, quota or unavailable storage errors.
    pub async fn start_observed(
        directory: &Path,
        auth: Arc<AccessPolicy>,
        metrics: Arc<Metrics>,
    ) -> Result<Self, HandlerError> {
        let (store, mut state) = MqttStore::open(directory).await?;
        let before = state.clone();
        state
            .sessions
            .retain(|_, session| session.persistent && auth.contains_principal(&session.principal));
        for session in state.sessions.values_mut() {
            session
                .subscriptions
                .retain(|filter, _| auth.allowed_subscribe(&session.principal, filter.as_str()));
            session.offline.retain(|message| {
                auth.allowed_delivery(&session.principal, message.topic.as_str())
            });
            session.outbound.retain(|entry| {
                auth.allowed_delivery(&session.principal, entry.message.topic.as_str())
            });
            // MQTT-4.3.3-2: PUBREC means the broker has accepted ownership of
            // the Application Message. A later ACL change cannot discard this
            // pending QoS 2 transition; PUBREL finishes under that decision.
            // New PUBLISH packets are checked against the current ACL in the
            // connection handler. Removed principals still lose the session.
        }
        // MQTT-3.1.2-8/10: broker crash can defer Will publication until restart.
        // Remove the Will and route it in the same durable transition.
        let mut recovered_wills = 0_u64;
        let pending = std::mem::take(&mut state.pending_wills);
        for will in pending.into_values() {
            if auth.allowed_publish(&will.principal, will.message.topic.as_str()) {
                apply_message(&mut state, &BTreeMap::new(), &auth, &will.message)?;
                recovered_wills += 1;
            }
        }
        if state != before {
            let start = std::time::Instant::now();
            store.commit(&state).await?;
            metrics.commit_attempts.fetch_add(1, Ordering::Relaxed);
            metrics.commit_nanos.fetch_add(
                u64::try_from(start.elapsed().as_nanos()).unwrap_or(u64::MAX),
                Ordering::Relaxed,
            );
            metrics.commits.fetch_add(1, Ordering::Relaxed);
        }
        metrics.wills.fetch_add(recovered_wills, Ordering::Relaxed);
        let (sender, mut receiver) = mpsc::channel(COMMAND_CAPACITY);
        let actor_metrics = metrics.clone();
        tokio::spawn(async move {
            let _actor_metric = actor_metrics.actor();
            let mut actor = Actor {
                metrics: actor_metrics,
                store,
                state,
                auth,
                live: BTreeMap::new(),
                next_generation: 1,
                fatal: false,
                commits_since_snapshot: 0,
            };
            while let Some(command) = receiver.recv().await {
                if let Command::Shutdown { reply } = command {
                    receiver.close();
                    let result = actor.shutdown().await;
                    actor.fail_closed();
                    let _ = reply.send(result);
                    break;
                }
                actor.handle(command).await;
                if actor.fatal {
                    break;
                }
            }
        });
        Ok(Self { metrics, sender })
    }

    #[cfg_attr(not(unix), allow(dead_code))]
    pub(crate) async fn reload_security(&self, candidate: AuthPolicy) -> Result<u64, HandlerError> {
        let (reply, result) = oneshot::channel();
        self.sender
            .try_send(Command::SecurityReload { candidate, reply })
            .map_err(|_| RouterError::Unavailable)?;
        result
            .await
            .map_err(|_| RouterError::Unavailable)?
            .map_err(Into::into)
    }

    pub(crate) fn metrics(&self) -> Arc<Metrics> {
        self.metrics.clone()
    }

    pub(crate) async fn probe(&self) -> bool {
        let (reply, result) = oneshot::channel();
        if self.sender.try_send(Command::Probe { reply }).is_err() {
            return false;
        }
        let ready = result.await.unwrap_or(false);
        self.metrics.commands_queued.store(
            u64::try_from(self.sender.max_capacity() - self.sender.capacity()).unwrap_or(u64::MAX),
            Ordering::Relaxed,
        );
        ready && self.metrics.actor_alive.load(Ordering::Relaxed)
    }

    #[cfg(test)]
    pub(crate) async fn stop_for_test(&self) {
        let _ = self.sender.send(Command::Stop).await;
        self.sender.closed().await;
    }

    #[cfg(test)]
    pub(super) async fn register(
        &self,
        client_id: String,
        principal: String,
        clean: bool,
    ) -> Result<Session, RouterError> {
        self.register_with_will(client_id, principal, clean, None)
            .await
    }

    #[cfg(test)]
    pub(super) async fn register_with_will(
        &self,
        client_id: String,
        principal: String,
        clean: bool,
        will: Option<StoredMessage>,
    ) -> Result<Session, RouterError> {
        self.register_with_epoch(client_id, principal, clean, will, None)
            .await
    }

    pub(super) async fn register_with_epoch(
        &self,
        client_id: String,
        principal: String,
        clean: bool,
        will: Option<StoredMessage>,
        security_generation: Option<u64>,
    ) -> Result<Session, RouterError> {
        let (reply, result) = oneshot::channel();
        self.send(Command::Register {
            security_generation,
            client_id,
            principal,
            clean,
            will,
            reply,
        })
        .await?;
        result.await.map_err(|_| RouterError::Unavailable)?
    }

    pub(super) async fn subscribe(
        &self,
        session: &Session,
        filters: Vec<(TopicFilter, Option<u8>)>,
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
        filters: Vec<TopicFilter>,
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

    pub(super) async fn unregister(
        &self,
        session: &Session,
        graceful: bool,
    ) -> Result<(), RouterError> {
        let (reply, result) = oneshot::channel();
        self.send(Command::Unregister {
            client_id: session.client_id.clone(),
            generation: session.generation,
            graceful,
            reply,
        })
        .await?;
        result.await.map_err(|_| RouterError::Unavailable)?
    }

    async fn send(&self, command: Command) -> Result<(), RouterError> {
        self.sender
            .send(command)
            .await
            .map_err(|_| RouterError::Unavailable)
    }
}

impl Actor {
    async fn shutdown(&mut self) -> Result<(), RouterError> {
        // Server stop is not a client DISCONNECT (MQTT-3.1.2-8/-10).
        // Publish all Wills against an offline view so durable subscribers
        // retain deliveries instead of losing them with the closing sockets.
        let mut candidate = self.state.clone();
        candidate.sessions.retain(|_, session| session.persistent);
        let mut published = 0;
        for will in std::mem::take(&mut candidate.pending_wills).into_values() {
            if self
                .auth
                .allowed_publish(&will.principal, will.message.topic.as_str())
            {
                apply_message(&mut candidate, &BTreeMap::new(), &self.auth, &will.message)?;
                published += 1;
            }
        }
        self.commit(candidate).await?;
        self.metrics.wills.fetch_add(published, Ordering::Relaxed);
        self.store.snapshot().await?;
        self.store.shutdown().await?;
        Ok(())
    }

    async fn reload_security(&mut self, policy: AuthPolicy) -> Result<u64, RouterError> {
        let dynamic = self.auth.dynamic().ok_or(RouterError::Security)?;
        if dynamic.generation() == u64::MAX {
            return Err(RouterError::Security);
        }
        let view = dynamic.view(policy.clone());
        let mut candidate = self.state.clone();
        candidate.sessions.retain(|_, s| s.persistent);
        for session in candidate.sessions.values_mut() {
            session
                .subscriptions
                .retain(|filter, _| view.allowed_subscribe(&session.principal, filter.as_str()));
            session
                .offline
                .retain(|m| view.allowed_delivery(&session.principal, m.topic.as_str()));
            session
                .outbound
                .retain(|m| view.allowed_delivery(&session.principal, m.message.topic.as_str()));
            // Accepted inbound QoS2 remains owned, even while credentials are revoked.
        }
        let mut published = 0;
        for will in std::mem::take(&mut candidate.pending_wills).into_values() {
            if view.allowed_publish(&will.principal, will.message.topic.as_str()) {
                apply_message(&mut candidate, &BTreeMap::new(), &view, &will.message)?;
                published += 1;
            }
        }
        self.commit(candidate).await?;
        let Ok(generation) = dynamic.publish(policy) else {
            self.fail_closed();
            return Err(RouterError::Security);
        };
        self.metrics.wills.fetch_add(published, Ordering::Relaxed);
        for (_, live) in std::mem::take(&mut self.live) {
            let _ = live.close.send(true);
        }
        self.update_metrics();
        Ok(generation)
    }
    async fn probe(&mut self) -> bool {
        let ready = self.store.probe().await.is_ok() && !self.fatal;
        if !ready {
            self.metrics
                .persistence_errors
                .fetch_add(1, Ordering::Relaxed);
            self.metrics.reject(Rejection::Persistence);
            self.fail_closed();
        }
        self.update_metrics();
        ready
    }
    async fn handle(&mut self, command: Command) {
        match command {
            Command::Shutdown { .. } => unreachable!("shutdown handled by actor loop"),
            #[cfg(test)]
            Command::Stop => self.fail_closed(),
            Command::Probe { reply } => {
                let ready = self.probe().await;
                let _ = reply.send(ready);
            }
            Command::SecurityReload { candidate, reply } => {
                let result = self.reload_security(candidate).await;
                let _ = reply.send(result);
            }
            Command::Register {
                security_generation,
                client_id,
                principal,
                clean,
                will,
                reply,
            } => {
                let result =
                    if security_generation.is_some_and(|g| g != self.auth.security_generation()) {
                        Err(RouterError::Security)
                    } else {
                        self.register_with_will(client_id, principal, clean, will)
                            .await
                    };
                self.record_result(&result);
                let _ = reply.send(result);
            }
            Command::Subscribe {
                client_id,
                generation,
                filters,
                reply,
            } => {
                let result = self.subscribe(&client_id, generation, filters).await;
                self.record_result(&result);
                let _ = reply.send(result);
            }
            Command::Unsubscribe {
                client_id,
                generation,
                filters,
                reply,
            } => {
                let result = self.unsubscribe(&client_id, generation, filters).await;
                self.record_result(&result);
                let _ = reply.send(result);
            }
            Command::Publish {
                client_id,
                generation,
                message,
                packet_id,
                reply,
            } => {
                let result = self
                    .publish(&client_id, generation, message, packet_id)
                    .await;
                self.record_result(&result);
                let _ = reply.send(result);
            }
            Command::PubRel {
                client_id,
                generation,
                packet_id,
                reply,
            } => {
                let result = self.pubrel(&client_id, generation, packet_id).await;
                self.record_result(&result);
                let _ = reply.send(result);
            }
            Command::Ack {
                client_id,
                generation,
                kind,
                packet_id,
                reply,
            } => {
                let result = self.ack(&client_id, generation, kind, packet_id).await;
                self.record_result(&result);
                let _ = reply.send(result);
            }
            Command::Unregister {
                client_id,
                generation,
                graceful,
                reply,
            } => {
                let result = self
                    .unregister_with_reason(&client_id, generation, graceful)
                    .await;
                self.record_result(&result);
                let _ = reply.send(result);
            }
        }
    }

    fn record_result<T>(&self, result: &Result<T, RouterError>) {
        if let Err(error) = result {
            match error {
                RouterError::Store(StateError::Limit(_)) => self.metrics.reject(Rejection::Quota),
                RouterError::WillDenied | RouterError::PrincipalMismatch => {
                    self.metrics.reject(Rejection::Authorization);
                }
                RouterError::Store(StateError::Storage(_) | StateError::WorkerUnavailable) => {
                    self.metrics.reject(Rejection::Persistence);
                }
                _ => {}
            }
        }
    }
    fn update_metrics(&self) {
        fn count(value: usize) -> u64 {
            u64::try_from(value).unwrap_or(u64::MAX)
        }
        self.metrics
            .sessions
            .store(count(self.state.sessions.len()), Ordering::Relaxed);
        self.metrics
            .retained
            .store(count(self.state.retained.len()), Ordering::Relaxed);
        self.metrics.offline.store(
            count(self.state.sessions.values().map(|s| s.offline.len()).sum()),
            Ordering::Relaxed,
        );
        self.metrics.inflight.store(
            count(
                self.state
                    .sessions
                    .values()
                    .map(|s| s.outbound.len() + s.inbound_qos2.len())
                    .sum(),
            ),
            Ordering::Relaxed,
        );
        self.metrics.deliveries_queued.store(
            count(
                self.live
                    .values()
                    .map(|l| l.sender.max_capacity() - l.sender.capacity())
                    .sum(),
            ),
            Ordering::Relaxed,
        );
    }

    async fn commit(&mut self, candidate: DurableState) -> Result<(), RouterError> {
        let started = std::time::Instant::now();
        let result = self.store.commit(&candidate).await;
        self.metrics.commit_attempts.fetch_add(1, Ordering::Relaxed);
        self.metrics.commit_nanos.fetch_add(
            u64::try_from(started.elapsed().as_nanos()).unwrap_or(u64::MAX),
            Ordering::Relaxed,
        );
        if let Err(error) = result {
            // The WAL outcome can be uncertain after an I/O error or a cancelled
            // reply. Never continue from stale in-memory state; reopen on restart.
            if !matches!(
                error,
                StateError::Limit(_) | StateError::Malformed | StateError::UnsupportedVersion(_)
            ) {
                self.metrics
                    .persistence_errors
                    .fetch_add(1, Ordering::Relaxed);
                self.fail_closed();
            }
            return Err(error.into());
        }
        self.metrics.commits.fetch_add(1, Ordering::Relaxed);
        self.state = candidate;
        self.update_metrics();
        self.commits_since_snapshot += 1;
        if self.commits_since_snapshot >= 128 {
            if let Err(error) = self.store.snapshot().await {
                self.metrics
                    .persistence_errors
                    .fetch_add(1, Ordering::Relaxed);
                self.fail_closed();
                return Err(error.into());
            }
            self.metrics.snapshots.fetch_add(1, Ordering::Relaxed);
            self.commits_since_snapshot = 0;
        }
        Ok(())
    }

    fn fail_closed(&mut self) {
        self.fatal = true;
        self.metrics.actor_alive.store(false, Ordering::Relaxed);
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

    #[cfg(test)]
    async fn register(
        &mut self,
        client_id: String,
        principal: String,
        clean: bool,
    ) -> Result<Session, RouterError> {
        self.register_with_will(client_id, principal, clean, None)
            .await
    }

    async fn register_with_will(
        &mut self,
        client_id: String,
        principal: String,
        clean: bool,
        will: Option<StoredMessage>,
    ) -> Result<Session, RouterError> {
        let old = self.state.sessions.get(&client_id);
        // A ClientId belongs to its authenticated principal even when the new
        // CONNECT requests a clean session. Never let another principal erase
        // durable state or take over a live connection by reusing that ID.
        if old.is_some_and(|session| session.principal != principal) {
            return Err(RouterError::PrincipalMismatch);
        }
        if will
            .as_ref()
            .is_some_and(|w| !self.auth.allowed_publish(&principal, w.topic.as_str()))
        {
            return Err(RouterError::WillDenied);
        }
        let session_present = !clean && old.is_some_and(|session| session.persistent);
        if let Some(generation) = self.live.get(&client_id).map(|live| live.generation) {
            // Existing network connection ends abnormally on same-owner takeover.
            self.unregister_with_reason(&client_id, generation, false)
                .await?;
        }
        let mut candidate = self.state.clone();
        if !session_present {
            candidate
                .sessions
                .insert(client_id.clone(), DurableSession::new(principal, !clean));
        }
        if let Some(message) = will {
            candidate.pending_wills.insert(
                client_id.clone(),
                PendingWill {
                    principal: candidate.sessions[&client_id].principal.clone(),
                    message,
                },
            );
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
        filters: Vec<(TopicFilter, Option<u8>)>,
    ) -> Result<(Vec<u8>, Vec<Delivery>), RouterError> {
        self.current(client_id, generation)?;
        let mut candidate = self.state.clone();
        let mut codes = Vec::with_capacity(filters.len());
        let mut retained_matches = BTreeMap::new();
        for (filter, granted) in filters {
            let principal = &self
                .state
                .sessions
                .get(client_id)
                .ok_or(RouterError::Stale)?
                .principal;
            let Some(qos) =
                granted.filter(|_| self.auth.allowed_subscribe(principal, filter.as_str()))
            else {
                self.metrics.reject(Rejection::Authorization);
                codes.push(0x80);
                continue;
            };
            candidate
                .sessions
                .get_mut(client_id)
                .ok_or(RouterError::Stale)?
                .subscriptions
                .insert(filter.clone(), qos);
            codes.push(qos);
            for topic in candidate.retained.keys().filter(|topic| {
                filter.matches(topic) && self.auth.allowed_delivery(principal, topic.as_str())
            }) {
                retained_matches
                    .entry(topic.clone())
                    .and_modify(|maximum: &mut u8| *maximum = (*maximum).max(qos))
                    .or_insert(qos);
            }
        }
        let mut deliveries = Vec::with_capacity(retained_matches.len());
        for (topic, maximum) in retained_matches {
            let mut delivered = candidate
                .retained
                .get(&topic)
                .cloned()
                .ok_or(RouterError::Stale)?;
            delivered.qos = delivered.qos.min(maximum);
            let session = candidate
                .sessions
                .get_mut(client_id)
                .ok_or(RouterError::Stale)?;
            deliveries.push(prepare_delivery(session, delivered)?);
        }
        self.commit(candidate).await?;
        Ok((codes, deliveries))
    }

    async fn unsubscribe(
        &mut self,
        client_id: &str,
        generation: u64,
        filters: Vec<TopicFilter>,
    ) -> Result<(), RouterError> {
        self.current(client_id, generation)?;
        let mut candidate = self.state.clone();
        let session = candidate
            .sessions
            .get_mut(client_id)
            .ok_or(RouterError::Stale)?;
        for filter in filters {
            session.subscriptions.remove(&filter);
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
        let qos = usize::from(message.qos);
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
            self.commit(candidate).await?;
            self.metrics.received[qos].fetch_add(1, Ordering::Relaxed);
            return Ok(());
        }
        let deliveries = apply_message(&mut candidate, &self.live, &self.auth, &message)?;
        self.commit(candidate).await?;
        self.metrics.received[qos].fetch_add(1, Ordering::Relaxed);
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
        let deliveries = apply_message(&mut candidate, &self.live, &self.auth, &pending.message)?;
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

    #[cfg(test)]
    async fn unregister(&mut self, client_id: &str, generation: u64) -> Result<(), RouterError> {
        self.unregister_with_reason(client_id, generation, false)
            .await
    }

    async fn unregister_with_reason(
        &mut self,
        client_id: &str,
        generation: u64,
        graceful: bool,
    ) -> Result<(), RouterError> {
        self.current(client_id, generation)?;
        let mut candidate = self.state.clone();
        let will = candidate.pending_wills.remove(client_id);
        if !candidate
            .sessions
            .get(client_id)
            .is_some_and(|s| s.persistent)
        {
            candidate.sessions.remove(client_id);
        }
        let mut remaining_live = self.live.clone();
        remaining_live.remove(client_id);
        let mut deliveries = Vec::new();
        let mut published = false;
        if let Some(will) = will.filter(|_| !graceful)
            && self
                .auth
                .allowed_publish(&will.principal, will.message.topic.as_str())
        {
            published = true;
            deliveries = apply_message(&mut candidate, &remaining_live, &self.auth, &will.message)?;
        }
        // MQTT-3.1.2-10 and MQTT-3.14.4-3: cancellation/publication is durable.
        self.commit(candidate).await?;
        if published {
            self.metrics.wills.fetch_add(1, Ordering::Relaxed);
        }
        if let Some(old) = self.live.remove(client_id) {
            let _ = old.close.send(true);
        }
        self.deliver(deliveries);
        Ok(())
    }

    fn deliver(&mut self, deliveries: Vec<(String, Delivery)>) {
        for (client_id, delivery) in deliveries {
            if let Some(live) = self.live.get(&client_id)
                && live.sender.try_send(delivery).is_err()
            {
                self.metrics.reject(Rejection::Delivery);
                let _ = live.close.send(true);
            }
        }
    }
}

fn apply_message(
    state: &mut DurableState,
    live: &BTreeMap<String, Live>,
    auth: &AccessPolicy,
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
        if !auth.allowed_delivery(&session.principal, message.topic.as_str()) {
            continue;
        }
        let Some(maximum) = session
            .subscriptions
            .iter()
            .filter(|(filter, _)| filter.matches(&message.topic))
            .map(|(_, qos)| *qos)
            .max()
        else {
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
    use crate::{auth::AuthPolicy, mqtt::topic::TopicName};
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
        let auth = Arc::new(AccessPolicy::password_lab(policy(directory.path(), true)));
        (
            directory,
            Actor {
                metrics: Arc::default(),
                store,
                state,
                auth,
                live: BTreeMap::new(),
                next_generation: 1,
                fatal: false,
                commits_since_snapshot: 0,
            },
        )
    }

    fn message(topic: &str, qos: u8, retain: bool, payload: &[u8]) -> StoredMessage {
        StoredMessage {
            topic: TopicName::try_from(topic.to_owned()).unwrap(),
            payload: payload.to_vec(),
            qos,
            retain,
        }
    }

    fn filter(value: &str) -> TopicFilter {
        TopicFilter::try_from(value.to_owned()).unwrap()
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
                vec![(filter("test/state"), Some(2))],
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
                vec![(filter("test/state"), Some(2))],
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
                vec![(filter("test/ordered"), Some(1))],
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
                vec![(filter("test/qos2-order"), Some(2))],
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
            metrics: Arc::default(),
            store,
            state,
            auth: Arc::clone(&actor.auth),
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
    async fn wildcard_overlap_delivers_once_at_highest_qos_and_deduplicates_retained() {
        // MQTT-3.3.5-1, MQTT-4.7.1-2/3.
        let (_directory, mut actor) = actor().await;
        let mut subscriber = actor
            .register("wildcard-sub".into(), "user".into(), false)
            .await
            .unwrap();
        let publisher = actor
            .register("wildcard-pub".into(), "user".into(), true)
            .await
            .unwrap();
        let (codes, retained) = actor
            .subscribe(
                "wildcard-sub",
                subscriber.generation,
                vec![
                    (filter("sport/#"), Some(1)),
                    (filter("sport/+/score"), Some(2)),
                ],
            )
            .await
            .unwrap();
        assert_eq!(codes, [1, 2]);
        assert!(retained.is_empty());

        actor
            .publish(
                "wildcard-pub",
                publisher.generation,
                message("sport/tennis/score", 2, false, b"15-0"),
                Some(7),
            )
            .await
            .unwrap();
        actor
            .pubrel("wildcard-pub", publisher.generation, 7)
            .await
            .unwrap();
        let Delivery::Publish {
            message: routed, ..
        } = subscriber.outbound.try_recv().unwrap()
        else {
            panic!("unexpected PUBREL");
        };
        assert_eq!(routed.qos, 2);
        assert!(subscriber.outbound.try_recv().is_err());

        actor
            .publish(
                "wildcard-pub",
                publisher.generation,
                message("sport/tennis/state", 1, true, b"online"),
                Some(8),
            )
            .await
            .unwrap();
        let retained_subscriber = actor
            .register("retained-sub".into(), "user".into(), false)
            .await
            .unwrap();
        let (_, retained) = actor
            .subscribe(
                "retained-sub",
                retained_subscriber.generation,
                vec![
                    (filter("sport/#"), Some(1)),
                    (filter("sport/+/state"), Some(2)),
                ],
            )
            .await
            .unwrap();
        assert_eq!(retained.len(), 1);
        let Delivery::Publish {
            message: retained_message,
            ..
        } = &retained[0]
        else {
            panic!("unexpected PUBREL");
        };
        assert_eq!(retained_message.topic.as_str(), "sport/tennis/state");
        actor.store.shutdown().await.unwrap();
    }

    #[tokio::test]
    async fn unsubscribe_removes_only_the_identical_wildcard_filter() {
        let (_directory, mut actor) = actor().await;
        let client = actor
            .register("sub".into(), "user".into(), false)
            .await
            .unwrap();
        actor
            .subscribe(
                "sub",
                client.generation,
                vec![(filter("sport/#"), Some(1)), (filter("sport/+"), Some(1))],
            )
            .await
            .unwrap();
        actor
            .unsubscribe("sub", client.generation, vec![filter("sport/#")])
            .await
            .unwrap();
        let subscriptions = &actor.state.sessions["sub"].subscriptions;
        assert!(!subscriptions.contains_key("sport/#"));
        assert!(subscriptions.contains_key("sport/+"));
        actor.store.shutdown().await.unwrap();
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
                vec![(filter("test/#"), Some(2))],
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
            metrics: Arc::default(),
            store,
            state,
            auth: Arc::clone(&actor.auth),
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
                vec![(filter("test/secret"), None)],
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
    async fn retained_system_topics_require_explicit_filter_and_allowed_acl() {
        // MQTT-4.7.2-1 and MQTT-3.8.4-3: retained delivery uses the same matcher.
        let (directory, mut actor) = actor().await;
        let publisher = actor
            .register("pub".into(), "user".into(), true)
            .await
            .unwrap();
        actor
            .publish(
                "pub",
                publisher.generation,
                message("$SYS/state", 0, true, b"online"),
                None,
            )
            .await
            .unwrap();
        let subscriber = actor
            .register("sub".into(), "user".into(), false)
            .await
            .unwrap();
        let (_, retained) = actor
            .subscribe("sub", subscriber.generation, vec![(filter("#"), Some(0))])
            .await
            .unwrap();
        assert!(retained.is_empty());
        let (_, retained) = actor
            .subscribe(
                "sub",
                subscriber.generation,
                vec![(filter("$SYS/#"), Some(0))],
            )
            .await
            .unwrap();
        assert_eq!(retained.len(), 1);
        let Delivery::Publish {
            message: retained_message,
            ..
        } = &retained[0]
        else {
            panic!("expected publication")
        };
        assert!(retained_message.retain);

        actor.auth = Arc::new(AccessPolicy::acl_lab(policy(directory.path(), true)));
        let (codes, retained) = actor
            .subscribe("sub", subscriber.generation, vec![(filter("#"), Some(0))])
            .await
            .unwrap();
        assert_eq!(codes, [0x80]);
        assert!(retained.is_empty());
        // A previously installed filter cannot bypass a subsequently restricted policy.
        let mut candidate = actor.state.clone();
        assert!(
            apply_message(
                &mut candidate,
                &actor.live,
                &actor.auth,
                &message("$SYS/state", 0, false, b"denied")
            )
            .unwrap()
            .is_empty()
        );
        actor.store.shutdown().await.unwrap();
    }

    #[tokio::test]
    async fn acl_revocation_purges_wildcard_offline_and_inflight_on_recovery() {
        let (directory, mut actor) = actor().await;
        let subscriber = actor
            .register("sub".into(), "user".into(), false)
            .await
            .unwrap();
        actor
            .subscribe(
                "sub",
                subscriber.generation,
                vec![(filter("test/#"), Some(1))],
            )
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
                message("test/private", 1, false, b"inflight"),
                Some(1),
            )
            .await
            .unwrap();
        actor
            .unregister("sub", subscriber.generation)
            .await
            .unwrap();
        actor
            .publish(
                "pub",
                publisher.generation,
                message("test/private", 1, false, b"offline"),
                Some(2),
            )
            .await
            .unwrap();
        assert_eq!(actor.state.sessions["sub"].outbound.len(), 1);
        assert_eq!(actor.state.sessions["sub"].offline.len(), 1);
        actor.store.shutdown().await.unwrap();

        // The new policy only permits the exact test/state topic.
        let policy = policy(directory.path(), true);
        let router = Router::start(directory.path(), Arc::new(AccessPolicy::acl_lab(policy)))
            .await
            .unwrap();
        let resumed = router
            .register("sub".into(), "user".into(), false)
            .await
            .unwrap();
        assert!(resumed.resumed);
        assert!(resumed.replay.is_empty());
    }

    #[tokio::test]
    async fn subscription_quota_failure_does_not_commit_partial_filters() {
        let (_directory, mut actor) = actor().await;
        let subscriber = actor
            .register("sub".into(), "user".into(), false)
            .await
            .unwrap();
        let accepted = (0..256)
            .map(|i| (filter(&format!("test/{i}/+")), Some(0)))
            .collect();
        actor
            .subscribe("sub", subscriber.generation, accepted)
            .await
            .unwrap();
        let before = actor.state.clone();
        assert!(matches!(
            actor
                .subscribe(
                    "sub",
                    subscriber.generation,
                    vec![(filter("extra/#"), Some(0))]
                )
                .await,
            Err(RouterError::Store(StateError::Limit(_)))
        ));
        assert_eq!(actor.state, before);
        actor.store.shutdown().await.unwrap();
    }

    #[tokio::test]
    async fn clean_connect_cannot_erase_another_principals_session() {
        let (_directory, mut actor) = actor().await;
        let victim = actor
            .register("shared-id".into(), "user".into(), false)
            .await
            .unwrap();
        actor
            .subscribe(
                "shared-id",
                victim.generation,
                vec![(filter("test/private"), Some(1))],
            )
            .await
            .unwrap();
        assert!(matches!(
            actor
                .register("shared-id".into(), "attacker".into(), true)
                .await,
            Err(RouterError::PrincipalMismatch)
        ));
        assert_eq!(actor.state.sessions["shared-id"].principal, "user");
        assert_eq!(actor.state.sessions["shared-id"].subscriptions.len(), 1);
        assert!(actor.current("shared-id", victim.generation).is_ok());
        actor.store.shutdown().await.unwrap();
    }

    #[tokio::test]
    async fn long_utf8_topics_route_and_survive_retained_offline_restore() {
        let (directory, mut actor) = actor().await;
        let topic = format!("{}/x", "é".repeat(511));
        let topic_filter = format!("{}/+", "é".repeat(511));
        assert_eq!(topic.len(), 1024);
        assert_eq!(topic_filter.len(), 1024);
        let mut subscriber = actor
            .register("sub".into(), "user".into(), false)
            .await
            .unwrap();
        let publisher = actor
            .register("pub".into(), "user".into(), true)
            .await
            .unwrap();
        actor
            .subscribe(
                "sub",
                subscriber.generation,
                vec![(filter(&topic_filter), Some(1))],
            )
            .await
            .unwrap();
        actor
            .publish(
                "pub",
                publisher.generation,
                message(&topic, 1, true, b"live"),
                Some(1),
            )
            .await
            .unwrap();
        let Delivery::Publish {
            message: delivered, ..
        } = subscriber.outbound.try_recv().unwrap()
        else {
            panic!("long topic was not routed");
        };
        assert_eq!(delivered.topic.as_str(), topic);
        actor
            .unregister("sub", subscriber.generation)
            .await
            .unwrap();
        actor
            .publish(
                "pub",
                publisher.generation,
                message(&topic, 1, true, b"offline"),
                Some(2),
            )
            .await
            .unwrap();
        actor.store.shutdown().await.unwrap();
        let (store, recovered) = MqttStore::open(directory.path()).await.unwrap();
        assert!(
            recovered.sessions["sub"]
                .subscriptions
                .contains_key(topic_filter.as_str())
        );
        assert_eq!(recovered.sessions["sub"].offline[0].topic.as_str(), topic);
        assert_eq!(recovered.retained[topic.as_str()].payload, b"offline");
        store.shutdown().await.unwrap();
    }

    #[tokio::test]
    async fn will_disconnect_cancel_takeover_acl_and_retained_are_atomic() {
        let (_directory, mut actor) = actor().await;
        let mut subscriber = actor
            .register("watcher".into(), "user".into(), false)
            .await
            .unwrap();
        actor
            .subscribe(
                "watcher",
                subscriber.generation,
                vec![(filter("test/state"), Some(2))],
            )
            .await
            .unwrap();
        for qos in 0..=2 {
            let producer = actor
                .register_with_will(
                    format!("source{qos}"),
                    "user".into(),
                    true,
                    Some(message("test/state", qos, true, b"offline")),
                )
                .await
                .unwrap();
            actor
                .unregister_with_reason(&producer.client_id, producer.generation, false)
                .await
                .unwrap();
            let Delivery::Publish {
                message: delivered, ..
            } = subscriber.outbound.try_recv().unwrap()
            else {
                panic!("Will missing")
            };
            assert_eq!(delivered.qos, qos);
            assert!(!delivered.retain);
            assert!(!actor.state.pending_wills.contains_key(&producer.client_id));
            assert_eq!(
                actor.state.retained[&TopicName::try_from("test/state".to_owned()).unwrap()]
                    .payload,
                b"offline"
            );
        }
        let source = actor
            .register_with_will(
                "normal".into(),
                "user".into(),
                false,
                Some(message("test/state", 1, true, b"cancel")),
            )
            .await
            .unwrap();
        actor
            .unregister_with_reason("normal", source.generation, true)
            .await
            .unwrap();
        assert!(subscriber.outbound.try_recv().is_err());
    }

    #[tokio::test]
    async fn will_takeover_and_acl_revocation_do_not_duplicate_or_bypass_policy() {
        let (directory, mut actor) = actor().await;
        let mut subscriber = actor
            .register("watcher".into(), "user".into(), false)
            .await
            .unwrap();
        actor
            .subscribe(
                "watcher",
                subscriber.generation,
                vec![(filter("test/state"), Some(2))],
            )
            .await
            .unwrap();
        let source = actor
            .register_with_will(
                "takeover".into(),
                "user".into(),
                true,
                Some(message("test/state", 1, false, b"old")),
            )
            .await
            .unwrap();
        let replacement = actor
            .register_with_will("takeover".into(), "user".into(), true, None)
            .await
            .unwrap();
        assert!(matches!(
            subscriber.outbound.try_recv(),
            Ok(Delivery::Publish { .. })
        ));
        assert!(matches!(
            actor
                .unregister_with_reason("takeover", source.generation, false)
                .await,
            Err(RouterError::Stale)
        ));
        actor
            .unregister_with_reason("takeover", replacement.generation, true)
            .await
            .unwrap();
        assert!(subscriber.outbound.try_recv().is_err());
        actor.auth = Arc::new(AccessPolicy::secure(policy(directory.path(), false)));
        assert!(matches!(
            actor
                .register_with_will(
                    "denied".into(),
                    "user".into(),
                    true,
                    Some(message("test/state", 1, true, b"denied"))
                )
                .await,
            Err(RouterError::WillDenied)
        ));
        assert!(!actor.state.sessions.contains_key("denied"));
        // A later revocation must also prevent the Will from publishing.
        actor.auth = Arc::new(AccessPolicy::secure(policy(directory.path(), true)));
        let revoked = actor
            .register_with_will(
                "revoked".into(),
                "user".into(),
                true,
                Some(message("test/state", 1, true, b"revoked")),
            )
            .await
            .unwrap();
        actor.auth = Arc::new(AccessPolicy::secure(policy(directory.path(), false)));
        actor
            .unregister_with_reason("revoked", revoked.generation, false)
            .await
            .unwrap();
        assert!(subscriber.outbound.try_recv().is_err());
        assert!(
            actor
                .state
                .retained
                .get(&TopicName::try_from("test/state".to_owned()).unwrap())
                .is_none_or(|message| message.payload != b"revoked")
        );
    }

    #[tokio::test]
    async fn retained_empty_will_deletes_and_restart_publishes_once() {
        let (directory, mut actor) = actor().await;
        let topic = "é".repeat(512);
        let source = actor
            .register_with_will(
                "long".into(),
                "user".into(),
                true,
                Some(message(&topic, 2, true, b"crash")),
            )
            .await
            .unwrap();
        assert!(actor.state.pending_wills.contains_key(&source.client_id));
        actor.store.shutdown().await.unwrap();
        let auth = Arc::new(AccessPolicy::password_lab(policy(directory.path(), true)));
        let router = Router::start(directory.path(), auth).await.unwrap();
        let mut subscriber = router
            .register_with_will("new".into(), "user".into(), false, None)
            .await
            .unwrap();
        let (_, retained) = router
            .subscribe(&subscriber, vec![(filter(&topic), Some(2))])
            .await
            .unwrap();
        assert_eq!(retained.len(), 1);
        let Delivery::Publish {
            message: stored, ..
        } = &retained[0]
        else {
            panic!("retained missing")
        };
        assert_eq!(stored.payload, b"crash");
        assert!(stored.retain);
        let empty = router
            .register_with_will(
                "empty".into(),
                "user".into(),
                true,
                Some(message(&topic, 0, true, b"")),
            )
            .await
            .unwrap();
        router.unregister(&empty, false).await.unwrap();
        let Delivery::Publish {
            message: deleted, ..
        } = subscriber.outbound.recv().await.unwrap()
        else {
            panic!("deletion missing")
        };
        assert_eq!(deleted.payload, []);
        assert!(!deleted.retain);
        let (_, retained) = router
            .subscribe(&subscriber, vec![(filter(&topic), Some(2))])
            .await
            .unwrap();
        assert!(retained.is_empty());
        router.unregister(&subscriber, true).await.unwrap();
        drop(router);
    }

    #[tokio::test]
    async fn cancelled_connection_task_guard_publishes_will() {
        let directory = tempfile::tempdir().unwrap();
        let auth = Arc::new(AccessPolicy::open_lab());
        let router = Router::start(directory.path(), auth).await.unwrap();
        let mut subscriber = router
            .register_with_will("subscriber".into(), "__open_lab__".into(), true, None)
            .await
            .unwrap();
        router
            .subscribe(&subscriber, vec![(filter("test/state"), Some(1))])
            .await
            .unwrap();
        let source = router
            .register_with_will(
                "source".into(),
                "__open_lab__".into(),
                true,
                Some(message("test/state", 1, false, b"cancelled-task")),
            )
            .await
            .unwrap();
        let guard = router.connection_guard(&source);
        let task = tokio::spawn(async move {
            let _guard = guard;
            std::future::pending::<()>().await;
        });
        task.abort();
        let _ = task.await;
        let delivery = tokio::time::timeout(
            std::time::Duration::from_secs(3),
            subscriber.outbound.recv(),
        )
        .await
        .unwrap()
        .unwrap();
        let Delivery::Publish { message, .. } = delivery else {
            panic!("Will missing")
        };
        assert_eq!(message.payload, b"cancelled-task");
        router.unregister(&subscriber, true).await.unwrap();
    }

    #[tokio::test]
    async fn metrics_count_qos2_acceptance_once_and_no_success_for_invalid_commit() {
        let (_directory, mut actor) = actor().await;
        let source = actor
            .register("source".into(), "user".into(), true)
            .await
            .unwrap();
        let qos2 = message("test/state", 2, true, b"value");
        actor
            .publish("source", source.generation, qos2.clone(), Some(1))
            .await
            .unwrap();
        actor
            .publish("source", source.generation, qos2, Some(1))
            .await
            .unwrap();
        assert_eq!(actor.metrics.received[2].load(Ordering::Relaxed), 1);
        actor.pubrel("source", source.generation, 1).await.unwrap();
        assert_eq!(actor.metrics.received[2].load(Ordering::Relaxed), 1);
        assert_eq!(actor.metrics.retained.load(Ordering::Relaxed), 1);
        let successful = actor.metrics.commits.load(Ordering::Relaxed);
        let mut invalid = actor.state.clone();
        invalid.sessions.get_mut("source").unwrap().next_packet_id = 0;
        assert!(actor.commit(invalid).await.is_err());
        assert_eq!(actor.metrics.commits.load(Ordering::Relaxed), successful);
        assert_eq!(actor.metrics.persistence_errors.load(Ordering::Relaxed), 0);
    }
    #[cfg(target_os = "linux")]
    async fn dynamic_actor() -> (TempDir, Actor) {
        use std::os::unix::fs::PermissionsExt;
        let (directory, mut actor) = actor().await;
        let users = fs::read_to_string(directory.path().join("users.toml")).unwrap();
        let path = directory.path().join("private.toml");
        fs::write(
            &path,
            format!("version=1\n{users}publish=['test/state']\nsubscribe=['test/state']\n"),
        )
        .unwrap();
        fs::set_permissions(&path, fs::Permissions::from_mode(0o600)).unwrap();
        actor.auth = Arc::new(crate::auth::DynamicPolicy::load(path, false).await.unwrap());
        (directory, actor)
    }

    #[cfg(target_os = "linux")]
    #[tokio::test]
    async fn dynamic_reload_rejects_stale_registration_and_preserves_durable_qos2() {
        let (directory, mut actor) = dynamic_actor().await;
        let source = actor
            .register("source".into(), "user".into(), false)
            .await
            .unwrap();
        actor
            .publish(
                "source",
                source.generation,
                message("test/state", 2, true, b"owned"),
                Some(7),
            )
            .await
            .unwrap();
        fs::write(
            directory.path().join("private.toml"),
            "version=1\nusers=[]\n",
        )
        .unwrap();
        let dynamic = actor.auth.dynamic().unwrap();
        assert_eq!(
            actor
                .reload_security(dynamic.candidate().await.unwrap())
                .await
                .unwrap(),
            2
        );
        assert_eq!(actor.state.sessions["source"].inbound_qos2.len(), 1);
        assert!(*source.closed.borrow());
        let (reply, result) = oneshot::channel();
        actor
            .handle(Command::Register {
                security_generation: Some(1),
                client_id: "stale".into(),
                principal: "user".into(),
                clean: true,
                will: None,
                reply,
            })
            .await;
        assert!(matches!(result.await.unwrap(), Err(RouterError::Security)));
        assert!(!actor.state.sessions.contains_key("stale"));
        actor.store.shutdown().await.unwrap();
        let (store, state) = MqttStore::open(directory.path()).await.unwrap();
        assert_eq!(state.sessions["source"].inbound_qos2.len(), 1);
        store.shutdown().await.unwrap();
    }

    #[cfg(target_os = "linux")]
    #[tokio::test]
    async fn dynamic_reload_storage_failure_does_not_publish_policy() {
        let (directory, mut actor) = dynamic_actor().await;
        let source = actor
            .register("source".into(), "user".into(), false)
            .await
            .unwrap();
        let dynamic = actor.auth.dynamic().unwrap();
        let candidate = dynamic.candidate().await.unwrap();
        actor.store.shutdown().await.unwrap();
        assert!(actor.reload_security(candidate).await.is_err());
        assert_eq!(actor.auth.security_generation(), 1);
        assert!(actor.auth.allowed_publish("user", "test/state"));
        assert!(actor.fatal);
        assert!(*source.closed.borrow());
        drop(directory);
    }
}
