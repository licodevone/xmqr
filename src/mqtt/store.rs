//! Versioned durable MQTT session and retained-message aggregate.
//!
//! The router actor is the sole owner of [`DurableState`]. It prepares a new
//! state, calls [`MqttStore::commit`], and only then publishes the new state or
//! sends an MQTT acknowledgment. No filesystem work is performed under an
//! asynchronous mutex. One aggregate under one WAL key makes a transition
//! involving a session, inflight packet and retained message atomic.

use std::{
    collections::{BTreeMap, HashSet, VecDeque},
    path::Path,
};

use serde::{Deserialize, Serialize};
use thiserror::Error;

use crate::persistence::{StorageError, actor::PersistenceHandle};

use super::topic::{TopicFilter, TopicName};

const KEY: &[u8] = b"mqtt311.state.v1";
const FORMAT_VERSION: u16 = 2;
const MAX_DOCUMENT_BYTES: usize = 1_000_000;
const MAX_SESSIONS: usize = 64;
const MAX_RETAINED: usize = 256;
const MAX_SUBSCRIPTIONS: usize = 256;
const MAX_OFFLINE: usize = 64;
const MAX_INFLIGHT: usize = 32;
const MAX_CLIENT_ID_BYTES: usize = 256;
const MAX_PRINCIPAL_BYTES: usize = 256;
const MAX_PAYLOAD_BYTES: usize = 4096;

#[derive(Debug, Error)]
pub(super) enum StateError {
    #[error("MQTT durable storage failed: {0}")]
    Storage(#[from] StorageError),
    #[error("MQTT durable document is malformed")]
    Malformed,
    #[error("MQTT durable document has unsupported version {0}")]
    UnsupportedVersion(u16),
    #[error("MQTT durable state exceeds limit: {0}")]
    Limit(&'static str),
    #[error("MQTT durable storage worker failed")]
    WorkerUnavailable,
}

/// One committed, versioned image. Mutate only from the router's single-owner
/// task, then commit the complete candidate before making it authoritative.
#[derive(Clone, Debug, Default, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub(super) struct DurableState {
    pub sessions: BTreeMap<String, DurableSession>,
    pub retained: BTreeMap<TopicName, StoredMessage>,
    // Wills belong to accepted connections, including clean sessions.
    #[serde(default)]
    pub pending_wills: BTreeMap<String, PendingWill>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub(super) struct PendingWill {
    pub principal: String,
    pub message: StoredMessage,
}

/// Session state retained across reconnects. `persistent = false` marks a
/// clean-session image that must be discarded after crash recovery.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub(super) struct DurableSession {
    pub principal: String,
    pub persistent: bool,
    pub subscriptions: BTreeMap<TopicFilter, u8>,
    pub offline: VecDeque<StoredMessage>,
    pub inbound_qos2: Vec<InboundQos2>,
    pub outbound: Vec<OutboundInflight>,
    pub next_packet_id: u16,
}

impl DurableSession {
    pub fn new(principal: String, persistent: bool) -> Self {
        Self {
            principal,
            persistent,
            subscriptions: BTreeMap::new(),
            offline: VecDeque::new(),
            inbound_qos2: Vec::new(),
            outbound: Vec::new(),
            next_packet_id: 1,
        }
    }
}

/// Payload bytes are hex encoded in the TOML envelope so the exact wire bytes
/// survive restart without an extra binary-format dependency.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub(super) struct StoredMessage {
    pub topic: TopicName,
    #[serde(with = "hex_bytes")]
    pub payload: Vec<u8>,
    pub qos: u8,
    pub retain: bool,
}

/// An inbound `QoS` 2 PUBLISH has been committed before PUBREC; PUBREL must
/// atomically route it and remove this record before PUBCOMP.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub(super) struct InboundQos2 {
    pub packet_id: u16,
    pub message: StoredMessage,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
#[allow(clippy::enum_variant_names)] // Names intentionally mirror the MQTT acknowledgment being awaited.
pub(super) enum OutboundStage {
    AwaitPubAck,
    AwaitPubRec,
    AwaitPubComp,
}

/// Every outbound inflight record is durable before transmission. After
/// reconnect the router retransmits according to `stage` with DUP set.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub(super) struct OutboundInflight {
    pub packet_id: u16,
    pub message: StoredMessage,
    pub stage: OutboundStage,
}

#[derive(Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Envelope {
    version: u16,
    state: DurableState,
}

/// Thin adapter over the bounded single-writer WAL actor. It intentionally
/// has no shared mutable state; callers serialize commits themselves.
pub(super) struct MqttStore {
    writer: PersistenceHandle,
}

impl MqttStore {
    /// Recover the last fsynced image. Disk recovery runs off Tokio workers.
    pub async fn open(path: impl AsRef<Path>) -> Result<(Self, DurableState), StateError> {
        let path = path.as_ref().to_path_buf();
        let writer = tokio::task::spawn_blocking(move || PersistenceHandle::start(path))
            .await
            .map_err(|_| StateError::WorkerUnavailable)??;
        let bytes = writer.get(KEY.to_vec()).await?;
        let state = if let Some(bytes) = bytes {
            if bytes.len() > MAX_DOCUMENT_BYTES {
                return Err(StateError::Limit("document bytes"));
            }
            let text = std::str::from_utf8(&bytes).map_err(|_| StateError::Malformed)?;
            let envelope: Envelope = toml::from_str(text).map_err(|_| StateError::Malformed)?;
            if !matches!(envelope.version, 1 | FORMAT_VERSION) {
                return Err(StateError::UnsupportedVersion(envelope.version));
            }
            validate(&envelope.state)?;
            envelope.state
        } else {
            DurableState::default()
        };
        Ok((Self { writer }, state))
    }

    /// Commit the whole candidate. Success is an fsync durability barrier.
    /// The caller must not expose the candidate or ACK `QoS` until this returns.
    pub async fn commit(&self, state: &DurableState) -> Result<(), StateError> {
        validate(state)?;
        let envelope = Envelope {
            version: FORMAT_VERSION,
            state: state.clone(),
        };
        let text = toml::to_string(&envelope).map_err(|_| StateError::Malformed)?;
        if text.len() > MAX_DOCUMENT_BYTES {
            return Err(StateError::Limit("document bytes"));
        }
        self.writer.put(KEY.to_vec(), text.into_bytes()).await?;
        Ok(())
    }

    /// Publish a WAL snapshot without changing logical MQTT state.
    pub async fn snapshot(&self) -> Result<(), StateError> {
        self.writer.snapshot().await?;
        Ok(())
    }

    /// Drain and stop the dedicated storage writer.
    #[cfg(test)]
    pub async fn shutdown(self) -> Result<(), StateError> {
        self.writer.shutdown().await?;
        Ok(())
    }
}

/// Validate quotas and semantic invariants before a WAL write or after
/// recovery. Document-byte quota is checked separately after serialization.
pub(super) fn validate(state: &DurableState) -> Result<(), StateError> {
    if state.sessions.len() > MAX_SESSIONS {
        return Err(StateError::Limit("sessions"));
    }
    if state.pending_wills.len() > MAX_SESSIONS {
        return Err(StateError::Limit("pending Wills"));
    }
    for (client_id, will) in &state.pending_wills {
        validate_message(&will.message)?;
        if state
            .sessions
            .get(client_id)
            .is_none_or(|s| s.principal != will.principal)
        {
            return Err(StateError::Malformed);
        }
    }
    if state.retained.len() > MAX_RETAINED {
        return Err(StateError::Limit("retained topics"));
    }
    for (client_id, session) in &state.sessions {
        if client_id.is_empty() || client_id.len() > MAX_CLIENT_ID_BYTES {
            return Err(StateError::Limit("client ID bytes"));
        }
        if session.principal.is_empty() || session.principal.len() > MAX_PRINCIPAL_BYTES {
            return Err(StateError::Limit("principal bytes"));
        }
        if session.next_packet_id == 0 {
            return Err(StateError::Malformed);
        }
        if session.subscriptions.len() > MAX_SUBSCRIPTIONS {
            return Err(StateError::Limit("subscriptions per session"));
        }
        for qos in session.subscriptions.values() {
            if *qos > 2 {
                return Err(StateError::Malformed);
            }
        }
        if session.offline.len() > MAX_OFFLINE {
            return Err(StateError::Limit("offline messages per session"));
        }
        for message in &session.offline {
            validate_message(message)?;
            if message.qos == 0 {
                return Err(StateError::Malformed);
            }
        }
        if session.inbound_qos2.len() > MAX_INFLIGHT || session.outbound.len() > MAX_INFLIGHT {
            return Err(StateError::Limit("inflight messages per session"));
        }
        let mut incoming_ids = HashSet::new();
        for entry in &session.inbound_qos2 {
            if entry.packet_id == 0 || !incoming_ids.insert(entry.packet_id) {
                return Err(StateError::Malformed);
            }
            validate_message(&entry.message)?;
            if entry.message.qos != 2 {
                return Err(StateError::Malformed);
            }
        }
        let mut outgoing_ids = HashSet::new();
        for entry in &session.outbound {
            if entry.packet_id == 0 || !outgoing_ids.insert(entry.packet_id) {
                return Err(StateError::Malformed);
            }
            validate_message(&entry.message)?;
            match (entry.message.qos, entry.stage) {
                (1, OutboundStage::AwaitPubAck)
                | (2, OutboundStage::AwaitPubRec | OutboundStage::AwaitPubComp) => {}
                _ => return Err(StateError::Malformed),
            }
        }
    }
    for (topic, message) in &state.retained {
        validate_message(message)?;
        if topic != &message.topic || message.payload.is_empty() || !message.retain {
            return Err(StateError::Malformed);
        }
    }
    Ok(())
}

fn validate_message(message: &StoredMessage) -> Result<(), StateError> {
    if message.payload.len() > MAX_PAYLOAD_BYTES {
        return Err(StateError::Limit("payload bytes"));
    }
    if message.qos > 2 {
        return Err(StateError::Malformed);
    }
    Ok(())
}

mod hex_bytes {
    use serde::{Deserialize, Deserializer, Serializer, de::Error as _};

    use super::MAX_PAYLOAD_BYTES;

    pub fn serialize<S: Serializer>(bytes: &[u8], serializer: S) -> Result<S::Ok, S::Error> {
        const HEX: &[u8; 16] = b"0123456789abcdef";
        let mut text = String::with_capacity(bytes.len() * 2);
        for &byte in bytes {
            text.push(char::from(HEX[usize::from(byte >> 4)]));
            text.push(char::from(HEX[usize::from(byte & 0x0f)]));
        }
        serializer.serialize_str(&text)
    }

    pub fn deserialize<'de, D: Deserializer<'de>>(deserializer: D) -> Result<Vec<u8>, D::Error> {
        let text = String::deserialize(deserializer)?;
        let bytes = text.as_bytes();
        if bytes.len() % 2 != 0 || bytes.len() > MAX_PAYLOAD_BYTES * 2 {
            return Err(D::Error::custom("invalid payload length"));
        }
        let mut output = Vec::with_capacity(bytes.len() / 2);
        let (pairs, remainder) = bytes.as_chunks::<2>();
        debug_assert_eq!(remainder, []);
        for pair in pairs {
            let high = nibble(pair[0]).ok_or_else(|| D::Error::custom("invalid payload hex"))?;
            let low = nibble(pair[1]).ok_or_else(|| D::Error::custom("invalid payload hex"))?;
            output.push((high << 4) | low);
        }
        Ok(output)
    }

    fn nibble(value: u8) -> Option<u8> {
        match value {
            b'0'..=b'9' => Some(value - b'0'),
            b'a'..=b'f' => Some(value - b'a' + 10),
            _ => None,
        }
    }
}

#[cfg(test)]
mod tests {
    use std::process::{Command, Stdio};

    use tempfile::tempdir;

    use super::*;
    use crate::persistence::Store;

    fn message(qos: u8) -> StoredMessage {
        StoredMessage {
            topic: TopicName::try_from("test/temperature".to_owned()).unwrap(),
            payload: vec![0, 255, 42],
            qos,
            retain: false,
        }
    }

    fn state() -> DurableState {
        let mut state = DurableState::default();
        state.sessions.insert(
            "sensor-1".into(),
            DurableSession {
                principal: "sensor".into(),
                persistent: true,
                subscriptions: BTreeMap::from([(
                    TopicFilter::try_from("test/temperature".to_owned()).unwrap(),
                    2,
                )]),
                offline: VecDeque::from([message(1)]),
                inbound_qos2: vec![InboundQos2 {
                    packet_id: 7,
                    message: message(2),
                }],
                outbound: vec![OutboundInflight {
                    packet_id: 8,
                    message: message(2),
                    stage: OutboundStage::AwaitPubComp,
                }],
                next_packet_id: 9,
            },
        );
        let mut retained = message(1);
        retained.retain = true;
        state.retained.insert(retained.topic.clone(), retained);
        state
    }

    #[tokio::test]
    async fn reopens_complete_committed_image_after_writer_shutdown() {
        let directory = tempdir().unwrap();
        let (store, initial) = MqttStore::open(directory.path()).await.unwrap();
        assert_eq!(initial, DurableState::default());
        let expected = state();
        store.commit(&expected).await.unwrap();
        store.snapshot().await.unwrap();
        store.shutdown().await.unwrap();
        let (reopened, recovered) = MqttStore::open(directory.path()).await.unwrap();
        assert_eq!(recovered, expected);
        reopened.shutdown().await.unwrap();
    }

    #[tokio::test]
    async fn rejects_invalid_transition_without_replacing_committed_state() {
        let directory = tempdir().unwrap();
        let (store, _) = MqttStore::open(directory.path()).await.unwrap();
        let expected = state();
        store.commit(&expected).await.unwrap();
        let mut invalid = expected.clone();
        invalid.sessions.get_mut("sensor-1").unwrap().outbound[0].packet_id = 0;
        assert!(matches!(
            store.commit(&invalid).await,
            Err(StateError::Malformed)
        ));
        store.shutdown().await.unwrap();
        let (reopened, recovered) = MqttStore::open(directory.path()).await.unwrap();
        assert_eq!(recovered, expected);
        reopened.shutdown().await.unwrap();
    }

    #[test]
    fn detects_duplicate_inflight_and_bounds_offline() {
        let mut state = state();
        let duplicate = state.sessions["sensor-1"].outbound[0].clone();
        state
            .sessions
            .get_mut("sensor-1")
            .unwrap()
            .outbound
            .push(duplicate);
        assert!(matches!(validate(&state), Err(StateError::Malformed)));
        let session = state.sessions.get_mut("sensor-1").unwrap();
        session.outbound.pop();
        session.offline.resize(MAX_OFFLINE + 1, message(1));
        assert!(matches!(
            validate(&state),
            Err(StateError::Limit("offline messages per session"))
        ));
    }

    #[tokio::test]
    async fn rejects_unsupported_document_version() {
        let directory = tempdir().unwrap();
        {
            let mut writer = Store::open(directory.path()).unwrap();
            let document = toml::to_string(&Envelope {
                version: FORMAT_VERSION + 1,
                state: state(),
            })
            .unwrap();
            writer.put(KEY, document.as_bytes()).unwrap();
        }
        assert!(matches!(
            MqttStore::open(directory.path()).await,
            Err(StateError::UnsupportedVersion(3))
        ));
    }

    #[test]
    fn crash_probe() {
        let Ok(_stage) = std::env::var("MQTT_AGGREGATE_CRASH_STAGE") else {
            return;
        };
        let path = std::env::var("MQTT_AGGREGATE_CRASH_DIRECTORY").unwrap();
        let mut writer = Store::open(path).unwrap();
        let next = state();
        let encoded = toml::to_string(&Envelope {
            version: FORMAT_VERSION,
            state: next,
        })
        .unwrap();
        writer.put(KEY, encoded.as_bytes()).unwrap();
        panic!("configured WAL crash point did not fire");
    }

    #[test]
    fn crash_recovery_never_exposes_partial_mqtt_transition() {
        for stage in ["after_wal_append_before_fsync", "after_wal_fsync"] {
            let directory = tempdir().unwrap();
            let baseline = DurableState::default();
            {
                let mut writer = Store::open(directory.path()).unwrap();
                let encoded = toml::to_string(&Envelope {
                    version: FORMAT_VERSION,
                    state: baseline.clone(),
                })
                .unwrap();
                writer.put(KEY, encoded.as_bytes()).unwrap();
            }
            let status = Command::new(std::env::current_exe().unwrap())
                .arg("--exact")
                .arg("mqtt::store::tests::crash_probe")
                .arg("--nocapture")
                .env("MQTT_AGGREGATE_CRASH_STAGE", stage)
                .env("MQTT_AGGREGATE_CRASH_DIRECTORY", directory.path())
                .env("MQTT_STORAGE_CRASH_STAGE", stage)
                .stdout(Stdio::null())
                .stderr(Stdio::null())
                .status()
                .unwrap();
            assert_eq!(status.code(), Some(71));
            let recovered = Store::open(directory.path()).unwrap();
            let text = std::str::from_utf8(recovered.get(KEY).unwrap()).unwrap();
            let envelope: Envelope = toml::from_str(text).unwrap();
            validate(&envelope.state).unwrap();
            if stage == "after_wal_fsync" {
                assert_eq!(envelope.state, state());
            } else {
                assert!(envelope.state == baseline || envelope.state == state());
            }
        }
    }

    #[tokio::test]
    async fn reads_v1_and_commits_v2_without_losing_retained() {
        let directory = tempdir().unwrap();
        let expected = state();
        {
            let mut writer = Store::open(directory.path()).unwrap();
            let document = toml::to_string(&Envelope {
                version: 1,
                state: expected.clone(),
            })
            .unwrap()
            .replace("[state.pending_wills]\n", "");
            writer.put(KEY, document.as_bytes()).unwrap();
        }
        let (store, recovered) = MqttStore::open(directory.path()).await.unwrap();
        assert_eq!(recovered, expected);
        store.commit(&recovered).await.unwrap();
        store.shutdown().await.unwrap();
        let writer = Store::open(directory.path()).unwrap();
        let bytes = writer.get(KEY).unwrap();
        let envelope: Envelope = toml::from_str(std::str::from_utf8(bytes).unwrap()).unwrap();
        assert_eq!(envelope.version, 2);
        assert_eq!(envelope.state, expected);
    }
}
