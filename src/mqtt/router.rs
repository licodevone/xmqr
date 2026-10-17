//! Single-owner MQTT session actor. A candidate state is fsynced before ACKs
//! or fan-out, so no async mutex is held across storage I/O.

use std::{
    collections::{BTreeMap, BTreeSet, VecDeque},
    path::Path,
    time::{Duration, SystemTime, UNIX_EPOCH},
};

use sha2::{Digest, Sha256};
use thiserror::Error;
use tokio::sync::{mpsc, oneshot, watch};

use crate::auth::{AccessPolicy, AuthPolicy};
use crate::monitoring::{Metrics, Rejection};
use crate::transport::HandlerError;
use std::sync::{Arc, atomic::Ordering};

use super::StateLimits;
use super::store::{
    AdminReceipt, DurableSession, DurableState, InboundQos2, MAX_ADMIN_RECEIPTS, MqttStore,
    OutboundInflight, OutboundStage, PendingWill, SharedOrigin, StateError, StoredMessage,
};
use super::topic::{TopicFilter, TopicName};

const COMMAND_CAPACITY: usize = 256;
const DELIVERY_CAPACITY: usize = 64;

struct SharedCandidate {
    client_id: String,
    active: bool,
    qos: u8,
    preserve_retain: bool,
    identifier: Option<u32>,
}

fn unix_ms() -> Result<u64, RouterError> {
    unix_ms_from(SystemTime::now())
}

fn unix_ms_from(instant: SystemTime) -> Result<u64, RouterError> {
    let elapsed = instant
        .duration_since(UNIX_EPOCH)
        .map_err(|_| RouterError::Clock)?;
    u64::try_from(elapsed.as_millis()).map_err(|_| RouterError::Clock)
}

fn expiry_deadline(now: u64, seconds: u32) -> Result<u64, RouterError> {
    now.checked_add(u64::from(seconds) * 1000)
        .ok_or(RouterError::Clock)
}

pub(super) fn message_expiry_deadline(seconds: u32) -> Result<u64, RouterError> {
    expiry_deadline(unix_ms()?, seconds)
}

pub(super) fn remaining_message_expiry(deadline: u64) -> Result<u32, RouterError> {
    let remaining_ms = deadline.saturating_sub(unix_ms()?);
    u32::try_from(remaining_ms.div_ceil(1000)).map_err(|_| RouterError::Clock)
}

fn message_expired(message: &StoredMessage, now: u64) -> bool {
    message
        .expiry_at_unix_ms
        .is_some_and(|deadline| deadline <= now)
}

fn session_expired(session: &DurableSession, now: u64) -> bool {
    session
        .expires_at_unix_ms
        .is_some_and(|deadline| deadline <= now)
}

pub(super) struct SessionPolicy {
    pub clean: bool,
    pub persistent: bool,
    pub expiry_interval_seconds: Option<u32>,
    pub will_delay_seconds: u32,
    pub receive_maximum: u16,
}

fn reconcile_recovered_sessions(
    state: &mut DurableState,
    auth: &AccessPolicy,
    limits: StateLimits,
) -> Result<(), RouterError> {
    let now = unix_ms()?;
    let ended: Vec<_> = state
        .sessions
        .values()
        .filter(|session| {
            !session.persistent
                || session_expired(session, now)
                || !auth.contains_principal(&session.principal)
        })
        .cloned()
        .collect();
    state.sessions.retain(|_, session| {
        session.persistent
            && !session_expired(session, now)
            && auth.contains_principal(&session.principal)
    });
    for session in state.sessions.values_mut() {
        // Crash time is unknown; start a connected finite session's timer on
        // recovery so already accepted data is not silently discarded.
        if let Some(seconds) = session.expiry_interval_seconds
            && session.expires_at_unix_ms.is_none()
        {
            session.expires_at_unix_ms = Some(expiry_deadline(now, seconds)?);
        }
        let shared = &session.shared_filters;
        session.subscriptions.retain(|filter, _| {
            auth.allowed_subscribe(
                &session.principal,
                if shared.contains(filter) {
                    super::topic::shared_inner(filter.as_str()).unwrap_or(filter.as_str())
                } else {
                    filter.as_str()
                },
            )
        });
        session
            .shared_filters
            .retain(|filter| session.subscriptions.contains_key(filter));
        session
            .subscription_options
            .retain(|filter, _| session.subscriptions.contains_key(filter));
        session
            .subscription_identifiers
            .retain(|filter, _| session.subscriptions.contains_key(filter));
        session
            .offline
            .retain(|message| auth.allowed_delivery(&session.principal, message.topic.as_str()));
        session.outbound.retain(|entry| {
            auth.allowed_delivery(&session.principal, entry.message.topic.as_str())
        });
        // Accepted inbound QoS2 remains owned after later ACL changes.
    }
    reassign_ended_shared_qos1(
        limits,
        state,
        &BTreeMap::new(),
        auth,
        ended,
        &mut Vec::new(),
    )?;
    Ok(())
}

#[derive(Debug, Error)]
pub(crate) enum AdminError {
    #[error("administrative request ID conflicts with committed receipt")]
    Conflict,
    #[error("security generation changed")]
    Stale,
    #[error("administrative receipt capacity exhausted")]
    Capacity,
    #[error("administrative actor unavailable")]
    Unavailable,
    #[error("administrative commit failed")]
    CommitFailed,
    #[error("administrative target not found")]
    NotFound,
    #[error("administrative request ID belongs to an old audit epoch")]
    StaleEpoch,
    #[error("audit archive does not match current receipts")]
    ArchiveChanged,
}

#[derive(Debug, Error)]
pub(super) enum RouterError {
    #[error(transparent)]
    Store(#[from] StateError),
    #[error("inbound QoS 2 durable quota exhausted by an earlier session")]
    InboundQos2Quota,
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
    #[error("system clock unavailable for MQTT session expiry")]
    Clock,
    #[error("invalid MQTT 5 DISCONNECT Session Expiry transition")]
    InvalidSessionExpiry,
}

/// A packet to send to a connected subscriber after the durable transition.
#[derive(Clone, Debug)]
#[expect(
    clippy::large_enum_variant,
    reason = "bounded delivery channel avoids heap allocation on the publish path"
)]
pub(super) enum Delivery {
    Publish {
        message: StoredMessage,
        packet_id: Option<u16>,
        dup: bool,
    },
    PubRel(u16),
}

type SubscribeResult = Result<(Vec<u8>, Vec<Delivery>), RouterError>;
#[derive(Clone)]
pub(crate) struct AdminReceiptView {
    pub operation: String,
    pub request_sha256: String,
    pub expected_generation: u64,
    pub applied_generation: u64,
    pub actor_uid: u32,
    pub timestamp_unix_ms: u64,
    pub epoch: u32,
    pub archive_count: u16,
}

impl From<&AdminReceipt> for AdminReceiptView {
    fn from(receipt: &AdminReceipt) -> Self {
        Self {
            operation: receipt.operation.clone(),
            request_sha256: receipt.request_sha256.clone(),
            expected_generation: receipt.expected_generation,
            applied_generation: receipt.applied_generation,
            actor_uid: receipt.actor_uid,
            timestamp_unix_ms: receipt.timestamp_unix_ms,
            epoch: receipt.epoch,
            archive_count: receipt.archive_count,
        }
    }
}

pub(crate) struct AdminPage {
    pub items: Vec<serde_json::Value>,
    pub next_cursor: Option<String>,
}

#[derive(Clone, Copy)]
pub(crate) enum AdminListKind {
    Sessions,
    Retained,
}

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
    receive_maximum: usize,
    pending_replay: VecDeque<Delivery>,
    sent_unacked: BTreeSet<u16>,
    inbound_accepted: BTreeSet<u16>,
}

struct Actor {
    limits: StateLimits,
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
    AdminAuditRotate {
        request_id: String,
        archive_sha256: String,
        archive_count: u16,
        actor_uid: u32,
        reply: oneshot::Sender<Result<(u32, bool), AdminError>>,
    },
    AdminStatus {
        reply: oneshot::Sender<(u32, usize)>,
    },
    AdminAuditList {
        offset: usize,
        limit: usize,
        reply: oneshot::Sender<AdminPage>,
    },
    AdminSessionDisconnect {
        client_id: String,
        request_id: String,
        actor_uid: u32,
        reply: oneshot::Sender<Result<bool, AdminError>>,
    },
    AdminRetainedDelete {
        topic: super::topic::TopicName,
        request_id: String,
        actor_uid: u32,
        reply: oneshot::Sender<Result<bool, AdminError>>,
    },
    AdminList {
        kind: AdminListKind,
        cursor: Option<String>,
        limit: usize,
        reply: oneshot::Sender<AdminPage>,
    },
    AdminReceiptLookup {
        request_id: String,
        reply: oneshot::Sender<Option<AdminReceiptView>>,
    },
    AdminReload {
        candidate: AuthPolicy,
        request_id: String,
        bundle_sha256: String,
        expected_generation: u64,
        actor_uid: u32,
        reply: oneshot::Sender<Result<(u64, bool), AdminError>>,
    },
    #[cfg(test)]
    Inject {
        fault: crate::persistence::faults::Fault,
        reply: oneshot::Sender<Result<(), RouterError>>,
    },
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
        persistent: bool,
        expiry_interval_seconds: Option<u32>,
        will_delay_seconds: u32,
        receive_maximum: u16,
        will: Option<StoredMessage>,
        reply: oneshot::Sender<Result<Session, RouterError>>,
    },
    Subscribe {
        client_id: String,
        generation: u64,
        filters: Vec<(TopicFilter, Option<u8>, u8, u8)>,
        identifier: Option<u32>,
        mqtt5_shared: bool,
        reply: oneshot::Sender<SubscribeResult>,
    },
    Unsubscribe {
        client_id: String,
        generation: u64,
        filters: Vec<TopicFilter>,
        reply: oneshot::Sender<Result<Vec<u8>, RouterError>>,
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
    DiscardOutbound {
        client_id: String,
        generation: u64,
        packet_id: u16,
        reply: oneshot::Sender<Result<(), RouterError>>,
    },
    Unregister {
        client_id: String,
        generation: u64,
        graceful: bool,
        expiry_override: Option<u32>,
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
    inbound_receive_maximum: u16,
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
                        expiry_override: None,
                        reply,
                    })
                    .await;
                let _ = result.await;
            });
        }
    }
}

impl Router {
    pub(crate) async fn admin_audit_rotate(
        &self,
        request_id: String,
        archive_sha256: String,
        archive_count: u16,
        actor_uid: u32,
    ) -> Result<(u32, bool), AdminError> {
        let (reply, result) = oneshot::channel();
        self.sender
            .try_send(Command::AdminAuditRotate {
                request_id,
                archive_sha256,
                archive_count,
                actor_uid,
                reply,
            })
            .map_err(|_| AdminError::Unavailable)?;
        result.await.map_err(|_| AdminError::Unavailable)?
    }

    pub(crate) async fn admin_status(&self) -> Result<(u32, usize), AdminError> {
        let (reply, result) = oneshot::channel();
        self.sender
            .try_send(Command::AdminStatus { reply })
            .map_err(|_| AdminError::Unavailable)?;
        result.await.map_err(|_| AdminError::Unavailable)
    }

    pub(crate) fn note_admin_replay(&self) {
        self.metrics
            .admin_mutations_replayed
            .fetch_add(1, Ordering::Relaxed);
    }

    pub(crate) async fn admin_audit_list(
        &self,
        offset: usize,
        limit: usize,
    ) -> Result<AdminPage, AdminError> {
        let (reply, result) = oneshot::channel();
        self.sender
            .try_send(Command::AdminAuditList {
                offset,
                limit,
                reply,
            })
            .map_err(|_| AdminError::Unavailable)?;
        result.await.map_err(|_| AdminError::Unavailable)
    }

    pub(crate) async fn admin_session_disconnect(
        &self,
        client_id: String,
        request_id: String,
        actor_uid: u32,
    ) -> Result<bool, AdminError> {
        let (reply, result) = oneshot::channel();
        self.sender
            .try_send(Command::AdminSessionDisconnect {
                client_id,
                request_id,
                actor_uid,
                reply,
            })
            .map_err(|_| AdminError::Unavailable)?;
        result.await.map_err(|_| AdminError::Unavailable)?
    }

    pub(crate) async fn admin_retained_delete(
        &self,
        topic: super::topic::TopicName,
        request_id: String,
        actor_uid: u32,
    ) -> Result<bool, AdminError> {
        let (reply, result) = oneshot::channel();
        self.sender
            .try_send(Command::AdminRetainedDelete {
                topic,
                request_id,
                actor_uid,
                reply,
            })
            .map_err(|_| AdminError::Unavailable)?;
        result.await.map_err(|_| AdminError::Unavailable)?
    }

    pub(crate) async fn admin_list(
        &self,
        kind: AdminListKind,
        cursor: Option<String>,
        limit: usize,
    ) -> Result<AdminPage, AdminError> {
        let (reply, result) = oneshot::channel();
        self.sender
            .try_send(Command::AdminList {
                kind,
                cursor,
                limit,
                reply,
            })
            .map_err(|_| AdminError::Unavailable)?;
        result.await.map_err(|_| AdminError::Unavailable)
    }

    pub(crate) async fn admin_receipt(
        &self,
        request_id: String,
    ) -> Result<Option<AdminReceiptView>, AdminError> {
        let (reply, result) = oneshot::channel();
        self.sender
            .try_send(Command::AdminReceiptLookup { request_id, reply })
            .map_err(|_| AdminError::Unavailable)?;
        result.await.map_err(|_| AdminError::Unavailable)
    }

    pub(crate) async fn admin_reload(
        &self,
        candidate: AuthPolicy,
        request_id: String,
        bundle_sha256: String,
        expected_generation: u64,
        actor_uid: u32,
    ) -> Result<(u64, bool), AdminError> {
        let (reply, result) = oneshot::channel();
        self.sender
            .try_send(Command::AdminReload {
                candidate,
                request_id,
                bundle_sha256,
                expected_generation,
                actor_uid,
                reply,
            })
            .map_err(|_| AdminError::Unavailable)?;
        result.await.map_err(|_| AdminError::Unavailable)?
    }
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
        Self::start_observed_with_limits(directory, auth, metrics, StateLimits::default()).await
    }

    /// Recover and start with validated, immutable logical quotas.
    /// # Errors
    /// Rejects state above the configured quotas before recovery transitions.
    #[expect(
        clippy::too_many_lines,
        reason = "recovery reconciles sessions and Wills before the actor becomes visible"
    )]
    pub async fn start_observed_with_limits(
        directory: &Path,
        auth: Arc<AccessPolicy>,
        metrics: Arc<Metrics>,
        limits: StateLimits,
    ) -> Result<Self, HandlerError> {
        let (store, mut state) = MqttStore::open_with_limits(directory, limits).await?;
        let before = state.clone();
        if let Err(error) = reconcile_recovered_sessions(&mut state, &auth, limits) {
            store.shutdown().await?;
            return Err(error.into());
        }
        // After crash the exact connection-loss time is unknown. Start an
        // active delayed Will's clock at recovery; a disconnected Will keeps
        // its committed absolute deadline.
        let now = unix_ms()?;
        for (client_id, will) in &mut state.pending_wills {
            if will.publish_at_unix_ms.is_none() {
                let deadline = state.sessions.get(client_id).map_or(Ok(now), |session| {
                    let delayed = expiry_deadline(now, will.delay_seconds)?;
                    Ok::<_, RouterError>(
                        session
                            .expires_at_unix_ms
                            .map_or(delayed, |end| delayed.min(end)),
                    )
                })?;
                will.publish_at_unix_ms = Some(deadline);
            }
        }
        // Publish only Wills whose delay or session expiry has passed.
        let mut recovered_wills = 0_u64;
        let due: Vec<_> = state
            .pending_wills
            .iter()
            .filter(|(id, will)| {
                will.publish_at_unix_ms.is_some_and(|at| at <= now)
                    || state
                        .sessions
                        .get(*id)
                        .is_none_or(|session| session_expired(session, now))
            })
            .map(|(id, _)| id.clone())
            .collect();
        for id in due {
            let will = state.pending_wills.remove(&id).ok_or(RouterError::Stale)?;
            if auth.allowed_publish(&will.principal, will.message.topic.as_str()) {
                if let Err(error) = apply_message(
                    limits,
                    &mut state,
                    &BTreeMap::new(),
                    &auth,
                    &will.message,
                    None,
                ) {
                    store.shutdown().await?;
                    return Err(error.into());
                }
                recovered_wills += 1;
            }
        }
        if state != before {
            let start = std::time::Instant::now();
            if let Err(error) = store.commit(&state).await {
                store.shutdown().await?;
                return Err(error.into());
            }
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
                limits,
                metrics: actor_metrics,
                store,
                state,
                auth,
                live: BTreeMap::new(),
                next_generation: 1,
                fatal: false,
                commits_since_snapshot: 0,
            };
            let mut expiry_tick = tokio::time::interval(Duration::from_millis(250));
            expiry_tick.set_missed_tick_behavior(tokio::time::MissedTickBehavior::Skip);
            loop {
                let command = tokio::select! {
                    command = receiver.recv() => command,
                    _ = expiry_tick.tick() => {
                        if actor.expire_sessions().await.is_err() { actor.fail_closed(); break; }
                        continue;
                    }
                };
                let Some(command) = command else {
                    break;
                };
                if actor.expire_sessions().await.is_err() {
                    actor.fail_closed();
                    break;
                }
                #[cfg(test)]
                if let Command::Inject { fault, reply } = command {
                    let result = actor.store.inject_for_test(fault).await.map_err(Into::into);
                    let _ = reply.send(result);
                    continue;
                }
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
        Ok(Self {
            metrics,
            sender,
            inbound_receive_maximum: u16::try_from(limits.max_inflight).unwrap_or(u16::MAX),
        })
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

    pub(crate) fn inbound_receive_maximum(&self) -> u16 {
        self.inbound_receive_maximum
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
    pub(super) async fn inject_for_test(
        &self,
        fault: crate::persistence::faults::Fault,
    ) -> Result<(), RouterError> {
        let (reply, result) = oneshot::channel();
        self.send(Command::Inject { fault, reply }).await?;
        result.await.map_err(|_| RouterError::Unavailable)?
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

    #[cfg(test)]
    pub(super) async fn register_with_epoch(
        &self,
        client_id: String,
        principal: String,
        clean: bool,
        will: Option<StoredMessage>,
        security_generation: Option<u64>,
    ) -> Result<Session, RouterError> {
        self.register_with_policy(
            client_id,
            principal,
            SessionPolicy {
                clean,
                persistent: !clean,
                expiry_interval_seconds: None,
                will_delay_seconds: 0,
                receive_maximum: u16::MAX,
            },
            will,
            security_generation,
        )
        .await
    }

    pub(super) async fn register_with_policy(
        &self,
        client_id: String,
        principal: String,
        policy: SessionPolicy,
        will: Option<StoredMessage>,
        security_generation: Option<u64>,
    ) -> Result<Session, RouterError> {
        let (reply, result) = oneshot::channel();
        self.send(Command::Register {
            security_generation,
            client_id,
            principal,
            clean: policy.clean,
            persistent: policy.persistent,
            expiry_interval_seconds: policy.expiry_interval_seconds,
            will_delay_seconds: policy.will_delay_seconds,
            receive_maximum: policy.receive_maximum,
            will,
            reply,
        })
        .await?;
        result.await.map_err(|_| RouterError::Unavailable)?
    }

    #[cfg(test)]
    pub(super) async fn subscribe(
        &self,
        session: &Session,
        filters: Vec<(TopicFilter, Option<u8>)>,
    ) -> Result<(Vec<u8>, Vec<Delivery>), RouterError> {
        self.subscribe_with_handling(
            session,
            filters
                .into_iter()
                .map(|(filter, qos)| (filter, qos, 0, 0))
                .collect(),
        )
        .await
    }

    #[cfg(test)]
    pub(super) async fn subscribe_with_handling(
        &self,
        session: &Session,
        filters: Vec<(TopicFilter, Option<u8>, u8, u8)>,
    ) -> Result<(Vec<u8>, Vec<Delivery>), RouterError> {
        self.subscribe_with_shared(session, filters, None, false)
            .await
    }

    pub(super) async fn subscribe_with_shared(
        &self,
        session: &Session,
        filters: Vec<(TopicFilter, Option<u8>, u8, u8)>,
        identifier: Option<u32>,
        mqtt5_shared: bool,
    ) -> Result<(Vec<u8>, Vec<Delivery>), RouterError> {
        let (reply, result) = oneshot::channel();
        self.send(Command::Subscribe {
            client_id: session.client_id.clone(),
            generation: session.generation,
            filters,
            identifier,
            mqtt5_shared,
            reply,
        })
        .await?;
        result.await.map_err(|_| RouterError::Unavailable)?
    }

    pub(super) async fn unsubscribe(
        &self,
        session: &Session,
        filters: Vec<TopicFilter>,
    ) -> Result<Vec<u8>, RouterError> {
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

    pub(super) async fn discard_outbound(
        &self,
        session: &Session,
        packet_id: u16,
    ) -> Result<(), RouterError> {
        let (reply, result) = oneshot::channel();
        self.send(Command::DiscardOutbound {
            client_id: session.client_id.clone(),
            generation: session.generation,
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
        self.unregister_with_expiry(session, graceful, None).await
    }

    pub(super) async fn unregister_with_expiry(
        &self,
        session: &Session,
        graceful: bool,
        expiry_override: Option<u32>,
    ) -> Result<(), RouterError> {
        let (reply, result) = oneshot::channel();
        self.send(Command::Unregister {
            client_id: session.client_id.clone(),
            generation: session.generation,
            graceful,
            expiry_override,
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
    async fn expire_sessions(&mut self) -> Result<(), RouterError> {
        let now = unix_ms()?;
        let due_wills: Vec<_> = self
            .state
            .pending_wills
            .iter()
            .filter(|(id, will)| {
                will.publish_at_unix_ms.is_some_and(|at| at <= now)
                    || (!self.live.contains_key(*id)
                        && self
                            .state
                            .sessions
                            .get(*id)
                            .is_none_or(|session| session_expired(session, now)))
            })
            .map(|(id, _)| id.clone())
            .collect();
        let expired_sessions = self
            .state
            .sessions
            .iter()
            .any(|(id, session)| !self.live.contains_key(id) && session_expired(session, now));
        let expired_messages = self
            .state
            .retained
            .values()
            .any(|m| message_expired(m, now))
            || self
                .state
                .sessions
                .values()
                .any(|s| s.offline.iter().any(|m| message_expired(m, now)));
        if expired_sessions || expired_messages || !due_wills.is_empty() {
            let mut candidate = self.state.clone();
            let expired_ids: Vec<_> = candidate
                .sessions
                .iter()
                .filter(|(id, session)| {
                    !self.live.contains_key(*id) && session_expired(session, now)
                })
                .map(|(id, _)| id.clone())
                .collect();
            let ended: Vec<_> = expired_ids
                .iter()
                .filter_map(|id| candidate.sessions.remove(id))
                .collect();
            candidate
                .retained
                .retain(|_, message| !message_expired(message, now));
            for session in candidate.sessions.values_mut() {
                session
                    .offline
                    .retain(|message| !message_expired(message, now));
            }
            let mut deliveries = Vec::new();
            reassign_ended_shared_qos1(
                self.limits,
                &mut candidate,
                &self.live,
                &self.auth,
                ended,
                &mut deliveries,
            )?;
            let mut published = 0;
            for id in due_wills {
                let will = candidate
                    .pending_wills
                    .remove(&id)
                    .ok_or(RouterError::Stale)?;
                if self
                    .auth
                    .allowed_publish(&will.principal, will.message.topic.as_str())
                {
                    deliveries.extend(apply_message(
                        self.limits,
                        &mut candidate,
                        &self.live,
                        &self.auth,
                        &will.message,
                        None,
                    )?);
                    published += 1;
                }
            }
            self.commit(candidate).await?;
            self.metrics.wills.fetch_add(published, Ordering::Relaxed);
            self.deliver(deliveries);
        }
        Ok(())
    }

    async fn shutdown(&mut self) -> Result<(), RouterError> {
        // Server stop is not a client DISCONNECT (MQTT-3.1.2-8/-10).
        // Publish all Wills against an offline view so durable subscribers
        // retain deliveries instead of losing them with the closing sockets.
        let mut candidate = self.state.clone();
        let ended: Vec<_> = candidate
            .sessions
            .values()
            .filter(|session| !session.persistent)
            .cloned()
            .collect();
        candidate.sessions.retain(|_, session| session.persistent);
        reassign_ended_shared_qos1(
            self.limits,
            &mut candidate,
            &BTreeMap::new(),
            &self.auth,
            ended,
            &mut Vec::new(),
        )?;
        let now = unix_ms()?;
        for session in candidate.sessions.values_mut() {
            if let Some(seconds) = session.expiry_interval_seconds
                && session.expires_at_unix_ms.is_none()
            {
                session.expires_at_unix_ms = Some(expiry_deadline(now, seconds)?);
            }
        }
        let mut published = 0;
        for (client_id, mut will) in std::mem::take(&mut candidate.pending_wills) {
            if self
                .auth
                .allowed_publish(&will.principal, will.message.topic.as_str())
            {
                let delayed = will
                    .publish_at_unix_ms
                    .unwrap_or(expiry_deadline(now, will.delay_seconds)?);
                let deadline = candidate
                    .sessions
                    .get(&client_id)
                    .and_then(|session| session.expires_at_unix_ms)
                    .map_or(delayed, |end| delayed.min(end));
                if deadline <= now || !candidate.sessions.contains_key(&client_id) {
                    apply_message(
                        self.limits,
                        &mut candidate,
                        &BTreeMap::new(),
                        &self.auth,
                        &will.message,
                        None,
                    )?;
                    published += 1;
                } else {
                    will.publish_at_unix_ms = Some(deadline);
                    candidate.pending_wills.insert(client_id, will);
                }
            }
        }
        self.commit(candidate).await?;
        self.metrics.wills.fetch_add(published, Ordering::Relaxed);
        self.store.snapshot().await?;
        self.store.shutdown().await?;
        Ok(())
    }

    async fn reload_security(&mut self, policy: AuthPolicy) -> Result<u64, RouterError> {
        self.reload_security_with_receipt(policy, None).await
    }

    async fn reload_security_with_receipt(
        &mut self,
        policy: AuthPolicy,
        receipt: Option<AdminReceipt>,
    ) -> Result<u64, RouterError> {
        let dynamic = self.auth.dynamic().ok_or(RouterError::Security)?;
        if dynamic.generation() == u64::MAX {
            return Err(RouterError::Security);
        }
        let view = dynamic.view(policy.clone());
        let mut candidate = self.state.clone();
        let ended: Vec<_> = candidate
            .sessions
            .values()
            .filter(|session| !session.persistent)
            .cloned()
            .collect();
        candidate.sessions.retain(|_, s| s.persistent);
        let now = unix_ms()?;
        for session in candidate.sessions.values_mut() {
            if let Some(seconds) = session.expiry_interval_seconds
                && session.expires_at_unix_ms.is_none()
            {
                session.expires_at_unix_ms = Some(expiry_deadline(now, seconds)?);
            }
        }
        for session in candidate.sessions.values_mut() {
            let shared = &session.shared_filters;
            session.subscriptions.retain(|filter, _| {
                view.allowed_subscribe(
                    &session.principal,
                    if shared.contains(filter) {
                        super::topic::shared_inner(filter.as_str()).unwrap_or(filter.as_str())
                    } else {
                        filter.as_str()
                    },
                )
            });
            session
                .shared_filters
                .retain(|filter| session.subscriptions.contains_key(filter));
            session
                .subscription_options
                .retain(|filter, _| session.subscriptions.contains_key(filter));
            session
                .subscription_identifiers
                .retain(|filter, _| session.subscriptions.contains_key(filter));
            session
                .offline
                .retain(|m| view.allowed_delivery(&session.principal, m.topic.as_str()));
            session
                .outbound
                .retain(|m| view.allowed_delivery(&session.principal, m.message.topic.as_str()));
            // Accepted inbound QoS2 remains owned, even while credentials are revoked.
        }
        reassign_ended_shared_qos1(
            self.limits,
            &mut candidate,
            &BTreeMap::new(),
            &view,
            ended,
            &mut Vec::new(),
        )?;
        let mut published = 0;
        for (client_id, mut will) in std::mem::take(&mut candidate.pending_wills) {
            if view.allowed_publish(&will.principal, will.message.topic.as_str()) {
                let delayed = will
                    .publish_at_unix_ms
                    .unwrap_or(expiry_deadline(now, will.delay_seconds)?);
                let deadline = candidate
                    .sessions
                    .get(&client_id)
                    .and_then(|session| session.expires_at_unix_ms)
                    .map_or(delayed, |end| delayed.min(end));
                if deadline <= now || !candidate.sessions.contains_key(&client_id) {
                    apply_message(
                        self.limits,
                        &mut candidate,
                        &BTreeMap::new(),
                        &view,
                        &will.message,
                        None,
                    )?;
                    published += 1;
                } else {
                    will.publish_at_unix_ms = Some(deadline);
                    candidate.pending_wills.insert(client_id, will);
                }
            }
        }
        if let Some(receipt) = receipt {
            candidate.admin_receipts.push(receipt);
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
    #[expect(
        clippy::too_many_lines,
        reason = "all actor commands dispatch through one match"
    )]
    async fn handle(&mut self, command: Command) {
        match command {
            Command::AdminAuditRotate {
                request_id,
                archive_sha256,
                archive_count,
                actor_uid,
                reply,
            } => {
                let result = self
                    .admin_rotate_audit(request_id, archive_sha256, archive_count, actor_uid)
                    .await;
                self.count_admin_result(result.as_ref().map(|(_, replayed)| *replayed));
                let _ = reply.send(result);
            }
            Command::AdminStatus { reply } => {
                let _ = reply.send((self.state.admin_epoch, self.state.admin_receipts.len()));
            }
            Command::AdminAuditList {
                offset,
                limit,
                reply,
            } => {
                let page = self.admin_audit_page(offset, limit);
                let _ = reply.send(page);
            }
            Command::AdminSessionDisconnect {
                client_id,
                request_id,
                actor_uid,
                reply,
            } => {
                let result = self
                    .admin_disconnect_session(&client_id, request_id, actor_uid)
                    .await;
                self.count_admin_result(result.as_ref().map(|replayed| *replayed));
                let _ = reply.send(result);
            }
            Command::AdminRetainedDelete {
                topic,
                request_id,
                actor_uid,
                reply,
            } => {
                let result = self
                    .admin_delete_retained(topic, request_id, actor_uid)
                    .await;
                self.count_admin_result(result.as_ref().map(|replayed| *replayed));
                let _ = reply.send(result);
            }
            Command::AdminList {
                kind,
                cursor,
                limit,
                reply,
            } => {
                let page = self.admin_list_page(kind, cursor.as_deref(), limit);
                let _ = reply.send(page);
            }
            Command::AdminReceiptLookup { request_id, reply } => {
                let receipt = self
                    .state
                    .admin_receipts
                    .iter()
                    .find(|r| r.request_id == request_id)
                    .map(AdminReceiptView::from);
                let _ = reply.send(receipt);
            }
            Command::AdminReload {
                candidate,
                request_id,
                bundle_sha256,
                expected_generation,
                actor_uid,
                reply,
            } => {
                let result = self
                    .admin_reload_candidate(
                        candidate,
                        request_id,
                        bundle_sha256,
                        expected_generation,
                        actor_uid,
                    )
                    .await;
                self.count_admin_result(result.as_ref().map(|(_, replayed)| *replayed));
                let _ = reply.send(result);
            }
            Command::Shutdown { .. } => unreachable!("shutdown handled by actor loop"),
            #[cfg(test)]
            Command::Stop | Command::Inject { .. } => self.fail_closed(),
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
                persistent,
                expiry_interval_seconds,
                will_delay_seconds,
                receive_maximum,
                will,
                reply,
            } => {
                let result =
                    if security_generation.is_some_and(|g| g != self.auth.security_generation()) {
                        Err(RouterError::Security)
                    } else {
                        self.register_with_policy_and_delay(
                            client_id,
                            principal,
                            SessionPolicy {
                                clean,
                                persistent,
                                expiry_interval_seconds,
                                will_delay_seconds,
                                receive_maximum,
                            },
                            will,
                        )
                        .await
                    };
                self.record_result(&result);
                let _ = reply.send(result);
            }
            Command::Subscribe {
                client_id,
                generation,
                filters,
                identifier,
                mqtt5_shared,
                reply,
            } => {
                let result = self
                    .subscribe_with_shared(
                        &client_id,
                        generation,
                        filters,
                        identifier,
                        mqtt5_shared,
                    )
                    .await;
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
            Command::DiscardOutbound {
                client_id,
                generation,
                packet_id,
                reply,
            } => {
                let result = self
                    .discard_outbound(&client_id, generation, packet_id)
                    .await;
                self.record_result(&result);
                let _ = reply.send(result);
            }
            Command::Unregister {
                client_id,
                generation,
                graceful,
                expiry_override,
                reply,
            } => {
                let result = self
                    .unregister_with_receipt(
                        &client_id,
                        generation,
                        graceful,
                        expiry_override,
                        None,
                    )
                    .await;
                self.record_result(&result);
                let _ = reply.send(result);
            }
        }
    }

    fn admin_audit_page(&self, offset: usize, limit: usize) -> AdminPage {
        let items = self
            .state
            .admin_receipts
            .iter()
            .skip(offset)
            .take(limit)
            .map(|receipt| {
                serde_json::json!({
                    "request_id":receipt.request_id,"operation":receipt.operation,
                    "outcome":receipt.outcome,"request_sha256":receipt.request_sha256,
                    "expected_generation":receipt.expected_generation,
                    "applied_generation":receipt.applied_generation,
                    "actor_uid":receipt.actor_uid,"timestamp_unix_ms":receipt.timestamp_unix_ms,
                "epoch":receipt.epoch,"archive_count":receipt.archive_count,
                })
            })
            .collect();
        let next = offset.saturating_add(limit);
        AdminPage {
            items,
            next_cursor: (next < self.state.admin_receipts.len()).then(|| next.to_string()),
        }
    }

    fn admin_list_page(
        &self,
        kind: AdminListKind,
        cursor: Option<&str>,
        limit: usize,
    ) -> AdminPage {
        let mut entries: Vec<(String, serde_json::Value)> = match kind {
            AdminListKind::Sessions => self
                .state
                .sessions
                .iter()
                .filter(|(id, _)| cursor.is_none_or(|after| id.as_str() > after))
                .take(limit + 1)
                .map(|(id, session)| {
                    (
                        id.clone(),
                        serde_json::json!({"client_id":id,"connected":self.live.contains_key(id),
                            "persistent":session.persistent,"subscriptions":session.subscriptions.len(),
                            "offline":session.offline.len(),"inbound_qos2":session.inbound_qos2.len(),
                            "outbound":session.outbound.len()}),
                    )
                })
                .collect(),
            AdminListKind::Retained => self
                .state
                .retained
                .iter()
                .filter(|(topic, _)| cursor.is_none_or(|after| topic.as_str() > after))
                .take(limit + 1)
                .map(|(topic, message)| {
                    (
                        topic.as_str().to_owned(),
                        serde_json::json!({"topic":topic.as_str(),"qos":message.qos,
                            "payload_bytes":message.payload.len()}),
                    )
                })
                .collect(),
        };
        let has_more = entries.len() > limit;
        entries.truncate(limit);
        let next_cursor = has_more.then(|| entries.last().expect("positive page limit").0.clone());
        AdminPage {
            items: entries.into_iter().map(|(_, item)| item).collect(),
            next_cursor,
        }
    }

    async fn admin_rotate_audit(
        &mut self,
        request_id: String,
        archive_sha256: String,
        archive_count: u16,
        actor_uid: u32,
    ) -> Result<(u32, bool), AdminError> {
        if let Some(receipt) = self
            .state
            .admin_receipts
            .iter()
            .find(|r| r.request_id == request_id)
        {
            return if receipt.operation == "audit_rotate"
                && receipt.request_sha256 == archive_sha256
                && receipt.archive_count == archive_count
            {
                Ok((
                    u32::try_from(receipt.applied_generation)
                        .map_err(|_| AdminError::Unavailable)?,
                    true,
                ))
            } else {
                Err(AdminError::Conflict)
            };
        }
        self.check_admin_id(&request_id)?;
        if self.state.admin_epoch == u32::MAX {
            return Err(AdminError::Capacity);
        }
        let count = self.state.admin_receipts.len();
        if count == 0 || count != usize::from(archive_count) {
            return Err(AdminError::ArchiveChanged);
        }
        let bytes = serde_json::to_vec(&self.admin_audit_page(0, MAX_ADMIN_RECEIPTS).items)
            .map_err(|_| AdminError::Unavailable)?;
        let actual = format!("{:x}", Sha256::digest(bytes));
        if actual != archive_sha256 {
            return Err(AdminError::ArchiveChanged);
        }
        let millis = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map_err(|_| AdminError::Unavailable)?
            .as_millis();
        let timestamp_unix_ms = u64::try_from(millis).map_err(|_| AdminError::Unavailable)?;
        let mut candidate = self.state.clone();
        for old in &self.state.admin_receipts {
            if old.epoch == 0 && !candidate.retired_admin_ids.contains(&old.request_id) {
                candidate.retired_admin_ids.push(old.request_id.clone());
            }
        }
        if candidate.retired_admin_ids.len() > super::store::MAX_RETIRED_ADMIN_IDS {
            return Err(AdminError::Capacity);
        }
        candidate.admin_receipts.clear();
        candidate.admin_epoch += 1;
        candidate.admin_receipts.push(AdminReceipt {
            request_id,
            operation: "audit_rotate".into(),
            outcome: "committed".into(),
            request_sha256: archive_sha256,
            expected_generation: u64::from(self.state.admin_epoch),
            applied_generation: u64::from(candidate.admin_epoch),
            actor_uid,
            timestamp_unix_ms,
            epoch: self.state.admin_epoch,
            archive_count,
        });
        let new_epoch = candidate.admin_epoch;
        self.commit(candidate)
            .await
            .map_err(|_| AdminError::CommitFailed)?;
        Ok((new_epoch, false))
    }

    fn check_admin_id(&self, request_id: &str) -> Result<(), AdminError> {
        if self
            .state
            .retired_admin_ids
            .iter()
            .any(|id| id == request_id)
            || (self.state.admin_epoch > 0
                && !request_id.starts_with(&format!("{:08x}", self.state.admin_epoch)))
        {
            return Err(AdminError::StaleEpoch);
        }
        Ok(())
    }

    async fn admin_disconnect_session(
        &mut self,
        client_id: &str,
        request_id: String,
        actor_uid: u32,
    ) -> Result<bool, AdminError> {
        let mut hasher = Sha256::new();
        hasher.update(b"session_disconnect\0");
        hasher.update(client_id.as_bytes());
        let digest = format!("{:x}", hasher.finalize());
        if let Some(receipt) = self
            .state
            .admin_receipts
            .iter()
            .find(|r| r.request_id == request_id)
        {
            return if receipt.operation == "session_disconnect" && receipt.request_sha256 == digest
            {
                Ok(true)
            } else {
                Err(AdminError::Conflict)
            };
        }
        self.check_admin_id(&request_id)?;
        if self.state.admin_receipts.len() >= MAX_ADMIN_RECEIPTS {
            return Err(AdminError::Capacity);
        }
        let generation = self
            .live
            .get(client_id)
            .ok_or(AdminError::NotFound)?
            .generation;
        let millis = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map_err(|_| AdminError::Unavailable)?
            .as_millis();
        let timestamp_unix_ms = u64::try_from(millis).map_err(|_| AdminError::Unavailable)?;
        let receipt = AdminReceipt {
            request_id,
            operation: "session_disconnect".into(),
            outcome: "committed".into(),
            request_sha256: digest,
            expected_generation: 0,
            applied_generation: 0,
            actor_uid,
            timestamp_unix_ms,
            epoch: self.state.admin_epoch,
            archive_count: 0,
        };
        self.unregister_with_receipt(client_id, generation, false, None, Some(receipt))
            .await
            .map_err(|_| AdminError::CommitFailed)?;
        Ok(false)
    }

    async fn admin_delete_retained(
        &mut self,
        topic: super::topic::TopicName,
        request_id: String,
        actor_uid: u32,
    ) -> Result<bool, AdminError> {
        let mut hasher = Sha256::new();
        hasher.update(b"retained_delete\0");
        hasher.update(topic.as_str().as_bytes());
        let digest = format!("{:x}", hasher.finalize());
        if let Some(receipt) = self
            .state
            .admin_receipts
            .iter()
            .find(|r| r.request_id == request_id)
        {
            return if receipt.operation == "retained_delete" && receipt.request_sha256 == digest {
                Ok(true)
            } else {
                Err(AdminError::Conflict)
            };
        }
        self.check_admin_id(&request_id)?;
        if self.state.admin_receipts.len() >= MAX_ADMIN_RECEIPTS {
            return Err(AdminError::Capacity);
        }
        if !self.state.retained.contains_key(&topic) {
            return Err(AdminError::NotFound);
        }
        let millis = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map_err(|_| AdminError::Unavailable)?
            .as_millis();
        let timestamp_unix_ms = u64::try_from(millis).map_err(|_| AdminError::Unavailable)?;
        let receipt = AdminReceipt {
            request_id,
            operation: "retained_delete".into(),
            outcome: "committed".into(),
            request_sha256: digest,
            expected_generation: 0,
            applied_generation: 0,
            actor_uid,
            timestamp_unix_ms,
            epoch: self.state.admin_epoch,
            archive_count: 0,
        };
        let mut candidate = self.state.clone();
        candidate.retained.remove(&topic);
        candidate.admin_receipts.push(receipt);
        self.commit(candidate)
            .await
            .map_err(|_| AdminError::CommitFailed)?;
        Ok(false)
    }

    async fn admin_reload_candidate(
        &mut self,
        policy: AuthPolicy,
        request_id: String,
        bundle_sha256: String,
        expected_generation: u64,
        actor_uid: u32,
    ) -> Result<(u64, bool), AdminError> {
        if let Some(receipt) = self
            .state
            .admin_receipts
            .iter()
            .find(|r| r.request_id == request_id)
        {
            return if receipt.operation == "reload"
                && receipt.request_sha256 == bundle_sha256
                && receipt.expected_generation == expected_generation
            {
                Ok((receipt.applied_generation, true))
            } else {
                Err(AdminError::Conflict)
            };
        }
        self.check_admin_id(&request_id)?;
        if self.auth.security_generation() != expected_generation || expected_generation == u64::MAX
        {
            return Err(AdminError::Stale);
        }
        if self.state.admin_receipts.len() >= MAX_ADMIN_RECEIPTS {
            return Err(AdminError::Capacity);
        }
        let millis = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map_err(|_| AdminError::Unavailable)?
            .as_millis();
        let timestamp_unix_ms = u64::try_from(millis).map_err(|_| AdminError::Unavailable)?;
        let receipt = AdminReceipt {
            request_id,
            operation: "reload".into(),
            outcome: "committed".into(),
            request_sha256: bundle_sha256,
            expected_generation,
            applied_generation: expected_generation + 1,
            actor_uid,
            timestamp_unix_ms,
            epoch: self.state.admin_epoch,
            archive_count: 0,
        };
        self.reload_security_with_receipt(policy, Some(receipt))
            .await
            .map(|generation| (generation, false))
            .map_err(|_| AdminError::CommitFailed)
    }

    fn count_admin_result(&self, result: Result<bool, &AdminError>) {
        let counter = match result {
            Ok(true) => &self.metrics.admin_mutations_replayed,
            Ok(false) => &self.metrics.admin_mutations_committed,
            Err(_) => &self.metrics.admin_mutations_refused,
        };
        counter.fetch_add(1, Ordering::Relaxed);
    }

    fn record_result<T>(&self, result: &Result<T, RouterError>) {
        if let Err(error) = result {
            match error {
                RouterError::Store(StateError::Limit(_)) | RouterError::InboundQos2Quota => {
                    self.metrics.reject(Rejection::Quota);
                }
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
        self.metrics
            .admin_receipts
            .store(count(self.state.admin_receipts.len()), Ordering::Relaxed);
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

    #[cfg(test)]
    async fn register_with_will(
        &mut self,
        client_id: String,
        principal: String,
        clean: bool,
        will: Option<StoredMessage>,
    ) -> Result<Session, RouterError> {
        self.register_with_policy(client_id, principal, clean, !clean, None, will)
            .await
    }

    #[cfg(test)]
    async fn register_with_policy(
        &mut self,
        client_id: String,
        principal: String,
        clean: bool,
        persistent: bool,
        expiry_interval_seconds: Option<u32>,
        will: Option<StoredMessage>,
    ) -> Result<Session, RouterError> {
        self.register_with_policy_and_delay(
            client_id,
            principal,
            SessionPolicy {
                clean,
                persistent,
                expiry_interval_seconds,
                will_delay_seconds: 0,
                receive_maximum: u16::MAX,
            },
            will,
        )
        .await
    }

    #[expect(
        clippy::too_many_lines,
        reason = "registration and prior Will resolution share one durable transition"
    )]
    async fn register_with_policy_and_delay(
        &mut self,
        client_id: String,
        principal: String,
        policy: SessionPolicy,
        will: Option<StoredMessage>,
    ) -> Result<Session, RouterError> {
        let SessionPolicy {
            clean,
            persistent,
            expiry_interval_seconds,
            will_delay_seconds,
            receive_maximum,
        } = policy;
        let now = unix_ms()?;
        let old = self
            .state
            .sessions
            .get(&client_id)
            .filter(|session| !session_expired(session, now));
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
        let previous_will = candidate.pending_wills.remove(&client_id);
        let mut prior_deliveries = Vec::new();
        let mut prior_will_published = false;
        let mut ended = Vec::new();
        if clean || !session_present {
            ended.extend(candidate.sessions.remove(&client_id));
            if let Some(prior) = previous_will
                && self
                    .auth
                    .allowed_publish(&prior.principal, prior.message.topic.as_str())
            {
                prior_deliveries = apply_message(
                    self.limits,
                    &mut candidate,
                    &self.live,
                    &self.auth,
                    &prior.message,
                    None,
                )?;
                prior_will_published = true;
            }
        }
        if self
            .state
            .sessions
            .get(&client_id)
            .is_some_and(|session| session_expired(session, now))
        {
            ended.extend(candidate.sessions.remove(&client_id));
        }
        reassign_ended_shared_qos1(
            self.limits,
            &mut candidate,
            &self.live,
            &self.auth,
            ended,
            &mut prior_deliveries,
        )?;
        if !session_present {
            candidate.sessions.insert(
                client_id.clone(),
                DurableSession::new(principal, persistent),
            );
        } else if let Some(session) = candidate.sessions.get_mut(&client_id) {
            session.persistent = persistent;
        }
        if let Some(session) = candidate.sessions.get_mut(&client_id) {
            session.expiry_interval_seconds = expiry_interval_seconds;
            session.expires_at_unix_ms = None;
        }
        if let Some(message) = will {
            candidate.pending_wills.insert(
                client_id.clone(),
                PendingWill {
                    principal: candidate.sessions[&client_id].principal.clone(),
                    message,
                    delay_seconds: will_delay_seconds,
                    publish_at_unix_ms: None,
                },
            );
        }
        let effective_maximum = self.limits.max_inflight.min(usize::from(receive_maximum));
        let mut replay = Vec::new();
        let mut pending_replay = VecDeque::new();
        let mut sent_unacked = BTreeSet::new();
        let mut replay_publish_count = 0;
        if session_present {
            let session = candidate
                .sessions
                .get_mut(&client_id)
                .ok_or(RouterError::Stale)?;
            for record in &session.outbound {
                let delivery = match record.stage {
                    OutboundStage::AwaitPubComp => Delivery::PubRel(record.packet_id),
                    OutboundStage::AwaitPubAck | OutboundStage::AwaitPubRec => Delivery::Publish {
                        message: record.message.clone(),
                        packet_id: Some(record.packet_id),
                        dup: true,
                    },
                };
                if matches!(delivery, Delivery::Publish { .. }) {
                    if replay_publish_count >= effective_maximum {
                        pending_replay.push_back(delivery);
                        continue;
                    }
                    replay_publish_count += 1;
                    sent_unacked.insert(record.packet_id);
                }
                replay.push(delivery);
            }
            if pending_replay.is_empty() {
                drain_offline(self.limits, session, &mut replay, effective_maximum, 0)?;
                for delivery in &replay {
                    if let Delivery::Publish {
                        packet_id: Some(packet_id),
                        ..
                    } = delivery
                    {
                        sent_unacked.insert(*packet_id);
                    }
                }
            }
        }
        self.commit(candidate).await?;
        if prior_will_published {
            self.metrics.wills.fetch_add(1, Ordering::Relaxed);
        }
        self.deliver(prior_deliveries);
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
                receive_maximum: effective_maximum,
                pending_replay,
                sent_unacked,
                inbound_accepted: BTreeSet::new(),
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

    #[cfg(test)]
    async fn subscribe(
        &mut self,
        client_id: &str,
        generation: u64,
        filters: Vec<(TopicFilter, Option<u8>)>,
    ) -> Result<(Vec<u8>, Vec<Delivery>), RouterError> {
        self.subscribe_with_handling(
            client_id,
            generation,
            filters
                .into_iter()
                .map(|(filter, qos)| (filter, qos, 0, 0))
                .collect(),
        )
        .await
    }

    #[cfg(test)]
    async fn subscribe_with_handling(
        &mut self,
        client_id: &str,
        generation: u64,
        filters: Vec<(TopicFilter, Option<u8>, u8, u8)>,
    ) -> Result<(Vec<u8>, Vec<Delivery>), RouterError> {
        self.subscribe_with_shared(client_id, generation, filters, None, false)
            .await
    }

    #[expect(
        clippy::too_many_lines,
        reason = "subscription validation, retained matching and one durable commit share an atomic transition"
    )]
    async fn subscribe_with_shared(
        &mut self,
        client_id: &str,
        generation: u64,
        filters: Vec<(TopicFilter, Option<u8>, u8, u8)>,
        identifier: Option<u32>,
        mqtt5_shared: bool,
    ) -> Result<(Vec<u8>, Vec<Delivery>), RouterError> {
        self.current(client_id, generation)?;
        let mut candidate = self.state.clone();
        let mut codes = Vec::with_capacity(filters.len());
        let mut retained_matches = BTreeMap::<_, (u8, Vec<u32>)>::new();
        for (filter, granted, retain_handling, subscription_flags) in filters {
            let inner = mqtt5_shared
                .then(|| super::topic::shared_inner(filter.as_str()))
                .flatten();
            let principal = &self
                .state
                .sessions
                .get(client_id)
                .ok_or(RouterError::Stale)?
                .principal;
            let Some(qos) = granted.filter(|_| {
                self.auth
                    .allowed_subscribe(principal, inner.unwrap_or(filter.as_str()))
            }) else {
                self.metrics.reject(Rejection::Authorization);
                codes.push(0x80);
                continue;
            };
            let session = candidate
                .sessions
                .get_mut(client_id)
                .ok_or(RouterError::Stale)?;
            let already_existed =
                update_subscription(session, &filter, qos, subscription_flags, identifier);
            if inner.is_some() {
                session.shared_filters.insert(filter.clone());
            } else {
                session.shared_filters.remove(&filter);
            }
            codes.push(qos);
            if inner.is_some() {
                continue;
            }
            if retain_handling == 2 || retain_handling == 1 && already_existed {
                continue;
            }
            for topic in candidate.retained.keys().filter(|topic| {
                filter.matches(topic) && self.auth.allowed_delivery(principal, topic.as_str())
            }) {
                add_retained_match(&mut retained_matches, topic, qos, identifier);
            }
        }
        if codes.iter().all(|code| *code >= 0x80) {
            return Ok((codes, Vec::new()));
        }
        let mut deliveries = Vec::with_capacity(retained_matches.len());
        let receive_maximum = self
            .live
            .get(client_id)
            .ok_or(RouterError::Stale)?
            .receive_maximum;
        for (topic, (maximum, identifiers)) in retained_matches {
            let mut delivered = candidate
                .retained
                .get(&topic)
                .cloned()
                .ok_or(RouterError::Stale)?;
            delivered.qos = delivered.qos.min(maximum);
            delivered.subscription_identifiers = identifiers;
            let session = candidate
                .sessions
                .get_mut(client_id)
                .ok_or(RouterError::Stale)?;
            let queued_publish_count = deliveries
                .iter()
                .filter(|delivery| {
                    matches!(
                        delivery,
                        Delivery::Publish {
                            packet_id: Some(_),
                            ..
                        }
                    )
                })
                .count();
            let outstanding = self.live[client_id].sent_unacked.len();
            if delivered.qos > 0
                && (session.outbound.len() >= self.limits.max_inflight
                    || outstanding + queued_publish_count >= receive_maximum)
            {
                session.offline.push_back(delivered);
            } else {
                deliveries.push(prepare_delivery(self.limits, session, delivered)?);
            }
        }
        self.commit(candidate).await?;
        if let Some(live) = self.live.get_mut(client_id) {
            for delivery in &deliveries {
                if let Delivery::Publish {
                    packet_id: Some(packet_id),
                    ..
                } = delivery
                {
                    live.sent_unacked.insert(*packet_id);
                }
            }
        }
        Ok((codes, deliveries))
    }

    async fn unsubscribe(
        &mut self,
        client_id: &str,
        generation: u64,
        filters: Vec<TopicFilter>,
    ) -> Result<Vec<u8>, RouterError> {
        self.current(client_id, generation)?;
        let mut candidate = self.state.clone();
        let session = candidate
            .sessions
            .get_mut(client_id)
            .ok_or(RouterError::Stale)?;
        let mut codes = Vec::with_capacity(filters.len());
        let mut changed = false;
        for filter in filters {
            let removed = session.subscriptions.remove(&filter).is_some();
            session.subscription_options.remove(&filter);
            session.subscription_identifiers.remove(&filter);
            session.shared_filters.remove(&filter);
            codes.push(if removed { 0x00 } else { 0x11 });
            changed |= removed;
        }
        if changed {
            self.commit(candidate).await?;
        }
        Ok(codes)
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
            if session.inbound_qos2.len() >= self.limits.max_inflight
                && self
                    .live
                    .get(client_id)
                    .is_some_and(|live| live.inbound_accepted.len() < self.limits.max_inflight)
            {
                return Err(RouterError::InboundQos2Quota);
            }
            session
                .inbound_qos2
                .push(InboundQos2 { packet_id, message });
            self.commit(candidate).await?;
            if let Some(live) = self.live.get_mut(client_id) {
                live.inbound_accepted.insert(packet_id);
            }
            self.metrics.received[qos].fetch_add(1, Ordering::Relaxed);
            return Ok(());
        }
        let deliveries = apply_message(
            self.limits,
            &mut candidate,
            &self.live,
            &self.auth,
            &message,
            Some(client_id),
        )?;
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
        let deliveries = apply_message(
            self.limits,
            &mut candidate,
            &self.live,
            &self.auth,
            &pending.message,
            Some(client_id),
        )?;
        self.commit(candidate).await?;
        if let Some(live) = self.live.get_mut(client_id) {
            live.inbound_accepted.remove(&packet_id);
        }
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
        let live = self.live.get(client_id).ok_or(RouterError::Stale)?;
        if live.pending_replay.iter().any(|delivery| {
            matches!(delivery, Delivery::Publish { packet_id: Some(id), .. } if *id == packet_id)
        }) {
            return Err(RouterError::Stale);
        }
        let receive_maximum = live.receive_maximum;
        let has_pending_replay = !live.pending_replay.is_empty();
        let replenishes_quota = live.sent_unacked.contains(&packet_id);
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
                if !has_pending_replay
                    && (replenishes_quota || live.sent_unacked.len() < receive_maximum)
                {
                    drain_offline(
                        self.limits,
                        session,
                        &mut actions,
                        receive_maximum,
                        live.sent_unacked.len() - usize::from(replenishes_quota),
                    )?;
                }
                self.commit(candidate).await?;
                if let Some(live) = self.live.get_mut(client_id)
                    && live.sent_unacked.remove(&packet_id)
                    && let Some(pending) = live.pending_replay.pop_front()
                {
                    self.deliver(vec![(client_id.to_owned(), pending)]);
                }
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

    async fn discard_outbound(
        &mut self,
        client_id: &str,
        generation: u64,
        packet_id: u16,
    ) -> Result<(), RouterError> {
        self.current(client_id, generation)?;
        let live = self.live.get(client_id).ok_or(RouterError::Stale)?;
        if live.pending_replay.iter().any(|delivery| {
            matches!(delivery, Delivery::Publish { packet_id: Some(id), .. } if *id == packet_id)
        }) {
            return Err(RouterError::Stale);
        }
        let receive_maximum = live.receive_maximum;
        let has_pending_replay = !live.pending_replay.is_empty();
        let replenishes_quota = live.sent_unacked.contains(&packet_id);
        let mut candidate = self.state.clone();
        let session = candidate
            .sessions
            .get_mut(client_id)
            .ok_or(RouterError::Stale)?;
        let index = session
            .outbound
            .iter()
            .position(|item| item.packet_id == packet_id)
            .ok_or(RouterError::Stale)?;
        session.outbound.remove(index);
        let mut actions = Vec::new();
        if !has_pending_replay && (replenishes_quota || live.sent_unacked.len() < receive_maximum) {
            drain_offline(
                self.limits,
                session,
                &mut actions,
                receive_maximum,
                live.sent_unacked.len() - usize::from(replenishes_quota),
            )?;
        }
        self.commit(candidate).await?;
        if let Some(live) = self.live.get_mut(client_id)
            && live.sent_unacked.remove(&packet_id)
            && let Some(pending) = live.pending_replay.pop_front()
        {
            self.deliver(vec![(client_id.to_owned(), pending)]);
        }
        self.deliver(
            actions
                .into_iter()
                .map(|delivery| (client_id.to_owned(), delivery))
                .collect(),
        );
        Ok(())
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
        self.unregister_with_receipt(client_id, generation, graceful, None, None)
            .await
    }

    async fn unregister_with_receipt(
        &mut self,
        client_id: &str,
        generation: u64,
        graceful: bool,
        expiry_override: Option<u32>,
        receipt: Option<AdminReceipt>,
    ) -> Result<(), RouterError> {
        self.current(client_id, generation)?;
        let mut candidate = self.state.clone();
        if let Some(expiry) = expiry_override {
            let session = candidate
                .sessions
                .get_mut(client_id)
                .ok_or(RouterError::Stale)?;
            if !session.persistent && expiry != 0 {
                return Err(RouterError::InvalidSessionExpiry);
            }
            session.persistent = expiry != 0;
            session.expiry_interval_seconds = (1..u32::MAX).contains(&expiry).then_some(expiry);
        }
        let will = candidate.pending_wills.remove(client_id);
        let had_will = will.is_some();
        let now = unix_ms()?;
        if let Some(session) = candidate.sessions.get_mut(client_id)
            && let Some(seconds) = session.expiry_interval_seconds
        {
            session.expires_at_unix_ms = Some(expiry_deadline(now, seconds)?);
        }
        let ended = if candidate
            .sessions
            .get(client_id)
            .is_some_and(|s| s.persistent)
        {
            Vec::new()
        } else {
            candidate.sessions.remove(client_id).into_iter().collect()
        };
        let mut remaining_live = self.live.clone();
        remaining_live.remove(client_id);
        let mut deliveries = Vec::new();
        reassign_ended_shared_qos1(
            self.limits,
            &mut candidate,
            &remaining_live,
            &self.auth,
            ended,
            &mut deliveries,
        )?;
        let mut published = false;
        if let Some(mut will) = will.filter(|_| !graceful)
            && self
                .auth
                .allowed_publish(&will.principal, will.message.topic.as_str())
        {
            let deadline = expiry_deadline(now, will.delay_seconds)?;
            let deadline = candidate
                .sessions
                .get(client_id)
                .and_then(|session| session.expires_at_unix_ms)
                .map_or(deadline, |end| deadline.min(end));
            if deadline <= now || !candidate.sessions.contains_key(client_id) {
                published = true;
                deliveries = match apply_message(
                    self.limits,
                    &mut candidate,
                    &remaining_live,
                    &self.auth,
                    &will.message,
                    None,
                ) {
                    Ok(deliveries) => deliveries,
                    Err(error) => {
                        self.fail_closed();
                        return Err(error);
                    }
                };
            } else {
                will.publish_at_unix_ms = Some(deadline);
                candidate.pending_wills.insert(client_id.to_owned(), will);
            }
        }
        if let Some(receipt) = receipt {
            candidate.admin_receipts.push(receipt);
        }
        // MQTT-3.1.2-10 and MQTT-3.14.4-3: cancellation/publication is durable.
        // A failed Will must remain pending; continuing would allow takeover
        // to replace that obligation or route to a connection already gone.
        if let Err(error) = self.commit(candidate).await {
            if had_will {
                self.fail_closed();
            }
            return Err(error);
        }
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
            if let Some(live) = self.live.get_mut(&client_id) {
                let packet_id = match &delivery {
                    Delivery::Publish {
                        packet_id: Some(packet_id),
                        ..
                    } => Some(*packet_id),
                    _ => None,
                };
                if packet_id.is_some() && live.sent_unacked.len() >= live.receive_maximum {
                    self.metrics.reject(Rejection::Delivery);
                    let _ = live.close.send(true);
                    continue;
                }
                if live.sender.try_send(delivery).is_err() {
                    self.metrics.reject(Rejection::Delivery);
                    let _ = live.close.send(true);
                } else if let Some(packet_id) = packet_id {
                    live.sent_unacked.insert(packet_id);
                }
            }
        }
    }
}

fn add_retained_match(
    matches: &mut BTreeMap<TopicName, (u8, Vec<u32>)>,
    topic: &TopicName,
    qos: u8,
    identifier: Option<u32>,
) {
    let (maximum, ids) = matches
        .entry(topic.clone())
        .or_insert_with(|| (qos, Vec::new()));
    *maximum = (*maximum).max(qos);
    if let Some(id) = identifier {
        ids.push(id);
    }
}

fn update_subscription(
    session: &mut DurableSession,
    filter: &TopicFilter,
    qos: u8,
    flags: u8,
    identifier: Option<u32>,
) -> bool {
    let existed = session.subscriptions.insert(filter.clone(), qos).is_some();
    if flags == 0 {
        session.subscription_options.remove(filter);
    } else {
        session.subscription_options.insert(filter.clone(), flags);
    }
    if let Some(id) = identifier {
        session.subscription_identifiers.insert(filter.clone(), id);
    } else {
        session.subscription_identifiers.remove(filter);
    }
    existed
}

fn apply_message(
    limits: StateLimits,
    state: &mut DurableState,
    live: &BTreeMap<String, Live>,
    auth: &AccessPolicy,
    message: &StoredMessage,
    publisher_id: Option<&str>,
) -> Result<Vec<(String, Delivery)>, RouterError> {
    let expired = message_expired(message, unix_ms()?);
    if message.retain {
        if message.payload.is_empty() || expired {
            state.retained.remove(&message.topic);
        } else {
            state
                .retained
                .insert(message.topic.clone(), message.clone());
        }
    }
    if expired {
        return Ok(Vec::new());
    }
    let mut deliveries = Vec::new();
    let mut groups: BTreeMap<TopicFilter, Vec<SharedCandidate>> = BTreeMap::new();
    for (client_id, session) in &mut state.sessions {
        if !auth.allowed_delivery(&session.principal, message.topic.as_str()) {
            continue;
        }
        if live.contains_key(client_id) || session.persistent {
            for filter in &session.shared_filters {
                let Some(inner) = super::topic::shared_inner(filter.as_str()) else {
                    continue;
                };
                if !super::topic::matches_filter(inner, message.topic.as_str()) {
                    continue;
                }
                if let Some(&qos) = session.subscriptions.get(filter) {
                    let preserve_retain = session
                        .subscription_options
                        .get(filter)
                        .is_some_and(|bits| bits & 0x08 != 0);
                    groups
                        .entry(filter.clone())
                        .or_default()
                        .push(SharedCandidate {
                            client_id: client_id.clone(),
                            active: live.contains_key(client_id),
                            qos,
                            preserve_retain,
                            identifier: session.subscription_identifiers.get(filter).copied(),
                        });
                }
            }
        }
        let matching = session.subscriptions.iter().filter(|(filter, _)| {
            !session.shared_filters.contains(*filter)
                && filter.matches(&message.topic)
                && !(publisher_id == Some(client_id.as_str())
                    && session
                        .subscription_options
                        .get(*filter)
                        .is_some_and(|bits| bits & 0x04 != 0))
        });
        let mut maximum = None;
        let mut preserve_retain = false;
        let mut identifiers = Vec::new();
        for (filter, qos) in matching {
            maximum = Some(maximum.map_or(*qos, |value: u8| value.max(*qos)));
            preserve_retain |= session
                .subscription_options
                .get(filter)
                .is_some_and(|bits| bits & 0x08 != 0);
            if let Some(id) = session.subscription_identifiers.get(filter) {
                identifiers.push(*id);
            }
        }
        let Some(maximum) = maximum else {
            continue;
        };
        let mut outbound = message.clone();
        outbound.qos = outbound.qos.min(maximum);
        outbound.retain &= preserve_retain;
        outbound.subscription_identifiers = identifiers;
        if let Some(connection) = live.get(client_id) {
            if outbound.qos > 0
                && (session.outbound.len() >= limits.max_inflight
                    || connection.sent_unacked.len() >= connection.receive_maximum)
            {
                session.offline.push_back(outbound);
            } else {
                let delivery = prepare_delivery(limits, session, outbound)?;
                deliveries.push((client_id.clone(), delivery));
            }
        } else if session.persistent && outbound.qos > 0 {
            session.offline.push_back(outbound);
        }
    }
    apply_shared_deliveries(limits, state, live, message, &groups, &mut deliveries)?;
    Ok(deliveries)
}

fn apply_shared_deliveries(
    limits: StateLimits,
    state: &mut DurableState,
    live: &BTreeMap<String, Live>,
    message: &StoredMessage,
    groups: &BTreeMap<TopicFilter, Vec<SharedCandidate>>,
    deliveries: &mut Vec<(String, Delivery)>,
) -> Result<(), RouterError> {
    if groups.is_empty() {
        return Ok(());
    }
    let turn = state.shared_cursor;
    state.shared_cursor = state.shared_cursor.wrapping_add(1);
    for (filter, members) in groups {
        let active: Vec<_> = members.iter().filter(|member| member.active).collect();
        let choices = if active.is_empty() {
            members.iter().collect::<Vec<_>>()
        } else {
            active
        };
        let modulus = u64::try_from(choices.len()).unwrap_or(u64::MAX);
        let index = usize::try_from(turn % modulus).unwrap_or_default();
        let choice = choices[index];
        let session = state
            .sessions
            .get_mut(&choice.client_id)
            .ok_or(RouterError::Stale)?;
        let mut outbound = message.clone();
        outbound.qos = outbound.qos.min(choice.qos);
        outbound.shared_origin = (outbound.qos == 1).then(|| SharedOrigin {
            filter: filter.clone(),
            retained: message.retain,
        });
        outbound.retain &= choice.preserve_retain;
        outbound.subscription_identifiers = choice.identifier.into_iter().collect();
        let Some(connection) = live.get(&choice.client_id) else {
            if outbound.qos > 0 && session.persistent {
                session.offline.push_back(outbound);
            }
            continue;
        };
        let queued = deliveries
            .iter()
            .filter(|(recipient, delivery)| {
                recipient == &choice.client_id
                    && matches!(
                        delivery,
                        Delivery::Publish {
                            packet_id: Some(_),
                            ..
                        }
                    )
            })
            .count();
        if outbound.qos > 0
            && (session.outbound.len() >= limits.max_inflight
                || connection.sent_unacked.len() + queued >= connection.receive_maximum)
        {
            session.offline.push_back(outbound);
        } else {
            let delivery = prepare_delivery(limits, session, outbound)?;
            deliveries.push((choice.client_id.clone(), delivery));
        }
    }
    Ok(())
}

/// Reassign only unacknowledged shared `QoS1` copies owned by sessions that have
/// ended. The source PUBLISH Retain bit is kept separately from the old
/// member's RAP choice, so the new member receives its own options and ID.
#[expect(
    clippy::too_many_lines,
    reason = "candidate selection and durable routing share one transition"
)]
fn reassign_ended_shared_qos1(
    limits: StateLimits,
    state: &mut DurableState,
    live: &BTreeMap<String, Live>,
    auth: &AccessPolicy,
    ended: Vec<DurableSession>,
    deliveries: &mut Vec<(String, Delivery)>,
) -> Result<(), RouterError> {
    let now = unix_ms()?;
    for session in ended {
        let pending = session
            .outbound
            .into_iter()
            .filter(|entry| entry.stage == OutboundStage::AwaitPubAck)
            .map(|entry| entry.message)
            .chain(session.offline);
        for mut message in pending {
            let Some(origin) = message.shared_origin.clone() else {
                continue;
            };
            if message_expired(&message, now) {
                continue;
            }
            let Some(inner) = super::topic::shared_inner(origin.filter.as_str()) else {
                return Err(StateError::Malformed.into());
            };
            let mut active = Vec::new();
            let mut offline = Vec::new();
            for (client_id, member) in &state.sessions {
                if !member.shared_filters.contains(&origin.filter)
                    || !super::topic::matches_filter(inner, message.topic.as_str())
                    || !auth.allowed_delivery(&member.principal, message.topic.as_str())
                    || !auth.allowed_subscribe(&member.principal, inner)
                {
                    continue;
                }
                let Some(&qos) = member.subscriptions.get(&origin.filter) else {
                    continue;
                };
                let connection = live.get(client_id);
                let outgoing_qos = message.qos.min(qos);
                let queued = deliveries
                    .iter()
                    .filter(|(recipient, delivery)| {
                        recipient == client_id
                            && matches!(
                                delivery,
                                Delivery::Publish {
                                    packet_id: Some(_),
                                    ..
                                }
                            )
                    })
                    .count();
                let immediate = connection.is_some_and(|connection| {
                    outgoing_qos == 0
                        || (member.outbound.len() < limits.max_inflight
                            && connection.sent_unacked.len() + queued < connection.receive_maximum)
                });
                let can_queue = outgoing_qos > 0
                    && (connection.is_some() || member.persistent)
                    && member.offline.len() < limits.max_offline;
                if !immediate && !can_queue {
                    continue;
                }
                let choice = SharedCandidate {
                    client_id: client_id.clone(),
                    active: connection.is_some(),
                    qos,
                    preserve_retain: member
                        .subscription_options
                        .get(&origin.filter)
                        .is_some_and(|bits| bits & 0x08 != 0),
                    identifier: member.subscription_identifiers.get(&origin.filter).copied(),
                };
                if choice.active {
                    active.push(choice);
                } else {
                    offline.push(choice);
                }
            }
            let choices = if active.is_empty() { &offline } else { &active };
            if choices.is_empty() {
                // No eligible member or capacity: the recommendation is best
                // effort, and ending the source session cannot retain its copy.
                continue;
            }
            let modulus = u64::try_from(choices.len()).unwrap_or(u64::MAX);
            let index = usize::try_from(state.shared_cursor % modulus).unwrap_or_default();
            state.shared_cursor = state.shared_cursor.wrapping_add(1);
            let choice = &choices[index];
            message.qos = message.qos.min(choice.qos);
            message.retain = origin.retained && choice.preserve_retain;
            message.subscription_identifiers = choice.identifier.into_iter().collect();
            message.shared_origin = (message.qos == 1).then_some(origin);
            let member = state
                .sessions
                .get_mut(&choice.client_id)
                .ok_or(RouterError::Stale)?;
            let connection = live.get(&choice.client_id);
            let queued = deliveries
                .iter()
                .filter(|(recipient, delivery)| {
                    recipient == &choice.client_id
                        && matches!(
                            delivery,
                            Delivery::Publish {
                                packet_id: Some(_),
                                ..
                            }
                        )
                })
                .count();
            if connection.is_some_and(|connection| {
                message.qos == 0
                    || (member.outbound.len() < limits.max_inflight
                        && connection.sent_unacked.len() + queued < connection.receive_maximum)
            }) {
                let delivery = prepare_delivery(limits, member, message)?;
                deliveries.push((choice.client_id.clone(), delivery));
            } else {
                member.offline.push_back(message);
            }
        }
    }
    Ok(())
}

fn prepare_delivery(
    limits: StateLimits,
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
    if session.outbound.len() >= limits.max_inflight {
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
    limits: StateLimits,
    session: &mut DurableSession,
    actions: &mut Vec<Delivery>,
    receive_maximum: usize,
    sent_unacked: usize,
) -> Result<(), RouterError> {
    let now = unix_ms()?;
    while session.outbound.len() < limits.max_inflight
        && sent_unacked
            + actions
                .iter()
                .filter(|action| {
                    matches!(
                        action,
                        Delivery::Publish {
                            packet_id: Some(_),
                            ..
                        }
                    )
                })
                .count()
            < receive_maximum
    {
        let Some(message) = session.offline.pop_front() else {
            break;
        };
        if message_expired(&message, now) {
            continue;
        }
        actions.push(prepare_delivery(limits, session, message)?);
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
    #[tokio::test]
    async fn audit_rotation_is_allowed_at_full_receipt_capacity() {
        let (_directory, mut actor) = actor().await;
        let mut candidate = actor.state.clone();
        for index in 0..MAX_ADMIN_RECEIPTS {
            candidate.admin_receipts.push(AdminReceipt {
                request_id: format!("{index:032x}"),
                operation: "retained_delete".into(),
                outcome: "committed".into(),
                request_sha256: "a".repeat(64),
                expected_generation: 0,
                applied_generation: 0,
                actor_uid: 1000,
                timestamp_unix_ms: 1,
                epoch: 0,
                archive_count: 0,
            });
        }
        actor.commit(candidate).await.unwrap();
        let items = actor.admin_audit_page(0, MAX_ADMIN_RECEIPTS).items;
        let digest = format!("{:x}", Sha256::digest(serde_json::to_vec(&items).unwrap()));
        assert_eq!(
            actor
                .admin_rotate_audit("ffffffffffffffffffffffffffffffff".into(), digest, 128, 1000)
                .await
                .unwrap(),
            (1, false)
        );
        assert_eq!(actor.state.admin_receipts.len(), 1);
        assert_eq!(actor.state.retired_admin_ids.len(), 128);
        actor.store.shutdown().await.unwrap();
    }

    #[cfg(unix)]
    #[tokio::test]
    async fn audit_rotation_wal_error_preserves_receipts_and_epoch() {
        use crate::persistence::faults::{Action, Fault, Point};
        let (directory, mut actor) = actor().await;
        let topic = TopicName::try_from("test/state".to_owned()).unwrap();
        let mut candidate = actor.state.clone();
        candidate
            .retained
            .insert(topic.clone(), message("test/state", 1, true, b"private"));
        actor.commit(candidate).await.unwrap();
        actor
            .admin_delete_retained(topic, "0123456789abcdef0123456789abcdef".into(), 1000)
            .await
            .unwrap();
        let items = actor.admin_audit_page(0, MAX_ADMIN_RECEIPTS).items;
        let digest = format!("{:x}", Sha256::digest(serde_json::to_vec(&items).unwrap()));
        actor
            .store
            .inject_for_test(Fault {
                point: Point::WalAppend,
                action: Action::ErrorAfter(6, 28),
            })
            .await
            .unwrap();
        assert!(matches!(
            actor
                .admin_rotate_audit("fedcba9876543210fedcba9876543210".into(), digest, 1, 1000)
                .await,
            Err(AdminError::CommitFailed)
        ));
        assert!(actor.fatal);
        assert_eq!(actor.state.admin_epoch, 0);
        assert_eq!(actor.state.admin_receipts.len(), 1);
        actor.store.shutdown().await.unwrap();
        let (store, recovered) = MqttStore::open(directory.path()).await.unwrap();
        assert_eq!(recovered.admin_epoch, 0);
        assert_eq!(recovered.admin_receipts.len(), 1);
        store.shutdown().await.unwrap();
    }

    #[tokio::test]
    async fn audit_rotation_preserves_old_id_safety_and_restarts_in_new_epoch() {
        let (directory, mut actor) = actor().await;
        let topic = TopicName::try_from("test/state".to_owned()).unwrap();
        let mut candidate = actor.state.clone();
        candidate
            .retained
            .insert(topic.clone(), message("test/state", 1, true, b"private"));
        actor.commit(candidate).await.unwrap();
        let old_id = "0123456789abcdef0123456789abcdef".to_owned();
        assert!(
            !actor
                .admin_delete_retained(topic.clone(), old_id.clone(), 1000)
                .await
                .unwrap()
        );
        let items = actor.admin_audit_page(0, MAX_ADMIN_RECEIPTS).items;
        let digest = format!("{:x}", Sha256::digest(serde_json::to_vec(&items).unwrap()));
        let rotate_id = "fedcba9876543210fedcba9876543210".to_owned();
        assert!(matches!(
            actor
                .admin_rotate_audit(rotate_id.clone(), "0".repeat(64), 1, 1000)
                .await,
            Err(AdminError::ArchiveChanged)
        ));
        assert_eq!(actor.state.admin_epoch, 0);
        assert_eq!(
            actor
                .admin_rotate_audit(rotate_id.clone(), digest.clone(), 1, 1000)
                .await
                .unwrap(),
            (1, false)
        );
        assert_eq!(actor.state.admin_epoch, 1);
        assert_eq!(actor.state.admin_receipts.len(), 1);
        assert!(actor.state.retired_admin_ids.contains(&old_id));
        assert_eq!(
            actor
                .admin_rotate_audit(rotate_id, digest, 1, 1000)
                .await
                .unwrap(),
            (1, true)
        );
        assert!(matches!(
            actor
                .admin_delete_retained(topic.clone(), old_id.clone(), 1000)
                .await,
            Err(AdminError::StaleEpoch)
        ));
        let mut candidate = actor.state.clone();
        candidate
            .retained
            .insert(topic.clone(), message("test/state", 1, true, b"new"));
        actor.commit(candidate).await.unwrap();
        assert!(matches!(
            actor
                .admin_delete_retained(
                    topic.clone(),
                    "99999999000000000000000000000000".into(),
                    1000
                )
                .await,
            Err(AdminError::StaleEpoch)
        ));
        assert!(
            !actor
                .admin_delete_retained(topic, "00000001aaaaaaaaaaaaaaaaaaaaaaaa".into(), 1000)
                .await
                .unwrap()
        );
        actor.store.shutdown().await.unwrap();
        let (store, recovered) = MqttStore::open(directory.path()).await.unwrap();
        assert_eq!(recovered.admin_epoch, 1);
        assert_eq!(recovered.admin_receipts.len(), 2);
        assert!(recovered.retired_admin_ids.contains(&old_id));
        store.shutdown().await.unwrap();
    }

    #[tokio::test]
    async fn admin_disconnect_commits_will_qos2_and_receipt_once() {
        let (directory, mut actor) = actor().await;
        let session = actor
            .register_with_will(
                "device".into(),
                "user".into(),
                false,
                Some(message("test/state", 1, true, b"will")),
            )
            .await
            .unwrap();
        actor
            .publish(
                "device",
                session.generation,
                message("test/state", 2, false, b"accepted"),
                Some(7),
            )
            .await
            .unwrap();
        let id = "0123456789abcdef0123456789abcdef".to_owned();
        assert!(
            !actor
                .admin_disconnect_session("device", id.clone(), 1000)
                .await
                .unwrap()
        );
        assert!(*session.closed.borrow());
        assert_eq!(actor.state.sessions["device"].inbound_qos2.len(), 1);
        assert_eq!(actor.state.retained["test/state"].payload, b"will");
        assert_eq!(
            actor.state.admin_receipts[0].operation,
            "session_disconnect"
        );
        let audit = actor.admin_audit_page(0, 1);
        assert_eq!(audit.items[0]["operation"], "session_disconnect");
        assert!(audit.items[0].get("client_id").is_none());
        assert!(
            actor
                .admin_disconnect_session("device", id.clone(), 1000)
                .await
                .unwrap()
        );
        assert!(matches!(
            actor
                .admin_disconnect_session("device", "fedcba9876543210fedcba9876543210".into(), 1000)
                .await,
            Err(AdminError::NotFound)
        ));
        assert!(matches!(
            actor.admin_disconnect_session("other", id, 1000).await,
            Err(AdminError::Conflict)
        ));
        actor.store.shutdown().await.unwrap();
        let (store, recovered) = MqttStore::open(directory.path()).await.unwrap();
        assert_eq!(recovered.sessions["device"].inbound_qos2.len(), 1);
        assert_eq!(recovered.retained["test/state"].payload, b"will");
        assert_eq!(recovered.admin_receipts.len(), 1);
        store.shutdown().await.unwrap();
    }

    #[cfg(unix)]
    #[tokio::test]
    async fn admin_disconnect_wal_error_preserves_will_and_refuses_success() {
        use crate::persistence::faults::{Action, Fault, Point};
        let (directory, mut actor) = actor().await;
        let session = actor
            .register_with_will(
                "device".into(),
                "user".into(),
                false,
                Some(message("test/state", 1, true, b"will")),
            )
            .await
            .unwrap();
        actor
            .store
            .inject_for_test(Fault {
                point: Point::WalAppend,
                action: Action::ErrorAfter(6, 28),
            })
            .await
            .unwrap();
        assert!(matches!(
            actor
                .admin_disconnect_session("device", "0123456789abcdef0123456789abcdef".into(), 1000)
                .await,
            Err(AdminError::CommitFailed)
        ));
        assert!(actor.fatal);
        assert_eq!(actor.state.pending_wills.len(), 1);
        assert_eq!(actor.state.admin_receipts.len(), 0);
        actor.store.shutdown().await.unwrap();
        let (store, recovered) = MqttStore::open(directory.path()).await.unwrap();
        assert_eq!(recovered.pending_wills.len(), 1);
        assert_eq!(recovered.admin_receipts.len(), 0);
        store.shutdown().await.unwrap();
        drop(session);
    }

    #[tokio::test]
    async fn admin_retained_delete_commits_receipt_and_deduplicates_after_restart() {
        let (directory, mut actor) = actor().await;
        let topic = TopicName::try_from("private/value".to_owned()).unwrap();
        let mut candidate = actor.state.clone();
        candidate
            .retained
            .insert(topic.clone(), message("private/value", 1, true, b"hidden"));
        actor.commit(candidate).await.unwrap();
        let id = "0123456789abcdef0123456789abcdef".to_owned();
        assert!(
            !actor
                .admin_delete_retained(topic.clone(), id.clone(), 1000)
                .await
                .unwrap()
        );
        assert!(actor.state.retained.is_empty());
        assert!(
            actor
                .admin_delete_retained(topic.clone(), id.clone(), 1000)
                .await
                .unwrap()
        );
        assert!(matches!(
            actor
                .admin_delete_retained(TopicName::try_from("other".to_owned()).unwrap(), id, 1000)
                .await,
            Err(AdminError::Conflict)
        ));
        assert!(matches!(
            actor
                .admin_delete_retained(topic, "fedcba9876543210fedcba9876543210".into(), 1000)
                .await,
            Err(AdminError::NotFound)
        ));
        actor.store.shutdown().await.unwrap();
        let (store, recovered) = MqttStore::open(directory.path()).await.unwrap();
        assert!(recovered.retained.is_empty());
        assert_eq!(recovered.admin_receipts.len(), 1);
        assert_eq!(recovered.admin_receipts[0].operation, "retained_delete");
        store.shutdown().await.unwrap();
    }

    #[cfg(unix)]
    #[tokio::test]
    async fn admin_retained_delete_wal_error_never_reports_success() {
        use crate::persistence::faults::{Action, Fault, Point};
        let (directory, mut actor) = actor().await;
        let topic = TopicName::try_from("private/value".to_owned()).unwrap();
        let mut candidate = actor.state.clone();
        candidate
            .retained
            .insert(topic.clone(), message("private/value", 1, true, b"hidden"));
        actor.commit(candidate).await.unwrap();
        actor
            .store
            .inject_for_test(Fault {
                point: Point::WalAppend,
                action: Action::ErrorAfter(6, 28),
            })
            .await
            .unwrap();
        assert!(matches!(
            actor
                .admin_delete_retained(
                    topic.clone(),
                    "0123456789abcdef0123456789abcdef".into(),
                    1000
                )
                .await,
            Err(AdminError::CommitFailed)
        ));
        assert!(actor.fatal);
        assert!(actor.state.retained.contains_key(&topic));
        assert_eq!(actor.state.admin_receipts.len(), 0);
        actor.store.shutdown().await.unwrap();
        let (store, recovered) = MqttStore::open(directory.path()).await.unwrap();
        assert!(recovered.retained.contains_key(&topic));
        assert_eq!(recovered.admin_receipts.len(), 0);
        store.shutdown().await.unwrap();
    }

    #[tokio::test]
    async fn admin_inventory_is_paginated_and_never_returns_payloads() {
        let (_directory, mut actor) = actor().await;
        actor
            .state
            .sessions
            .insert("a".into(), DurableSession::new("owner".into(), true));
        actor
            .state
            .sessions
            .insert("b".into(), DurableSession::new("owner".into(), true));
        actor.state.retained.insert(
            TopicName::try_from("private/a".to_owned()).unwrap(),
            message("private/a", 1, true, b"secret-payload"),
        );
        actor.state.retained.insert(
            TopicName::try_from("private/b".to_owned()).unwrap(),
            message("private/b", 1, true, b"secret-payload"),
        );
        let first = actor.admin_list_page(AdminListKind::Sessions, None, 1);
        assert_eq!(first.items.len(), 1);
        assert_eq!(first.next_cursor.as_deref(), Some("a"));
        let second =
            actor.admin_list_page(AdminListKind::Sessions, first.next_cursor.as_deref(), 1);
        assert_eq!(second.items[0]["client_id"], "b");
        assert!(second.next_cursor.is_none());
        let retained = actor.admin_list_page(AdminListKind::Retained, None, 1);
        assert_eq!(retained.next_cursor.as_deref(), Some("private/a"));
        assert_eq!(retained.items[0]["payload_bytes"], 14);
        assert!(!retained.items[0].to_string().contains("secret-payload"));
        actor.store.shutdown().await.unwrap();
    }

    #[cfg(unix)]
    #[tokio::test]
    async fn storage_failure_closes_all_live_sessions_and_preserves_offline_candidate() {
        use crate::persistence::faults::{Action, Fault, Point};
        let (directory, mut actor) = actor().await;
        let publisher = actor
            .register("pub".into(), "user".into(), false)
            .await
            .unwrap();
        let mut online = actor
            .register("online".into(), "user".into(), false)
            .await
            .unwrap();
        let offline = actor
            .register("offline".into(), "user".into(), false)
            .await
            .unwrap();
        for session in [&online, &offline] {
            actor
                .subscribe(
                    &session.client_id,
                    session.generation,
                    vec![(filter("test/state"), Some(1))],
                )
                .await
                .unwrap();
        }
        actor
            .unregister_with_reason("offline", offline.generation, true)
            .await
            .unwrap();
        let before = actor.state.clone();
        actor
            .store
            .inject_for_test(Fault {
                point: Point::WalAppend,
                action: Action::ErrorAfter(6, 28),
            })
            .await
            .unwrap();
        assert!(
            actor
                .publish(
                    "pub",
                    publisher.generation,
                    message("test/state", 1, true, b"candidate"),
                    Some(7)
                )
                .await
                .is_err()
        );
        assert_eq!(actor.state, before);
        assert!(actor.fatal);
        assert!(*publisher.closed.borrow());
        assert!(*online.closed.borrow());
        assert!(online.outbound.try_recv().is_err());
        assert!(!actor.metrics.actor_alive.load(Ordering::Relaxed));
        actor.store.shutdown().await.unwrap();
        let (store, recovered) = MqttStore::open(directory.path()).await.unwrap();
        assert_eq!(recovered, before);
        store.shutdown().await.unwrap();
    }

    #[cfg(unix)]
    #[tokio::test]
    async fn snapshot_failure_after_durable_commit_refuses_reply_and_fanout_but_recovers_commit() {
        use crate::persistence::faults::{Action, Fault, Point};
        for point in [
            Point::SnapshotWrite,
            Point::DirectorySync,
            Point::WalCompactSync,
        ] {
            let (directory, mut actor) = actor().await;
            let publisher = actor
                .register("pub".into(), "user".into(), false)
                .await
                .unwrap();
            let mut subscriber = actor
                .register("sub".into(), "user".into(), false)
                .await
                .unwrap();
            actor
                .subscribe(
                    "sub",
                    subscriber.generation,
                    vec![(filter("test/state"), Some(1))],
                )
                .await
                .unwrap();
            actor.commits_since_snapshot = 127;
            actor
                .store
                .inject_for_test(Fault {
                    point,
                    action: Action::Error(5),
                })
                .await
                .unwrap();
            assert!(
                actor
                    .publish(
                        "pub",
                        publisher.generation,
                        message("test/state", 1, true, b"committed-no-ack"),
                        Some(7)
                    )
                    .await
                    .is_err()
            );
            assert!(actor.fatal);
            assert!(*publisher.closed.borrow());
            assert!(*subscriber.closed.borrow());
            assert!(subscriber.outbound.try_recv().is_err());
            assert_eq!(
                actor.state.retained["test/state"].payload,
                b"committed-no-ack"
            );
            actor.store.shutdown().await.unwrap();
            let (store, recovered) = MqttStore::open(directory.path()).await.unwrap();
            assert_eq!(recovered, actor.state);
            assert_eq!(recovered.sessions["sub"].outbound.len(), 1);
            store.shutdown().await.unwrap();
        }
    }

    #[cfg_attr(not(unix), ignore = "requires Unix directory fsync")]
    #[tokio::test]
    async fn saturated_will_closes_actor_and_preserves_obligation_until_compatible_restart() {
        let (directory, mut actor) = actor().await;
        actor.limits = StateLimits::new(64, 256, 256, 1, 32).unwrap();
        // The store and actor must enforce the same process quotas.
        actor.store.shutdown().await.unwrap();
        let (store, state) = MqttStore::open_with_limits(directory.path(), actor.limits)
            .await
            .unwrap();
        actor.store = store;
        actor.state = state;
        let subscriber = actor
            .register("sub".into(), "user".into(), false)
            .await
            .unwrap();
        actor
            .subscribe(
                "sub",
                subscriber.generation,
                vec![(filter("test/state"), Some(1))],
            )
            .await
            .unwrap();
        actor
            .unregister_with_reason("sub", subscriber.generation, true)
            .await
            .unwrap();
        let publisher = actor
            .register_with_will(
                "pub".into(),
                "user".into(),
                false,
                Some(message("test/state", 1, false, b"pending-will")),
            )
            .await
            .unwrap();
        actor
            .publish(
                "pub",
                publisher.generation,
                message("test/state", 1, false, b"already-queued"),
                Some(1),
            )
            .await
            .unwrap();
        let committed = actor.state.clone();
        assert!(matches!(
            actor
                .unregister_with_reason("pub", publisher.generation, false)
                .await,
            Err(RouterError::Store(StateError::Limit(_)))
        ));
        assert!(actor.fatal);
        assert!(*publisher.closed.borrow());
        assert_eq!(actor.state, committed);
        actor.store.shutdown().await.unwrap();

        // Recovery also fails without erasing the Will or holding the writer.
        for _ in 0..2 {
            assert!(
                Router::start_observed_with_limits(
                    directory.path(),
                    actor.auth.clone(),
                    Arc::default(),
                    actor.limits
                )
                .await
                .is_err()
            );
            let (store, recovered) = MqttStore::open(directory.path()).await.unwrap();
            assert_eq!(recovered, committed);
            store.shutdown().await.unwrap();
        }
        let router = Router::start(directory.path(), actor.auth.clone())
            .await
            .unwrap();
        let resumed = router
            .register("sub".into(), "user".into(), false)
            .await
            .unwrap();
        let payloads: Vec<_> = resumed
            .replay
            .iter()
            .map(|delivery| match delivery {
                Delivery::Publish { message, .. } => message.payload.clone(),
                Delivery::PubRel(_) => panic!("unexpected PUBREL"),
            })
            .collect();
        assert_eq!(
            payloads,
            [b"already-queued".to_vec(), b"pending-will".to_vec()]
        );
        router.shutdown().await.unwrap();
    }

    #[test]
    fn configured_inflight_defers_and_drains_without_losing_order() {
        let limits = StateLimits::new(64, 256, 256, 64, 1).unwrap();
        let mut session = DurableSession::new("user".into(), true);
        let first = StoredMessage {
            topic: super::super::topic::TopicName::try_from("test/first".to_owned()).unwrap(),
            payload: vec![1],
            qos: 1,
            retain: false,
            expiry_at_unix_ms: None,
            payload_format_indicator: None,
            content_type: None,
            response_topic: None,
            correlation_data: None,
            user_properties: Vec::new(),
            subscription_identifiers: Vec::new(),
            shared_origin: None,
        };
        let second = StoredMessage {
            topic: super::super::topic::TopicName::try_from("test/second".to_owned()).unwrap(),
            payload: vec![2],
            qos: 1,
            retain: false,
            expiry_at_unix_ms: None,
            payload_format_indicator: None,
            content_type: None,
            response_topic: None,
            correlation_data: None,
            user_properties: Vec::new(),
            subscription_identifiers: Vec::new(),
            shared_origin: None,
        };
        prepare_delivery(limits, &mut session, first.clone()).unwrap();
        assert!(prepare_delivery(limits, &mut session, second.clone()).is_err());
        session.offline.push_back(second.clone());
        let mut actions = Vec::new();
        drain_offline(limits, &mut session, &mut actions, limits.max_inflight, 0).unwrap();
        assert!(actions.is_empty());
        assert_eq!(session.offline.front(), Some(&second));
        session.outbound.clear();
        drain_offline(limits, &mut session, &mut actions, limits.max_inflight, 0).unwrap();
        assert_eq!(actions.len(), 1);
        assert!(session.offline.is_empty());
        assert_eq!(session.outbound[0].message, second);
    }

    #[tokio::test]
    async fn mqtt5_receive_maximum_one_defers_qos_and_allows_qos_zero() {
        let (_directory, mut actor) = actor().await;
        let mut subscriber = actor
            .register_with_policy_and_delay(
                "rx-one".into(),
                "user".into(),
                SessionPolicy {
                    clean: true,
                    persistent: true,
                    expiry_interval_seconds: None,
                    will_delay_seconds: 0,
                    receive_maximum: 1,
                },
                None,
            )
            .await
            .unwrap();
        actor
            .subscribe(
                "rx-one",
                subscriber.generation,
                vec![(filter("test/+"), Some(1))],
            )
            .await
            .unwrap();
        let publisher = actor
            .register("source".into(), "user".into(), true)
            .await
            .unwrap();
        for payload in [b"first".as_slice(), b"second".as_slice()] {
            actor
                .publish(
                    "source",
                    publisher.generation,
                    message("test/qos", 1, false, payload),
                    Some(7),
                )
                .await
                .unwrap();
        }
        let Delivery::Publish {
            packet_id: Some(first_id),
            ..
        } = subscriber.outbound.try_recv().unwrap()
        else {
            panic!("expected first QoS 1 publication");
        };
        assert!(subscriber.outbound.try_recv().is_err());
        assert_eq!(actor.state.sessions["rx-one"].offline.len(), 1);
        actor
            .publish(
                "source",
                publisher.generation,
                message("test/qos", 0, false, b"qos-zero"),
                None,
            )
            .await
            .unwrap();
        assert!(matches!(
            subscriber.outbound.try_recv(),
            Ok(Delivery::Publish {
                packet_id: None,
                ..
            })
        ));
        actor
            .ack("rx-one", subscriber.generation, AckKind::Ack, first_id)
            .await
            .unwrap();
        assert!(
            matches!(subscriber.outbound.try_recv(), Ok(Delivery::Publish { message, packet_id: Some(_), .. }) if message.payload == b"second")
        );
        actor.store.shutdown().await.unwrap();
    }

    #[tokio::test]
    async fn mqtt5_receive_maximum_replay_is_paced_after_smaller_reconnect() {
        let (_directory, mut actor) = actor().await;
        let policy = |clean, receive_maximum| SessionPolicy {
            clean,
            persistent: true,
            expiry_interval_seconds: None,
            will_delay_seconds: 0,
            receive_maximum,
        };
        let mut subscriber = actor
            .register_with_policy_and_delay(
                "rx-replay".into(),
                "user".into(),
                policy(true, 2),
                None,
            )
            .await
            .unwrap();
        actor
            .subscribe(
                "rx-replay",
                subscriber.generation,
                vec![(filter("test/+"), Some(1))],
            )
            .await
            .unwrap();
        let publisher = actor
            .register("source".into(), "user".into(), true)
            .await
            .unwrap();
        for payload in [b"one", b"two"] {
            actor
                .publish(
                    "source",
                    publisher.generation,
                    message("test/replay", 1, false, payload),
                    Some(8),
                )
                .await
                .unwrap();
        }
        assert!(subscriber.outbound.try_recv().is_ok());
        assert!(subscriber.outbound.try_recv().is_ok());
        actor
            .unregister_with_reason("rx-replay", subscriber.generation, false)
            .await
            .unwrap();
        subscriber = actor
            .register_with_policy_and_delay(
                "rx-replay".into(),
                "user".into(),
                policy(false, 1),
                None,
            )
            .await
            .unwrap();
        assert!(subscriber.resumed);
        assert_eq!(subscriber.replay.len(), 1);
        assert_eq!(actor.live["rx-replay"].pending_replay.len(), 1);
        let Delivery::Publish {
            packet_id: Some(first_id),
            ..
        } = &subscriber.replay[0]
        else {
            panic!("expected replay PUBLISH");
        };
        actor
            .ack("rx-replay", subscriber.generation, AckKind::Ack, *first_id)
            .await
            .unwrap();
        assert!(
            matches!(subscriber.outbound.try_recv(), Ok(Delivery::Publish { message, dup: true, .. }) if message.payload == b"two")
        );
        actor.store.shutdown().await.unwrap();
    }

    #[tokio::test]
    async fn mqtt5_receive_maximum_qos2_waits_for_pubcomp() {
        let (_directory, mut actor) = actor().await;
        let mut subscriber = actor
            .register_with_policy_and_delay(
                "rx-qos2".into(),
                "user".into(),
                SessionPolicy {
                    clean: true,
                    persistent: true,
                    expiry_interval_seconds: None,
                    will_delay_seconds: 0,
                    receive_maximum: 1,
                },
                None,
            )
            .await
            .unwrap();
        actor
            .subscribe(
                "rx-qos2",
                subscriber.generation,
                vec![(filter("test/+"), Some(2))],
            )
            .await
            .unwrap();
        let publisher = actor
            .register("source".into(), "user".into(), true)
            .await
            .unwrap();
        for (id, payload) in [(1, b"one".as_slice()), (2, b"two".as_slice())] {
            actor
                .publish(
                    "source",
                    publisher.generation,
                    message("test/qos2", 2, false, payload),
                    Some(id),
                )
                .await
                .unwrap();
            actor
                .pubrel("source", publisher.generation, id)
                .await
                .unwrap();
        }
        let Delivery::Publish {
            packet_id: Some(first_id),
            ..
        } = subscriber.outbound.try_recv().unwrap()
        else {
            panic!("expected QoS 2 PUBLISH");
        };
        assert!(subscriber.outbound.try_recv().is_err());
        assert!(
            matches!(actor.ack("rx-qos2", subscriber.generation, AckKind::Rec, first_id).await.unwrap().as_slice(), [Delivery::PubRel(id)] if *id == first_id)
        );
        assert!(subscriber.outbound.try_recv().is_err());
        actor
            .ack("rx-qos2", subscriber.generation, AckKind::Comp, first_id)
            .await
            .unwrap();
        assert!(
            matches!(subscriber.outbound.try_recv(), Ok(Delivery::Publish { message, .. }) if message.payload == b"two")
        );
        actor.store.shutdown().await.unwrap();
    }

    #[tokio::test]
    async fn mqtt5_receive_maximum_paces_retained_delivery() {
        let (_directory, mut actor) = actor().await;
        let publisher = actor
            .register("source".into(), "user".into(), true)
            .await
            .unwrap();
        for (topic, payload) in [
            ("test/a", b"first".as_slice()),
            ("test/b", b"second".as_slice()),
        ] {
            actor
                .publish(
                    "source",
                    publisher.generation,
                    message(topic, 1, true, payload),
                    Some(7),
                )
                .await
                .unwrap();
        }
        let mut subscriber = actor
            .register_with_policy_and_delay(
                "rx-retained".into(),
                "user".into(),
                SessionPolicy {
                    clean: true,
                    persistent: true,
                    expiry_interval_seconds: None,
                    will_delay_seconds: 0,
                    receive_maximum: 1,
                },
                None,
            )
            .await
            .unwrap();
        let (_, deliveries) = actor
            .subscribe(
                "rx-retained",
                subscriber.generation,
                vec![(filter("test/+"), Some(1))],
            )
            .await
            .unwrap();
        let [
            Delivery::Publish {
                packet_id: Some(first_id),
                message: first,
                ..
            },
        ] = deliveries.as_slice()
        else {
            panic!("expected one retained PUBLISH");
        };
        assert_eq!(first.payload, b"first");
        assert_eq!(actor.state.sessions["rx-retained"].offline.len(), 1);
        actor
            .ack(
                "rx-retained",
                subscriber.generation,
                AckKind::Ack,
                *first_id,
            )
            .await
            .unwrap();
        assert!(matches!(
            subscriber.outbound.try_recv(),
            Ok(Delivery::Publish { message, .. }) if message.payload == b"second" && message.retain
        ));
        actor.store.shutdown().await.unwrap();
    }

    #[tokio::test]
    async fn mqtt5_oversized_delivery_is_discarded_and_releases_quota() {
        let (_directory, mut actor) = actor().await;
        let mut subscriber = actor
            .register_with_policy_and_delay(
                "rx-size".into(),
                "user".into(),
                SessionPolicy {
                    clean: true,
                    persistent: true,
                    expiry_interval_seconds: None,
                    will_delay_seconds: 0,
                    receive_maximum: 1,
                },
                None,
            )
            .await
            .unwrap();
        actor
            .subscribe(
                "rx-size",
                subscriber.generation,
                vec![(filter("test/+"), Some(1))],
            )
            .await
            .unwrap();
        let publisher = actor
            .register("source".into(), "user".into(), true)
            .await
            .unwrap();
        for payload in [b"oversized".as_slice(), b"small".as_slice()] {
            actor
                .publish(
                    "source",
                    publisher.generation,
                    message("test/size", 1, false, payload),
                    Some(7),
                )
                .await
                .unwrap();
        }
        let Delivery::Publish {
            packet_id: Some(first_id),
            ..
        } = subscriber.outbound.try_recv().unwrap()
        else {
            panic!("expected first delivery");
        };
        assert!(subscriber.outbound.try_recv().is_err());
        actor
            .discard_outbound("rx-size", subscriber.generation, first_id)
            .await
            .unwrap();
        assert!(matches!(
            subscriber.outbound.try_recv(),
            Ok(Delivery::Publish { message, .. }) if message.payload == b"small"
        ));
        assert_eq!(actor.state.sessions["rx-size"].outbound.len(), 1);
        assert!(actor.state.sessions["rx-size"].offline.is_empty());
        actor.store.shutdown().await.unwrap();
    }

    use super::*;
    use crate::{auth::AuthPolicy, mqtt::topic::TopicName};
    use argon2::{
        Algorithm, Argon2, Params, Version,
        password_hash::{PasswordHasher, SaltString},
    };
    use sha2::{Digest, Sha256};
    use std::{fmt::Write as _, fs, sync::Arc};
    use tempfile::TempDir;

    #[test]
    fn expiry_clock_rejects_pre_epoch_and_deadline_overflow() {
        assert!(matches!(
            unix_ms_from(UNIX_EPOCH - Duration::from_secs(1)),
            Err(RouterError::Clock)
        ));
        assert!(matches!(
            expiry_deadline(u64::MAX, 1),
            Err(RouterError::Clock)
        ));
        assert_eq!(expiry_deadline(1_000, 2).unwrap(), 3_000);
    }

    #[tokio::test]
    async fn full_delivery_channel_closes_only_slow_session_and_keeps_actor_progress() {
        let (_directory, mut actor) = actor().await;
        let slow = actor
            .register("slow".into(), "user".into(), true)
            .await
            .unwrap();
        let mut fast = actor
            .register("fast".into(), "user".into(), true)
            .await
            .unwrap();
        let publisher = actor
            .register("publisher".into(), "user".into(), true)
            .await
            .unwrap();
        for session in [&slow, &fast] {
            actor
                .subscribe(
                    &session.client_id,
                    session.generation,
                    vec![(filter("test/state"), Some(0))],
                )
                .await
                .unwrap();
        }
        // QoS0 has no acknowledgment; a full bounded delivery channel must
        // close the slow connection, not block the shared actor or fast peer.
        for index in 0..=DELIVERY_CAPACITY {
            actor
                .publish(
                    "publisher",
                    publisher.generation,
                    message("test/state", 0, false, &index.to_be_bytes()),
                    None,
                )
                .await
                .unwrap();
            let delivery = fast.outbound.try_recv().unwrap();
            assert!(
                matches!(delivery, Delivery::Publish { message, packet_id: None, .. }
                if message.payload == index.to_be_bytes())
            );
        }
        assert_eq!(slow.outbound.len(), DELIVERY_CAPACITY);
        assert!(*slow.closed.borrow());
        assert!(!*fast.closed.borrow());
        assert!(actor.probe().await);
        actor.store.shutdown().await.unwrap();
    }

    #[tokio::test]
    async fn slow_session_quota_refusal_does_not_commit_partial_fanout_or_retained() {
        let (directory, mut actor) = actor().await;
        actor.limits = StateLimits::new(64, 256, 256, 1, 1).unwrap();
        actor.store.shutdown().await.unwrap();
        let (store, state) = MqttStore::open_with_limits(directory.path(), actor.limits)
            .await
            .unwrap();
        actor.store = store;
        actor.state = state;
        let slow = actor
            .register("slow".into(), "user".into(), false)
            .await
            .unwrap();
        let mut fast = actor
            .register("fast".into(), "user".into(), true)
            .await
            .unwrap();
        let publisher = actor
            .register("publisher".into(), "user".into(), true)
            .await
            .unwrap();
        for session in [&slow, &fast] {
            actor
                .subscribe(
                    &session.client_id,
                    session.generation,
                    vec![(filter("test/state"), Some(1))],
                )
                .await
                .unwrap();
        }
        for index in 1..=2u8 {
            actor
                .publish(
                    "publisher",
                    publisher.generation,
                    message("test/state", 1, true, &[index]),
                    Some(u16::from(index)),
                )
                .await
                .unwrap();
            let delivery = fast.outbound.try_recv().unwrap();
            let Delivery::Publish {
                packet_id: Some(id),
                ..
            } = delivery
            else {
                panic!("expected QoS1");
            };
            actor
                .ack("fast", fast.generation, AckKind::Ack, id)
                .await
                .unwrap();
        }
        let before = actor.state.clone();
        assert!(matches!(
            actor
                .publish(
                    "publisher",
                    publisher.generation,
                    message("test/state", 1, true, b"refused"),
                    Some(3)
                )
                .await,
            Err(RouterError::Store(StateError::Limit(_)))
        ));
        assert_eq!(actor.state, before);
        assert!(fast.outbound.try_recv().is_err());
        assert_eq!(actor.state.sessions["slow"].outbound.len(), 1);
        assert_eq!(actor.state.sessions["slow"].offline.len(), 1);
        assert!(actor.probe().await);
        actor.store.shutdown().await.unwrap();
    }

    async fn actor() -> (TempDir, Actor) {
        let directory = tempfile::tempdir().unwrap();
        let (store, state) = MqttStore::open(directory.path()).await.unwrap();
        let auth = Arc::new(AccessPolicy::password_lab(policy(directory.path(), true)));
        (
            directory,
            Actor {
                limits: StateLimits::default(),
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

    #[tokio::test]
    async fn mqtt5_shared_routes_one_member_per_group_without_initial_retained() {
        let (directory, mut actor) = actor().await;
        let publisher = actor
            .register("source".into(), "user".into(), true)
            .await
            .unwrap();
        actor
            .publish(
                "source",
                publisher.generation,
                message("test/state", 0, true, b"retained"),
                None,
            )
            .await
            .unwrap();
        let mut first = actor
            .register("first".into(), "user".into(), true)
            .await
            .unwrap();
        let mut second = actor
            .register("second".into(), "user".into(), true)
            .await
            .unwrap();
        let mut normal = actor
            .register("normal".into(), "user".into(), true)
            .await
            .unwrap();
        for session in [&first, &second] {
            let (codes, retained) = actor
                .subscribe_with_shared(
                    &session.client_id,
                    session.generation,
                    vec![(filter("$share/g/test/#"), Some(0), 0, 0)],
                    Some(7),
                    true,
                )
                .await
                .unwrap();
            assert_eq!(codes, [0]);
            assert!(retained.is_empty());
        }
        let (codes, retained) = actor
            .subscribe_with_shared(
                "normal",
                normal.generation,
                vec![(filter("test/#"), Some(0), 0, 0)],
                Some(8),
                true,
            )
            .await
            .unwrap();
        assert_eq!(codes, [0]);
        assert_eq!(retained.len(), 1);
        for number in 0..4 {
            actor
                .publish(
                    "source",
                    publisher.generation,
                    message("test/state", 0, false, &[number]),
                    None,
                )
                .await
                .unwrap();
        }
        let mut first_count = 0;
        let mut second_count = 0;
        for receiver in [&mut first, &mut second] {
            while let Ok(Delivery::Publish { message, .. }) = receiver.outbound.try_recv() {
                assert_eq!(message.subscription_identifiers, [7]);
                if receiver.client_id == "first" {
                    first_count += 1;
                } else {
                    second_count += 1;
                }
            }
        }
        assert_eq!((first_count, second_count), (2, 2));
        for _ in 0..4 {
            assert!(matches!(normal.outbound.try_recv(),
                Ok(Delivery::Publish { message, .. }) if message.subscription_identifiers == [8]));
        }
        assert!(normal.outbound.try_recv().is_err());
        assert_eq!(
            actor
                .unsubscribe("first", first.generation, vec![filter("$share/g/test/#")])
                .await
                .unwrap(),
            [0]
        );
        actor.store.shutdown().await.unwrap();
        let (store, mut recovered) = MqttStore::open(directory.path()).await.unwrap();
        reconcile_recovered_sessions(&mut recovered, &actor.auth, actor.limits).unwrap();
        assert!(recovered.sessions.is_empty());
        store.shutdown().await.unwrap();
    }

    #[tokio::test]
    async fn mqtt5_shared_qos1_unacked_moves_to_surviving_member_only_until_puback() {
        let (_directory, mut actor) = actor().await;
        let mut first = actor
            .register("alpha".into(), "user".into(), true)
            .await
            .unwrap();
        let mut second = actor
            .register("beta".into(), "user".into(), true)
            .await
            .unwrap();
        let publisher = actor
            .register("source".into(), "user".into(), true)
            .await
            .unwrap();
        let group = filter("$share/g/test/state");
        for (session, identifier, options) in [(&first, 7, 0), (&second, 9, 0x08)] {
            let (codes, retained) = actor
                .subscribe_with_shared(
                    &session.client_id,
                    session.generation,
                    vec![(group.clone(), Some(1), 0, options)],
                    Some(identifier),
                    true,
                )
                .await
                .unwrap();
            assert_eq!(codes, [1]);
            assert!(retained.is_empty());
        }
        actor
            .publish(
                "source",
                publisher.generation,
                message("test/state", 1, true, b"move-once"),
                Some(21),
            )
            .await
            .unwrap();
        let Delivery::Publish {
            packet_id: Some(_),
            message,
            ..
        } = first.outbound.try_recv().unwrap()
        else {
            panic!("first shared member must receive QoS1");
        };
        assert_eq!(message.subscription_identifiers, [7]);
        assert!(message.shared_origin.is_some());
        assert!(second.outbound.try_recv().is_err());
        actor.unregister("alpha", first.generation).await.unwrap();
        let Delivery::Publish {
            packet_id: Some(id),
            message,
            ..
        } = second.outbound.try_recv().unwrap()
        else {
            panic!("surviving member must receive reassigned QoS1");
        };
        assert_eq!(message.payload, b"move-once");
        assert_eq!(message.subscription_identifiers, [9]);
        assert!(
            message.retain,
            "survivor's RAP restores the original Retain bit"
        );
        assert_eq!(message.shared_origin.unwrap().filter, group);
        actor
            .ack("beta", second.generation, AckKind::Ack, id)
            .await
            .unwrap();
        assert_eq!(actor.state.sessions["beta"].outbound.len(), 0);
        actor.unregister("beta", second.generation).await.unwrap();
        assert!(!actor.state.sessions.contains_key("beta"));
        actor.store.shutdown().await.unwrap();
    }

    #[tokio::test]
    async fn mqtt5_shared_qos1_reassigns_temporary_member_after_recovery() {
        let (directory, mut actor) = actor().await;
        let mut first = actor
            .register("alpha".into(), "user".into(), true)
            .await
            .unwrap();
        let second = actor
            .register("beta".into(), "user".into(), false)
            .await
            .unwrap();
        let publisher = actor
            .register("source".into(), "user".into(), true)
            .await
            .unwrap();
        let group = filter("$share/g/test/state");
        for session in [&first, &second] {
            actor
                .subscribe_with_shared(
                    &session.client_id,
                    session.generation,
                    vec![(group.clone(), Some(1), 0, 0)],
                    None,
                    true,
                )
                .await
                .unwrap();
        }
        actor
            .publish(
                "source",
                publisher.generation,
                message("test/state", 1, false, b"after-crash"),
                Some(22),
            )
            .await
            .unwrap();
        assert!(matches!(
            first.outbound.try_recv(),
            Ok(Delivery::Publish {
                packet_id: Some(_),
                ..
            })
        ));
        actor.store.shutdown().await.unwrap();
        let (store, mut recovered) = MqttStore::open(directory.path()).await.unwrap();
        reconcile_recovered_sessions(&mut recovered, &actor.auth, actor.limits).unwrap();
        assert!(!recovered.sessions.contains_key("alpha"));
        assert_eq!(recovered.sessions["beta"].offline.len(), 1);
        assert_eq!(
            recovered.sessions["beta"].offline[0].payload,
            b"after-crash"
        );
        assert_eq!(
            recovered.sessions["beta"].offline[0]
                .shared_origin
                .as_ref()
                .unwrap()
                .filter,
            group
        );
        store.shutdown().await.unwrap();
    }

    #[tokio::test]
    async fn mqtt5_shared_qos1_reassigns_when_finite_session_expires() {
        let (_directory, mut actor) = actor().await;
        let mut first = actor
            .register_with_policy("alpha".into(), "user".into(), true, true, Some(1), None)
            .await
            .unwrap();
        let mut second = actor
            .register("beta".into(), "user".into(), true)
            .await
            .unwrap();
        let publisher = actor
            .register("source".into(), "user".into(), true)
            .await
            .unwrap();
        for session in [&first, &second] {
            actor
                .subscribe_with_shared(
                    &session.client_id,
                    session.generation,
                    vec![(filter("$share/g/test/state"), Some(1), 0, 0)],
                    None,
                    true,
                )
                .await
                .unwrap();
        }
        actor
            .publish(
                "source",
                publisher.generation,
                message("test/state", 1, false, b"expire"),
                Some(23),
            )
            .await
            .unwrap();
        assert!(matches!(
            first.outbound.try_recv(),
            Ok(Delivery::Publish {
                packet_id: Some(_),
                ..
            })
        ));
        actor.unregister("alpha", first.generation).await.unwrap();
        assert!(second.outbound.try_recv().is_err());
        tokio::time::sleep(Duration::from_millis(1100)).await;
        actor.expire_sessions().await.unwrap();
        assert!(!actor.state.sessions.contains_key("alpha"));
        assert!(matches!(second.outbound.try_recv(),
            Ok(Delivery::Publish { message, packet_id: Some(_), .. }) if message.payload == b"expire"));
        actor.store.shutdown().await.unwrap();
    }

    #[tokio::test]
    async fn mqtt5_shared_qos1_explicit_expiry_zero_moves_to_active_member() {
        let (_directory, mut actor) = actor().await;
        let mut first = actor
            .register("alpha".into(), "user".into(), false)
            .await
            .unwrap();
        let mut second = actor
            .register("beta".into(), "user".into(), true)
            .await
            .unwrap();
        let publisher = actor
            .register("source".into(), "user".into(), true)
            .await
            .unwrap();
        for session in [&first, &second] {
            actor
                .subscribe_with_shared(
                    &session.client_id,
                    session.generation,
                    vec![(filter("$share/g/test/state"), Some(1), 0, 0)],
                    None,
                    true,
                )
                .await
                .unwrap();
        }
        actor
            .publish(
                "source",
                publisher.generation,
                message("test/state", 1, false, b"override"),
                Some(25),
            )
            .await
            .unwrap();
        assert!(matches!(
            first.outbound.try_recv(),
            Ok(Delivery::Publish {
                packet_id: Some(_),
                ..
            })
        ));
        actor
            .unregister_with_receipt("alpha", first.generation, true, Some(0), None)
            .await
            .unwrap();
        assert!(!actor.state.sessions.contains_key("alpha"));
        assert!(matches!(second.outbound.try_recv(),
            Ok(Delivery::Publish { message, packet_id: Some(_), .. }) if message.payload == b"override"));
        actor.store.shutdown().await.unwrap();
    }

    #[tokio::test]
    async fn mqtt5_shared_qos1_ended_last_member_discards_unacked_copy() {
        let (_directory, mut actor) = actor().await;
        let mut first = actor
            .register("alpha".into(), "user".into(), true)
            .await
            .unwrap();
        let publisher = actor
            .register("source".into(), "user".into(), true)
            .await
            .unwrap();
        actor
            .subscribe_with_shared(
                "alpha",
                first.generation,
                vec![(filter("$share/g/test/state"), Some(1), 0, 0)],
                None,
                true,
            )
            .await
            .unwrap();
        actor
            .publish(
                "source",
                publisher.generation,
                message("test/state", 1, false, b"orphan"),
                Some(26),
            )
            .await
            .unwrap();
        assert!(matches!(
            first.outbound.try_recv(),
            Ok(Delivery::Publish {
                packet_id: Some(_),
                ..
            })
        ));
        actor.unregister("alpha", first.generation).await.unwrap();
        assert!(!actor.state.sessions.contains_key("alpha"));
        assert_eq!(actor.state.sessions["source"].outbound.len(), 0);
        actor.store.shutdown().await.unwrap();
    }

    #[tokio::test]
    async fn mqtt5_shared_qos1_full_survivor_queue_is_skipped_without_partial_state() {
        let (_directory, mut actor) = actor().await;
        let group = filter("$share/g/test/state");
        let mut survivor = DurableSession::new("user".into(), true);
        survivor.subscriptions.insert(group.clone(), 1);
        survivor.shared_filters.insert(group.clone());
        survivor
            .offline
            .push_back(message("queue/full", 1, false, b"prior"));
        actor.state.sessions.insert("survivor".into(), survivor);
        let mut ended = DurableSession::new("user".into(), false);
        let mut unacked = message("test/state", 1, false, b"unacked");
        unacked.shared_origin = Some(SharedOrigin {
            filter: group,
            retained: false,
        });
        ended.outbound.push(OutboundInflight {
            packet_id: 1,
            message: unacked,
            stage: OutboundStage::AwaitPubAck,
        });
        let before = actor.state.clone();
        let mut deliveries = Vec::new();
        let limits = StateLimits::new(64, 256, 256, 1, 32).unwrap();
        reassign_ended_shared_qos1(
            limits,
            &mut actor.state,
            &BTreeMap::new(),
            &actor.auth,
            vec![ended],
            &mut deliveries,
        )
        .unwrap();
        assert_eq!(actor.state, before);
        assert_eq!(deliveries.len(), 0);
        actor.store.shutdown().await.unwrap();
    }

    #[tokio::test]
    async fn mqtt5_shared_qos1_redistribution_commit_failure_is_atomic() {
        use crate::persistence::faults::{Action, Fault, Point};
        let (directory, mut actor) = actor().await;
        let mut first = actor
            .register("alpha".into(), "user".into(), true)
            .await
            .unwrap();
        let mut second = actor
            .register("beta".into(), "user".into(), true)
            .await
            .unwrap();
        let publisher = actor
            .register("source".into(), "user".into(), true)
            .await
            .unwrap();
        for session in [&first, &second] {
            actor
                .subscribe_with_shared(
                    &session.client_id,
                    session.generation,
                    vec![(filter("$share/g/test/state"), Some(1), 0, 0)],
                    None,
                    true,
                )
                .await
                .unwrap();
        }
        actor
            .publish(
                "source",
                publisher.generation,
                message("test/state", 1, false, b"atomic"),
                Some(24),
            )
            .await
            .unwrap();
        assert!(matches!(
            first.outbound.try_recv(),
            Ok(Delivery::Publish {
                packet_id: Some(_),
                ..
            })
        ));
        let before = actor.state.clone();
        actor
            .store
            .inject_for_test(Fault {
                point: Point::WalAppend,
                action: Action::ErrorAfter(6, 28),
            })
            .await
            .unwrap();
        assert!(actor.unregister("alpha", first.generation).await.is_err());
        assert_eq!(actor.state, before);
        assert!(second.outbound.try_recv().is_err());
        actor.store.shutdown().await.unwrap();
        let (store, recovered) = MqttStore::open(directory.path()).await.unwrap();
        let mut persisted = before;
        persisted.shared_cursor = 0;
        assert_eq!(recovered, persisted);
        store.shutdown().await.unwrap();
    }

    #[tokio::test]
    async fn mqtt5_shared_persistent_acl_and_normal_copy_are_independent() {
        let (directory, mut actor) = actor().await;
        actor.auth = Arc::new(AccessPolicy::acl_lab(policy(directory.path(), true)));
        let publisher = actor
            .register("source".into(), "user".into(), true)
            .await
            .unwrap();
        let mut member = actor
            .register("member".into(), "user".into(), true)
            .await
            .unwrap();
        let persistent = actor
            .register("persistent".into(), "user".into(), false)
            .await
            .unwrap();
        let (codes, retained) = actor
            .subscribe_with_shared(
                "persistent",
                persistent.generation,
                vec![(filter("$share/durable/test/state"), Some(1), 0, 0)],
                None,
                true,
            )
            .await
            .unwrap();
        assert_eq!(codes, [1]);
        assert!(retained.is_empty());
        assert!(
            actor.state.sessions["persistent"]
                .shared_filters
                .contains(&filter("$share/durable/test/state"))
        );
        let (codes, _) = actor
            .subscribe_with_shared(
                "member",
                member.generation,
                vec![(filter("$share/g/forbidden/#"), Some(1), 0, 0)],
                None,
                true,
            )
            .await
            .unwrap();
        assert_eq!(codes, [0x80]);
        assert!(actor.state.sessions["member"].shared_filters.is_empty());
        actor
            .subscribe_with_shared(
                "member",
                member.generation,
                vec![(filter("$share/g/test/state"), Some(1), 0, 0)],
                Some(3),
                true,
            )
            .await
            .unwrap();
        actor
            .subscribe_with_shared(
                "member",
                member.generation,
                vec![(filter("test/state"), Some(1), 0, 0)],
                Some(4),
                true,
            )
            .await
            .unwrap();
        actor
            .publish(
                "source",
                publisher.generation,
                message("test/state", 1, false, b"both"),
                Some(10),
            )
            .await
            .unwrap();
        let mut ids = Vec::new();
        for _ in 0..2 {
            let Delivery::Publish {
                message,
                packet_id: Some(id),
                ..
            } = member.outbound.try_recv().unwrap()
            else {
                panic!("expected QoS1 delivery");
            };
            ids.push(message.subscription_identifiers);
            actor
                .ack("member", member.generation, AckKind::Ack, id)
                .await
                .unwrap();
        }
        ids.sort();
        assert_eq!(ids, [vec![3], vec![4]]);
        assert!(
            matches!(actor.state.sessions["persistent"].outbound.as_slice(),
            [OutboundInflight { message, .. }] if message.payload == b"both")
        );
        actor.store.shutdown().await.unwrap();
    }

    #[tokio::test]
    async fn mqtt5_shared_offline_qos2_replays_to_the_chosen_persistent_session() {
        let (directory, mut actor) = actor().await;
        let subscriber = actor
            .register("durable".into(), "user".into(), false)
            .await
            .unwrap();
        let (codes, retained) = actor
            .subscribe_with_shared(
                "durable",
                subscriber.generation,
                vec![(filter("$share/workers/test/state"), Some(2), 0, 0)],
                Some(17),
                true,
            )
            .await
            .unwrap();
        assert_eq!(codes, [2]);
        assert!(retained.is_empty());
        actor
            .unregister("durable", subscriber.generation)
            .await
            .unwrap();
        let publisher = actor
            .register("source".into(), "user".into(), true)
            .await
            .unwrap();
        actor
            .publish(
                "source",
                publisher.generation,
                message("test/state", 2, false, b"assigned"),
                Some(7),
            )
            .await
            .unwrap();
        actor
            .pubrel("source", publisher.generation, 7)
            .await
            .unwrap();
        assert_eq!(actor.state.sessions["durable"].offline.len(), 1);
        assert_eq!(
            actor.state.sessions["durable"].offline[0].subscription_identifiers,
            [17]
        );
        actor.store.shutdown().await.unwrap();
        let (store, mut recovered) = MqttStore::open(directory.path()).await.unwrap();
        reconcile_recovered_sessions(&mut recovered, &actor.auth, actor.limits).unwrap();
        assert!(
            recovered.sessions["durable"]
                .shared_filters
                .contains(&filter("$share/workers/test/state"))
        );
        actor.store = store;
        actor.state = recovered;
        actor.live.clear();
        let resumed = actor
            .register("durable".into(), "user".into(), false)
            .await
            .unwrap();
        assert!(resumed.resumed);
        assert!(matches!(resumed.replay.as_slice(),
            [Delivery::Publish { message, packet_id: Some(_), .. }]
                if message.payload == b"assigned" && message.subscription_identifiers == [17]));
        actor.store.shutdown().await.unwrap();
    }

    #[tokio::test]
    async fn mqtt5_shared_inflight_qos2_stays_with_its_chosen_session_after_restart() {
        let (directory, mut actor) = actor().await;
        let mut first = actor
            .register("first".into(), "user".into(), false)
            .await
            .unwrap();
        let mut second = actor
            .register("second".into(), "user".into(), false)
            .await
            .unwrap();
        for session in [&first, &second] {
            actor
                .subscribe_with_shared(
                    &session.client_id,
                    session.generation,
                    vec![(filter("$share/workers/test/state"), Some(2), 0, 0)],
                    None,
                    true,
                )
                .await
                .unwrap();
        }
        let publisher = actor
            .register("source".into(), "user".into(), true)
            .await
            .unwrap();
        actor
            .publish(
                "source",
                publisher.generation,
                message("test/state", 2, false, b"chosen"),
                Some(9),
            )
            .await
            .unwrap();
        actor
            .pubrel("source", publisher.generation, 9)
            .await
            .unwrap();
        assert!(
            matches!(first.outbound.try_recv(), Ok(Delivery::Publish { message, .. })
            if message.payload == b"chosen")
        );
        assert!(second.outbound.try_recv().is_err());
        actor.store.shutdown().await.unwrap();
        let (store, mut recovered) = MqttStore::open(directory.path()).await.unwrap();
        reconcile_recovered_sessions(&mut recovered, &actor.auth, actor.limits).unwrap();
        actor.store = store;
        actor.state = recovered;
        actor.live.clear();
        let other = actor
            .register("second".into(), "user".into(), false)
            .await
            .unwrap();
        assert!(other.replay.is_empty());
        let chosen = actor
            .register("first".into(), "user".into(), false)
            .await
            .unwrap();
        assert!(
            matches!(chosen.replay.as_slice(), [Delivery::Publish { message, dup: true, .. }]
            if message.payload == b"chosen")
        );
        actor.store.shutdown().await.unwrap();
    }

    #[tokio::test]
    async fn resumed_qos2_full_quota_refuses_new_id_without_losing_old_transaction() {
        let (directory, mut actor) = actor().await;
        let limits = StateLimits {
            max_inflight: 1,
            ..actor.limits
        };
        actor.store.shutdown().await.unwrap();
        let (store, state) = MqttStore::open_with_limits(directory.path(), limits)
            .await
            .unwrap();
        actor.store = store;
        actor.state = state;
        actor.limits = limits;
        let initial = actor
            .register("publisher".into(), "user".into(), false)
            .await
            .unwrap();
        actor
            .publish(
                "publisher",
                initial.generation,
                message("test/state", 2, false, b"old"),
                Some(10),
            )
            .await
            .unwrap();
        let excess = actor
            .publish(
                "publisher",
                initial.generation,
                message("test/state", 2, false, b"excess"),
                Some(11),
            )
            .await;
        assert!(
            matches!(excess, Err(RouterError::Store(StateError::Limit(_)))),
            "{excess:?}"
        );
        actor
            .unregister("publisher", initial.generation)
            .await
            .unwrap();
        let resumed = actor
            .register("publisher".into(), "user".into(), false)
            .await
            .unwrap();
        assert!(resumed.resumed);
        let before = actor.state.clone();
        assert!(matches!(
            actor
                .publish(
                    "publisher",
                    resumed.generation,
                    message("test/state", 2, false, b"new"),
                    Some(11),
                )
                .await,
            Err(RouterError::InboundQos2Quota)
        ));
        assert_eq!(actor.state, before);
        actor
            .publish(
                "publisher",
                resumed.generation,
                message("test/state", 2, false, b"duplicate"),
                Some(10),
            )
            .await
            .unwrap();
        assert_eq!(actor.state, before);
        actor
            .pubrel("publisher", resumed.generation, 10)
            .await
            .unwrap();
        actor
            .publish(
                "publisher",
                resumed.generation,
                message("test/state", 2, false, b"new"),
                Some(11),
            )
            .await
            .unwrap();
        assert_eq!(actor.state.sessions["publisher"].inbound_qos2.len(), 1);
        actor.store.shutdown().await.unwrap();
        let (store, recovered) = MqttStore::open_with_limits(directory.path(), limits)
            .await
            .unwrap();
        assert_eq!(
            recovered.sessions["publisher"].inbound_qos2[0].packet_id,
            11
        );
        store.shutdown().await.unwrap();
    }

    #[tokio::test]
    async fn mqtt5_retain_handling_uses_subscription_existence_and_deduplicates_topics() {
        let (_directory, mut actor) = actor().await;
        let publisher = actor
            .register("publisher".into(), "user".into(), true)
            .await
            .unwrap();
        actor
            .publish(
                "publisher",
                publisher.generation,
                message("test/state", 0, true, b"retained"),
                None,
            )
            .await
            .unwrap();
        let subscriber = actor
            .register("subscriber".into(), "user".into(), false)
            .await
            .unwrap();
        let (codes, retained) = actor
            .subscribe_with_handling(
                "subscriber",
                subscriber.generation,
                vec![(filter("test/#"), Some(0), 2, 0)],
            )
            .await
            .unwrap();
        assert_eq!(codes, [0]);
        assert!(retained.is_empty());
        let (_, retained) = actor
            .subscribe_with_handling(
                "subscriber",
                subscriber.generation,
                vec![(filter("test/#"), Some(0), 1, 0)],
            )
            .await
            .unwrap();
        assert!(retained.is_empty());
        actor
            .unsubscribe("subscriber", subscriber.generation, vec![filter("test/#")])
            .await
            .unwrap();
        let (_, retained) = actor
            .subscribe_with_handling(
                "subscriber",
                subscriber.generation,
                vec![(filter("test/#"), Some(0), 1, 0)],
            )
            .await
            .unwrap();
        assert_eq!(retained.len(), 1);
        let (_, retained) = actor
            .subscribe_with_handling(
                "subscriber",
                subscriber.generation,
                vec![
                    (filter("test/#"), Some(0), 0, 0),
                    (filter("test/state"), Some(0), 0, 0),
                ],
            )
            .await
            .unwrap();
        assert_eq!(retained.len(), 1);
        actor.store.shutdown().await.unwrap();
    }

    #[tokio::test]
    async fn mqtt5_no_local_and_retain_as_published_respect_overlapping_filters() {
        let (directory, mut actor) = actor().await;
        let mut same = actor
            .register("same".into(), "user".into(), false)
            .await
            .unwrap();
        actor
            .subscribe_with_handling(
                "same",
                same.generation,
                vec![(filter("test/#"), Some(1), 2, 0x04)],
            )
            .await
            .unwrap();
        actor
            .publish(
                "same",
                same.generation,
                message("test/state", 1, true, b"self-suppressed"),
                Some(7),
            )
            .await
            .unwrap();
        assert!(same.outbound.try_recv().is_err());

        let other = actor
            .register("other".into(), "user".into(), true)
            .await
            .unwrap();
        actor
            .publish(
                "other",
                other.generation,
                message("test/state", 0, true, b"other-cleared"),
                None,
            )
            .await
            .unwrap();
        assert!(
            matches!(same.outbound.try_recv(), Ok(Delivery::Publish { message, .. })
            if message.payload == b"other-cleared" && !message.retain)
        );

        actor
            .subscribe_with_handling(
                "same",
                same.generation,
                vec![(filter("test/state"), Some(1), 2, 0x08)],
            )
            .await
            .unwrap();
        actor
            .publish(
                "same",
                same.generation,
                message("test/state", 0, true, b"self-eligible"),
                None,
            )
            .await
            .unwrap();
        assert!(
            matches!(same.outbound.try_recv(), Ok(Delivery::Publish { message, .. })
            if message.payload == b"self-eligible" && message.retain)
        );
        assert!(same.outbound.try_recv().is_err());

        actor.store.shutdown().await.unwrap();
        let (store, recovered) = MqttStore::open(directory.path()).await.unwrap();
        assert_eq!(
            recovered.sessions["same"].subscription_options[&filter("test/#")],
            0x04
        );
        assert_eq!(
            recovered.sessions["same"].subscription_options[&filter("test/state")],
            0x08
        );
        store.shutdown().await.unwrap();
    }

    fn message(topic: &str, qos: u8, retain: bool, payload: &[u8]) -> StoredMessage {
        StoredMessage {
            topic: TopicName::try_from(topic.to_owned()).unwrap(),
            payload: payload.to_vec(),
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
            limits: StateLimits::default(),
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
            limits: StateLimits::default(),
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
    async fn mqtt5_clean_start_and_expiry_control_independent_session_state() {
        // MQTT-3.1.2.4 and MQTT-3.1.2.11.2: Clean Start chooses the initial
        // state; Session Expiry decides whether it survives disconnection.
        let (_directory, mut actor) = actor().await;
        let fresh = actor
            .register_with_policy("v5".into(), "user".into(), true, true, None, None)
            .await
            .unwrap();
        assert!(!fresh.resumed);
        actor
            .subscribe(
                "v5",
                fresh.generation,
                vec![(filter("test/state"), Some(1))],
            )
            .await
            .unwrap();
        actor.unregister("v5", fresh.generation).await.unwrap();
        assert!(actor.state.sessions["v5"].persistent);

        let resumed = actor
            .register_with_policy("v5".into(), "user".into(), false, true, None, None)
            .await
            .unwrap();
        assert!(resumed.resumed);
        assert_eq!(actor.state.sessions["v5"].subscriptions.len(), 1);
        actor.unregister("v5", resumed.generation).await.unwrap();

        let expiring = actor
            .register_with_policy("v5".into(), "user".into(), false, false, None, None)
            .await
            .unwrap();
        assert!(expiring.resumed);
        assert!(!actor.state.sessions["v5"].persistent);
        actor.unregister("v5", expiring.generation).await.unwrap();
        assert!(!actor.state.sessions.contains_key("v5"));

        let empty = actor
            .register_with_policy("v5".into(), "user".into(), false, true, None, None)
            .await
            .unwrap();
        assert!(!empty.resumed);
        actor.unregister("v5", empty.generation).await.unwrap();
        actor.store.shutdown().await.unwrap();
    }

    #[tokio::test]
    async fn mqtt5_finite_expiry_resumes_then_purges_after_deadline() {
        let (_directory, mut actor) = actor().await;
        let fresh = actor
            .register_with_policy("finite".into(), "user".into(), true, true, Some(1), None)
            .await
            .unwrap();
        actor
            .subscribe(
                "finite",
                fresh.generation,
                vec![(filter("test/state"), Some(1))],
            )
            .await
            .unwrap();
        actor.unregister("finite", fresh.generation).await.unwrap();
        assert!(actor.state.sessions["finite"].expires_at_unix_ms.is_some());
        let resumed = actor
            .register_with_policy("finite".into(), "user".into(), false, true, Some(1), None)
            .await
            .unwrap();
        assert!(resumed.resumed);
        assert!(actor.state.sessions["finite"].expires_at_unix_ms.is_none());
        actor
            .unregister("finite", resumed.generation)
            .await
            .unwrap();
        tokio::time::sleep(Duration::from_millis(1100)).await;
        actor.expire_sessions().await.unwrap();
        assert!(!actor.state.sessions.contains_key("finite"));
        let new_session = actor
            .register_with_policy("finite".into(), "user".into(), false, true, Some(1), None)
            .await
            .unwrap();
        assert!(!new_session.resumed);
        actor.store.shutdown().await.unwrap();
    }

    #[tokio::test]
    async fn mqtt5_disconnect_overrides_session_expiry_atomically() {
        let (_directory, mut actor) = actor().await;
        let zero = actor
            .register_with_policy("zero".into(), "user".into(), true, true, Some(10), None)
            .await
            .unwrap();
        actor
            .unregister_with_receipt("zero", zero.generation, true, Some(0), None)
            .await
            .unwrap();
        assert!(!actor.state.sessions.contains_key("zero"));

        let finite = actor
            .register_with_policy(
                "finite-override".into(),
                "user".into(),
                true,
                true,
                Some(10),
                None,
            )
            .await
            .unwrap();
        actor
            .unregister_with_receipt("finite-override", finite.generation, true, Some(1), None)
            .await
            .unwrap();
        assert_eq!(
            actor.state.sessions["finite-override"].expiry_interval_seconds,
            Some(1)
        );
        assert!(
            actor.state.sessions["finite-override"]
                .expires_at_unix_ms
                .is_some()
        );

        let forever = actor
            .register_with_policy("forever".into(), "user".into(), true, true, Some(10), None)
            .await
            .unwrap();
        actor
            .unregister_with_receipt("forever", forever.generation, true, Some(u32::MAX), None)
            .await
            .unwrap();
        assert!(actor.state.sessions["forever"].persistent);
        assert_eq!(
            actor.state.sessions["forever"].expiry_interval_seconds,
            None
        );
        assert_eq!(actor.state.sessions["forever"].expires_at_unix_ms, None);

        let ephemeral = actor
            .register_with_policy("ephemeral".into(), "user".into(), true, false, None, None)
            .await
            .unwrap();
        let previous = actor.state.clone();
        assert!(matches!(
            actor
                .unregister_with_receipt("ephemeral", ephemeral.generation, true, Some(1), None)
                .await,
            Err(RouterError::InvalidSessionExpiry)
        ));
        assert_eq!(actor.state, previous);
        actor.store.shutdown().await.unwrap();
    }

    #[tokio::test]
    async fn mqtt5_disconnect_expiry_commit_failure_preserves_previous_session() {
        use crate::persistence::faults::{Action, Fault, Point};
        let (directory, mut actor) = actor().await;
        let session = actor
            .register_with_policy(
                "finite-fault".into(),
                "user".into(),
                true,
                true,
                Some(10),
                None,
            )
            .await
            .unwrap();
        let before = actor.state.clone();
        actor
            .store
            .inject_for_test(Fault {
                point: Point::WalAppend,
                action: Action::ErrorAfter(6, 28),
            })
            .await
            .unwrap();
        assert!(
            actor
                .unregister_with_receipt("finite-fault", session.generation, true, Some(0), None)
                .await
                .is_err()
        );
        assert_eq!(actor.state, before);
        actor.store.shutdown().await.unwrap();
        let (store, recovered) = MqttStore::open(directory.path()).await.unwrap();
        assert_eq!(recovered, before);
        store.shutdown().await.unwrap();
    }

    #[tokio::test]
    async fn mqtt5_will_delay_wal_failure_preserves_will_for_recovery() {
        use crate::persistence::faults::{Action, Fault, Point};
        let (directory, mut actor) = actor().await;
        let source = actor
            .register_with_policy_and_delay(
                "will-fault".into(),
                "user".into(),
                SessionPolicy {
                    clean: true,
                    persistent: true,
                    expiry_interval_seconds: None,
                    will_delay_seconds: 10,
                    receive_maximum: u16::MAX,
                },
                Some(message("test/will", 0, false, b"survives")),
            )
            .await
            .unwrap();
        let before = actor.state.clone();
        actor
            .store
            .inject_for_test(Fault {
                point: Point::WalAppend,
                action: Action::ErrorAfter(6, 28),
            })
            .await
            .unwrap();
        assert!(
            actor
                .unregister_with_reason("will-fault", source.generation, false)
                .await
                .is_err()
        );
        assert!(actor.fatal);
        assert_eq!(actor.state, before);
        actor.store.shutdown().await.unwrap();
        let (store, recovered) = MqttStore::open(directory.path()).await.unwrap();
        assert_eq!(recovered, before);
        assert!(recovered.pending_wills.contains_key("will-fault"));
        store.shutdown().await.unwrap();
    }

    #[tokio::test]
    #[expect(
        clippy::too_many_lines,
        reason = "one actor fixture covers delayed publication, cancellation, clean start and session expiry"
    )]
    async fn mqtt5_will_delay_publishes_or_cancels_with_session_transition() {
        let (_directory, mut actor) = actor().await;
        let mut watcher = actor
            .register("watcher".into(), "user".into(), false)
            .await
            .unwrap();
        actor
            .subscribe(
                "watcher",
                watcher.generation,
                vec![(filter("test/will"), Some(0))],
            )
            .await
            .unwrap();
        let policy = |clean, expiry, delay| SessionPolicy {
            clean,
            persistent: expiry != 0,
            expiry_interval_seconds: (1..u32::MAX).contains(&expiry).then_some(expiry),
            will_delay_seconds: delay,
            receive_maximum: u16::MAX,
        };
        let source = actor
            .register_with_policy_and_delay(
                "delayed".into(),
                "user".into(),
                policy(true, u32::MAX, 1),
                Some(message("test/will", 0, false, b"delayed")),
            )
            .await
            .unwrap();
        actor
            .unregister_with_reason("delayed", source.generation, false)
            .await
            .unwrap();
        assert!(watcher.outbound.try_recv().is_err());
        assert!(
            actor.state.pending_wills["delayed"]
                .publish_at_unix_ms
                .is_some()
        );
        tokio::time::sleep(Duration::from_millis(1100)).await;
        actor.expire_sessions().await.unwrap();
        assert!(
            matches!(watcher.outbound.try_recv(), Ok(Delivery::Publish { message, .. }) if message.payload == b"delayed")
        );

        let source = actor
            .register_with_policy_and_delay(
                "cancelled".into(),
                "user".into(),
                policy(true, u32::MAX, 10),
                Some(message("test/will", 0, false, b"cancelled")),
            )
            .await
            .unwrap();
        actor
            .unregister_with_reason("cancelled", source.generation, false)
            .await
            .unwrap();
        let resumed = actor
            .register_with_policy_and_delay(
                "cancelled".into(),
                "user".into(),
                policy(false, u32::MAX, 0),
                None,
            )
            .await
            .unwrap();
        assert!(resumed.resumed);
        assert!(!actor.state.pending_wills.contains_key("cancelled"));
        assert!(watcher.outbound.try_recv().is_err());

        let source = actor
            .register_with_policy_and_delay(
                "clean".into(),
                "user".into(),
                policy(true, u32::MAX, 10),
                Some(message("test/will", 0, false, b"clean")),
            )
            .await
            .unwrap();
        actor
            .unregister_with_reason("clean", source.generation, false)
            .await
            .unwrap();
        let fresh = actor
            .register_with_policy_and_delay(
                "clean".into(),
                "user".into(),
                policy(true, u32::MAX, 0),
                None,
            )
            .await
            .unwrap();
        assert!(!fresh.resumed);
        assert!(
            matches!(watcher.outbound.try_recv(), Ok(Delivery::Publish { message, .. }) if message.payload == b"clean")
        );

        let source = actor
            .register_with_policy_and_delay(
                "short-session".into(),
                "user".into(),
                policy(true, 1, 10),
                Some(message("test/will", 0, false, b"session-end")),
            )
            .await
            .unwrap();
        actor
            .unregister_with_reason("short-session", source.generation, false)
            .await
            .unwrap();
        tokio::time::sleep(Duration::from_millis(1100)).await;
        actor.expire_sessions().await.unwrap();
        assert!(
            matches!(watcher.outbound.try_recv(), Ok(Delivery::Publish { message, .. }) if message.payload == b"session-end")
        );
        actor.store.shutdown().await.unwrap();
    }

    #[tokio::test]
    async fn mqtt5_message_expiry_purges_retained_and_offline_after_reopen() {
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
        actor
            .unregister("sub", subscriber.generation)
            .await
            .unwrap();
        let publisher = actor
            .register("pub".into(), "user".into(), true)
            .await
            .unwrap();
        let mut expiring = message("test/expiring", 1, true, b"short-lived");
        expiring.expiry_at_unix_ms = Some(message_expiry_deadline(1).unwrap());
        actor
            .publish("pub", publisher.generation, expiring, Some(7))
            .await
            .unwrap();
        assert!(actor.state.retained.contains_key("test/expiring"));
        assert_eq!(actor.state.sessions["sub"].offline.len(), 1);
        actor.store.shutdown().await.unwrap();
        tokio::time::sleep(Duration::from_millis(1100)).await;
        let (store, state) = MqttStore::open(directory.path()).await.unwrap();
        let mut reopened = Actor {
            limits: StateLimits::default(),
            metrics: Arc::default(),
            store,
            state,
            auth: Arc::clone(&actor.auth),
            live: BTreeMap::new(),
            next_generation: 1,
            fatal: false,
            commits_since_snapshot: 0,
        };
        reopened.expire_sessions().await.unwrap();
        assert!(!reopened.state.retained.contains_key("test/expiring"));
        assert!(reopened.state.sessions["sub"].offline.is_empty());
        let resumed = reopened
            .register("sub".into(), "user".into(), false)
            .await
            .unwrap();
        assert!(resumed.replay.is_empty());
        reopened.store.shutdown().await.unwrap();
    }

    #[tokio::test]
    async fn mqtt5_expired_immediate_publication_replaces_old_retained_without_delivery() {
        let (_directory, mut actor) = actor().await;
        let publisher = actor
            .register("pub".into(), "user".into(), true)
            .await
            .unwrap();
        let mut subscriber = actor
            .register("sub".into(), "user".into(), false)
            .await
            .unwrap();
        actor
            .subscribe(
                "sub",
                subscriber.generation,
                vec![(filter("test/state"), Some(1))],
            )
            .await
            .unwrap();
        actor
            .publish(
                "pub",
                publisher.generation,
                message("test/state", 1, true, b"old"),
                Some(1),
            )
            .await
            .unwrap();
        let _ = subscriber.outbound.try_recv();
        let mut expired = message("test/state", 1, true, b"new");
        expired.expiry_at_unix_ms = Some(unix_ms().unwrap());
        actor
            .publish("pub", publisher.generation, expired, Some(2))
            .await
            .unwrap();
        assert!(!actor.state.retained.contains_key("test/state"));
        assert!(subscriber.outbound.try_recv().is_err());
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
                StateLimits::default(),
                &mut candidate,
                &actor.live,
                &actor.auth,
                &message("$SYS/state", 0, false, b"denied"),
                None,
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
        assert_eq!(deleted.payload, Vec::<u8>::new());
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
                persistent: false,
                expiry_interval_seconds: None,
                will_delay_seconds: 0,
                receive_maximum: u16::MAX,
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
