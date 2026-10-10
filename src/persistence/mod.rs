//! Durable single-writer key/value foundation for MQTT sessions and retained state.
//!
//! This module is synchronous by design. Use [`actor::PersistenceHandle`] from
//! Tokio tasks so filesystem calls never block a runtime worker.

pub mod actor;
pub mod backup;

use std::{
    collections::BTreeMap,
    fs::{self, File, OpenOptions},
    io::{self, Read, Seek, SeekFrom, Write},
    path::{Path, PathBuf},
};

use fs2::FileExt;
use thiserror::Error;

const WAL_NAME: &str = "state.wal";
const SNAPSHOT_NAME: &str = "state.snapshot";
const SNAPSHOT_TEMP_NAME: &str = "state.snapshot.tmp";
const LOCK_NAME: &str = "state.lock";
const WAL_HEADER: &[u8; 10] = b"MQWAL001\x00\x01";
const SNAPSHOT_MAGIC: &[u8; 8] = b"MQSNAP01";
const SNAPSHOT_VERSION: u16 = 1;
const SNAPSHOT_HEADER_LEN: usize = 8 + 2 + 8 + 4;
const RECORD_FIXED_LEN: usize = 8 + 1 + 2 + 4 + 4;
const MAX_KEY_BYTES: usize = 1_024;
const MAX_VALUE_BYTES: usize = 1_048_576;
const MAX_STATE_BYTES: usize = 64 * 1024 * 1024;
const MAX_ENTRIES: usize = 100_000;
const MAX_SNAPSHOT_BYTES: u64 = 80 * 1024 * 1024;
const MAX_RECORD_BYTES: usize = RECORD_FIXED_LEN + MAX_KEY_BYTES + MAX_VALUE_BYTES;

type DecodedRecord<'a> = (u64, u8, &'a [u8], &'a [u8]);
type SnapshotState = (BTreeMap<Vec<u8>, Vec<u8>>, u64);

#[derive(Debug, Error)]
pub enum StorageError {
    #[error("storage I/O failed: {0}")]
    Io(#[from] io::Error),
    #[error("storage directory must already exist")]
    MissingDirectory,
    #[error("another writer already owns this storage directory")]
    AlreadyOpen,
    #[error("invalid or corrupt {component}: {reason}")]
    Corrupt {
        component: &'static str,
        reason: &'static str,
    },
    #[error("unsupported {component} format version {version}")]
    UnsupportedVersion {
        component: &'static str,
        version: u16,
    },
    #[error("storage quota exceeded: {0}")]
    Limit(&'static str),
    #[error("storage state is uncertain after a failed write; close and recover")]
    Poisoned,
    #[error("sequence number overflow")]
    SequenceOverflow,
}

/// A single writer. Mutation takes `&mut self`; a cross-process file lock
/// prevents another broker instance from opening the same directory.
pub struct Store {
    directory: PathBuf,
    _lock: File,
    wal: File,
    state: BTreeMap<Vec<u8>, Vec<u8>>,
    state_bytes: usize,
    sequence: u64,
    poisoned: bool,
}

impl Store {
    /// Recover the last durable snapshot and replay the WAL.
    ///
    /// An incomplete final WAL record is discarded. A complete record with an
    /// invalid checksum, a sequence gap, or an unknown version fails closed.
    ///
    /// # Errors
    ///
    /// Returns an error for a missing directory, an active writer, I/O failure,
    /// quota violation, or corrupt/unsupported durable state.
    pub fn open(directory: impl AsRef<Path>) -> Result<Self, StorageError> {
        let directory = directory.as_ref().to_path_buf();
        if !directory.is_dir() {
            return Err(StorageError::MissingDirectory);
        }

        let lock_path = directory.join(LOCK_NAME);
        let lock = OpenOptions::new()
            .read(true)
            .write(true)
            .create(true)
            .truncate(false)
            .open(lock_path)?;
        lock.try_lock_exclusive().map_err(|error| {
            if error.kind() == io::ErrorKind::WouldBlock {
                StorageError::AlreadyOpen
            } else {
                StorageError::Io(error)
            }
        })?;

        // This file is never promoted to durable state. It is safe to remove
        // only after acquiring the exclusive lock.
        let temporary_snapshot = directory.join(SNAPSHOT_TEMP_NAME);
        match fs::remove_file(&temporary_snapshot) {
            Ok(()) => sync_directory(&directory)?,
            Err(error) if error.kind() == io::ErrorKind::NotFound => {}
            Err(error) => return Err(error.into()),
        }

        let snapshot_path = directory.join(SNAPSHOT_NAME);
        let snapshot_exists = snapshot_path.exists();
        let (mut state, snapshot_sequence) = read_snapshot(&snapshot_path)?;
        let mut state_bytes = calculate_state_bytes(&state)?;

        let wal_path = directory.join(WAL_NAME);
        let wal_exists = wal_path.exists();
        if snapshot_exists && !wal_exists {
            return Err(corrupt("WAL", "missing after a committed snapshot"));
        }
        let mut wal = OpenOptions::new()
            .read(true)
            .write(true)
            .create(true)
            .truncate(false)
            .open(&wal_path)?;

        let wal_length = wal.metadata()?.len();
        if !wal_exists
            || wal_length == 0
            || (snapshot_exists && wal_length < WAL_HEADER.len() as u64)
        {
            // Compaction may be interrupted after truncation. The published
            // snapshot has already been directory-synced at that point. An
            // empty WAL may also come from a crash during first initialization,
            // before any write could have been acknowledged.
            wal.set_len(0)?;
            wal.write_all(WAL_HEADER)?;
            wal.sync_all()?;
            sync_directory(&directory)?;
        }

        let sequence = replay_wal(&mut wal, snapshot_sequence, &mut state, &mut state_bytes)?;
        wal.seek(SeekFrom::End(0))?;

        Ok(Self {
            directory,
            _lock: lock,
            wal,
            state,
            state_bytes,
            sequence,
            poisoned: false,
        })
    }

    #[must_use]
    pub const fn sequence(&self) -> u64 {
        self.sequence
    }

    #[must_use]
    pub fn get(&self, key: &[u8]) -> Option<&[u8]> {
        self.state.get(key).map(Vec::as_slice)
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.state.len()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.state.is_empty()
    }

    /// Persist one upsert before making it visible in memory.
    ///
    /// # Errors
    ///
    /// Returns a quota, I/O, or poisoned-state error. An I/O error after the
    /// append starts has an uncertain outcome; reopen the store before retrying.
    pub fn put(&mut self, key: &[u8], value: &[u8]) -> Result<u64, StorageError> {
        self.ensure_writable()?;
        validate_key_value(key, value)?;
        let previous_size = self.state.get(key).map_or(0, |old| key.len() + old.len());
        let next_bytes = self
            .state_bytes
            .checked_sub(previous_size)
            .and_then(|bytes| bytes.checked_add(key.len() + value.len()))
            .ok_or(StorageError::Limit("state bytes"))?;
        if next_bytes > MAX_STATE_BYTES {
            return Err(StorageError::Limit("state bytes"));
        }
        if !self.state.contains_key(key) && self.state.len() >= MAX_ENTRIES {
            return Err(StorageError::Limit("entry count"));
        }

        let sequence = self.append_and_sync(1, key, value)?;
        self.state.insert(key.to_vec(), value.to_vec());
        self.state_bytes = next_bytes;
        Ok(sequence)
    }

    /// Persist a deletion. Deleting an absent key is recorded for sequencing.
    ///
    /// # Errors
    ///
    /// Returns an I/O, limit, or poisoned-state error.
    pub fn delete(&mut self, key: &[u8]) -> Result<u64, StorageError> {
        self.ensure_writable()?;
        validate_key_value(key, &[])?;
        let sequence = self.append_and_sync(2, key, &[])?;
        if let Some(previous) = self.state.remove(key) {
            self.state_bytes -= key.len() + previous.len();
        }
        Ok(sequence)
    }

    /// Create a versioned snapshot and compact the WAL.
    ///
    /// The temporary file is fully synced before rename. The containing
    /// directory is synced before any WAL bytes are removed.
    ///
    /// # Errors
    ///
    /// Returns an I/O error and poisons this instance if snapshot publication
    /// or WAL compaction fails. Recovery on a new instance remains possible.
    pub fn snapshot(&mut self) -> Result<u64, StorageError> {
        self.ensure_writable()?;
        self.poisoned = true;
        let result = self.write_snapshot_and_compact();
        if result.is_ok() {
            self.poisoned = false;
        }
        result.map(|()| self.sequence)
    }

    fn ensure_writable(&self) -> Result<(), StorageError> {
        if self.poisoned {
            Err(StorageError::Poisoned)
        } else {
            Ok(())
        }
    }

    fn append_and_sync(
        &mut self,
        operation: u8,
        key: &[u8],
        value: &[u8],
    ) -> Result<u64, StorageError> {
        let sequence = self
            .sequence
            .checked_add(1)
            .ok_or(StorageError::SequenceOverflow)?;
        let record = encode_record(sequence, operation, key, value)?;
        self.poisoned = true;
        self.wal.write_all(&record)?;
        crash_at("after_wal_append_before_fsync");
        self.wal.sync_data()?;
        crash_at("after_wal_fsync");
        self.sequence = sequence;
        self.poisoned = false;
        Ok(sequence)
    }

    fn write_snapshot_and_compact(&mut self) -> Result<(), StorageError> {
        let temporary_path = self.directory.join(SNAPSHOT_TEMP_NAME);
        let final_path = self.directory.join(SNAPSHOT_NAME);
        let snapshot = encode_snapshot(&self.state, self.sequence)?;
        let mut temporary_file = OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&temporary_path)?;
        temporary_file.write_all(&snapshot)?;
        temporary_file.sync_all()?;
        crash_at("after_snapshot_temp_fsync");
        drop(temporary_file);
        fs::rename(&temporary_path, &final_path)?;
        crash_at("after_snapshot_rename");
        sync_directory(&self.directory)?;
        crash_at("after_snapshot_dir_fsync");

        self.wal.set_len(WAL_HEADER.len() as u64)?;
        crash_at("after_wal_truncate");
        self.wal.seek(SeekFrom::Start(0))?;
        self.wal.write_all(WAL_HEADER)?;
        self.wal.sync_all()?;
        self.wal.seek(SeekFrom::End(0))?;
        Ok(())
    }
}

fn validate_key_value(key: &[u8], value: &[u8]) -> Result<(), StorageError> {
    if key.is_empty() || key.len() > MAX_KEY_BYTES {
        return Err(StorageError::Limit("key must contain 1..=1024 bytes"));
    }
    if value.len() > MAX_VALUE_BYTES {
        return Err(StorageError::Limit("value exceeds 1 MiB"));
    }
    Ok(())
}

fn encode_record(
    sequence: u64,
    operation: u8,
    key: &[u8],
    value: &[u8],
) -> Result<Vec<u8>, StorageError> {
    let key_len = u16::try_from(key.len()).map_err(|_| StorageError::Limit("key length"))?;
    let value_len = u32::try_from(value.len()).map_err(|_| StorageError::Limit("value length"))?;
    let body_len = RECORD_FIXED_LEN + key.len() + value.len();
    let mut output = Vec::with_capacity(4 + body_len);
    output.extend_from_slice(
        &u32::try_from(body_len)
            .map_err(|_| StorageError::Limit("record length"))?
            .to_le_bytes(),
    );
    output.extend_from_slice(&sequence.to_le_bytes());
    output.push(operation);
    output.extend_from_slice(&key_len.to_le_bytes());
    output.extend_from_slice(&value_len.to_le_bytes());
    output.extend_from_slice(key);
    output.extend_from_slice(value);
    let checksum = crc32fast::hash(&output[4..]);
    output.extend_from_slice(&checksum.to_le_bytes());
    Ok(output)
}

fn replay_wal(
    wal: &mut File,
    snapshot_sequence: u64,
    state: &mut BTreeMap<Vec<u8>, Vec<u8>>,
    state_bytes: &mut usize,
) -> Result<u64, StorageError> {
    wal.seek(SeekFrom::Start(0))?;
    let mut header = [0_u8; WAL_HEADER.len()];
    wal.read_exact(&mut header).map_err(|error| {
        if error.kind() == io::ErrorKind::UnexpectedEof {
            corrupt("WAL", "missing header")
        } else {
            StorageError::Io(error)
        }
    })?;
    if &header != WAL_HEADER {
        return Err(corrupt("WAL", "unknown magic or version"));
    }

    let mut last_seen = None;
    let mut durable_sequence = snapshot_sequence;
    loop {
        let record_start = wal.stream_position()?;
        let mut length_bytes = [0_u8; 4];
        match wal.read(&mut length_bytes) {
            Ok(0) => break,
            Ok(4) => {}
            Ok(read) => {
                if wal.read_exact(&mut length_bytes[read..]).is_err() {
                    truncate_torn_tail(wal, record_start)?;
                    break;
                }
            }
            Err(error) => return Err(error.into()),
        }
        let length = u32::from_le_bytes(length_bytes) as usize;
        if !(RECORD_FIXED_LEN..=MAX_RECORD_BYTES).contains(&length) {
            return Err(corrupt("WAL", "invalid record length"));
        }
        let mut frame = vec![0_u8; length];
        if let Err(error) = wal.read_exact(&mut frame) {
            if error.kind() == io::ErrorKind::UnexpectedEof {
                truncate_torn_tail(wal, record_start)?;
                break;
            }
            return Err(error.into());
        }
        let (sequence, operation, key, value) = decode_record(&frame)?;
        if last_seen.is_some_and(|previous: u64| previous.checked_add(1) != Some(sequence)) {
            return Err(corrupt("WAL", "sequence gap or duplicate"));
        }
        last_seen = Some(sequence);

        if sequence > snapshot_sequence {
            if sequence
                != durable_sequence
                    .checked_add(1)
                    .ok_or(StorageError::SequenceOverflow)?
            {
                return Err(corrupt("WAL", "sequence after snapshot is not contiguous"));
            }
            apply_record(state, state_bytes, operation, key, value)?;
            durable_sequence = sequence;
        }
    }
    Ok(durable_sequence)
}

#[cfg(test)]
fn crash_at(stage: &str) {
    if std::env::var("MQTT_STORAGE_CRASH_STAGE").is_ok_and(|configured| configured == stage) {
        std::process::exit(71);
    }
}

#[cfg(not(test))]
fn crash_at(_stage: &str) {}

fn decode_record(frame: &[u8]) -> Result<DecodedRecord<'_>, StorageError> {
    if frame.len() < RECORD_FIXED_LEN {
        return Err(corrupt("WAL", "record too short"));
    }
    let split = frame.len() - 4;
    let expected = u32::from_le_bytes(frame[split..].try_into().expect("four-byte checksum"));
    if crc32fast::hash(&frame[..split]) != expected {
        return Err(corrupt("WAL", "checksum mismatch"));
    }
    let sequence = u64::from_le_bytes(frame[0..8].try_into().expect("eight-byte sequence"));
    let operation = frame[8];
    let key_len = usize::from(u16::from_le_bytes(
        frame[9..11].try_into().expect("key length"),
    ));
    let value_len = u32::from_le_bytes(frame[11..15].try_into().expect("value length")) as usize;
    if key_len == 0
        || key_len > MAX_KEY_BYTES
        || value_len > MAX_VALUE_BYTES
        || 15 + key_len + value_len + 4 != frame.len()
        || !matches!(operation, 1 | 2)
        || (operation == 2 && value_len != 0)
    {
        return Err(corrupt("WAL", "invalid record contents"));
    }
    Ok((
        sequence,
        operation,
        &frame[15..15 + key_len],
        &frame[15 + key_len..split],
    ))
}

fn apply_record(
    state: &mut BTreeMap<Vec<u8>, Vec<u8>>,
    state_bytes: &mut usize,
    operation: u8,
    key: &[u8],
    value: &[u8],
) -> Result<(), StorageError> {
    match operation {
        1 => {
            let previous = state.get(key).map_or(0, |old| key.len() + old.len());
            let next = state_bytes
                .checked_sub(previous)
                .and_then(|size| size.checked_add(key.len() + value.len()))
                .ok_or(StorageError::Limit("state bytes"))?;
            if next > MAX_STATE_BYTES || (!state.contains_key(key) && state.len() >= MAX_ENTRIES) {
                return Err(StorageError::Limit("recovered state quota"));
            }
            state.insert(key.to_vec(), value.to_vec());
            *state_bytes = next;
        }
        2 => {
            if let Some(old) = state.remove(key) {
                *state_bytes -= key.len() + old.len();
            }
        }
        _ => return Err(corrupt("WAL", "unknown operation")),
    }
    Ok(())
}

fn truncate_torn_tail(wal: &mut File, valid_bytes: u64) -> Result<(), StorageError> {
    wal.set_len(valid_bytes)?;
    wal.sync_all()?;
    wal.seek(SeekFrom::Start(valid_bytes))?;
    Ok(())
}

fn encode_snapshot(
    state: &BTreeMap<Vec<u8>, Vec<u8>>,
    sequence: u64,
) -> Result<Vec<u8>, StorageError> {
    let mut output = Vec::with_capacity(SNAPSHOT_HEADER_LEN + state.len() * 6 + 4);
    output.extend_from_slice(SNAPSHOT_MAGIC);
    output.extend_from_slice(&SNAPSHOT_VERSION.to_le_bytes());
    output.extend_from_slice(&sequence.to_le_bytes());
    output.extend_from_slice(
        &u32::try_from(state.len())
            .map_err(|_| StorageError::Limit("snapshot entries"))?
            .to_le_bytes(),
    );
    for (key, value) in state {
        output.extend_from_slice(
            &u16::try_from(key.len())
                .map_err(|_| StorageError::Limit("snapshot key"))?
                .to_le_bytes(),
        );
        output.extend_from_slice(
            &u32::try_from(value.len())
                .map_err(|_| StorageError::Limit("snapshot value"))?
                .to_le_bytes(),
        );
        output.extend_from_slice(key);
        output.extend_from_slice(value);
    }
    if output.len() as u64 + 4 > MAX_SNAPSHOT_BYTES {
        return Err(StorageError::Limit("snapshot bytes"));
    }
    let checksum = crc32fast::hash(&output);
    output.extend_from_slice(&checksum.to_le_bytes());
    Ok(output)
}

fn read_snapshot(path: &Path) -> Result<SnapshotState, StorageError> {
    let mut file = match File::open(path) {
        Ok(file) => file,
        Err(error) if error.kind() == io::ErrorKind::NotFound => return Ok((BTreeMap::new(), 0)),
        Err(error) => return Err(error.into()),
    };
    if file.metadata()?.len() > MAX_SNAPSHOT_BYTES {
        return Err(StorageError::Limit("snapshot bytes"));
    }
    let mut bytes = Vec::new();
    file.read_to_end(&mut bytes)?;
    if bytes.len() < SNAPSHOT_HEADER_LEN + 4 || &bytes[0..8] != SNAPSHOT_MAGIC {
        return Err(corrupt("snapshot", "missing or invalid header"));
    }
    let version = u16::from_le_bytes(bytes[8..10].try_into().expect("version"));
    if version != SNAPSHOT_VERSION {
        return Err(StorageError::UnsupportedVersion {
            component: "snapshot",
            version,
        });
    }
    let checksum_start = bytes.len() - 4;
    let checksum = u32::from_le_bytes(bytes[checksum_start..].try_into().expect("checksum"));
    if crc32fast::hash(&bytes[..checksum_start]) != checksum {
        return Err(corrupt("snapshot", "checksum mismatch"));
    }
    let sequence = u64::from_le_bytes(bytes[10..18].try_into().expect("sequence"));
    let entry_count = u32::from_le_bytes(bytes[18..22].try_into().expect("entry count")) as usize;
    if entry_count > MAX_ENTRIES {
        return Err(StorageError::Limit("snapshot entries"));
    }
    let mut cursor = SNAPSHOT_HEADER_LEN;
    let mut state = BTreeMap::new();
    for _ in 0..entry_count {
        if cursor + 6 > checksum_start {
            return Err(corrupt("snapshot", "truncated entry header"));
        }
        let key_len = usize::from(u16::from_le_bytes(
            bytes[cursor..cursor + 2].try_into().expect("key length"),
        ));
        let value_len = u32::from_le_bytes(
            bytes[cursor + 2..cursor + 6]
                .try_into()
                .expect("value length"),
        ) as usize;
        cursor += 6;
        if key_len == 0
            || key_len > MAX_KEY_BYTES
            || value_len > MAX_VALUE_BYTES
            || key_len
                .checked_add(value_len)
                .and_then(|size| cursor.checked_add(size))
                .is_none_or(|end| end > checksum_start)
        {
            return Err(corrupt("snapshot", "invalid entry length"));
        }
        let key = bytes[cursor..cursor + key_len].to_vec();
        cursor += key_len;
        let value = bytes[cursor..cursor + value_len].to_vec();
        cursor += value_len;
        if state.insert(key, value).is_some() {
            return Err(corrupt("snapshot", "duplicate key"));
        }
    }
    if cursor != checksum_start {
        return Err(corrupt("snapshot", "trailing bytes"));
    }
    Ok((state, sequence))
}

fn calculate_state_bytes(state: &BTreeMap<Vec<u8>, Vec<u8>>) -> Result<usize, StorageError> {
    state.iter().try_fold(0_usize, |total, (key, value)| {
        total
            .checked_add(key.len() + value.len())
            .filter(|bytes| *bytes <= MAX_STATE_BYTES)
            .ok_or(StorageError::Limit("state bytes"))
    })
}

fn corrupt(component: &'static str, reason: &'static str) -> StorageError {
    StorageError::Corrupt { component, reason }
}

#[cfg(unix)]
fn sync_directory(directory: &Path) -> io::Result<()> {
    File::open(directory)?.sync_all()
}

#[cfg(not(unix))]
fn sync_directory(_directory: &Path) -> io::Result<()> {
    Err(io::Error::new(
        io::ErrorKind::Unsupported,
        "durable directory fsync is supported on Unix targets only",
    ))
}

#[cfg(all(test, unix))]
mod tests {
    use std::{
        fs::{File, OpenOptions},
        io::{Read, Seek, SeekFrom, Write},
        process::{Command, Stdio},
    };

    use tempfile::tempdir;

    use super::{
        SNAPSHOT_NAME, StorageError, Store, WAL_HEADER, WAL_NAME, actor::PersistenceHandle,
    };

    #[test]
    fn recovers_committed_writes_and_compacted_snapshot() {
        let directory = tempdir().expect("tempdir");
        {
            let mut store = Store::open(directory.path()).expect("open");
            assert_eq!(store.put(b"session/a", b"first").expect("put"), 1);
            assert_eq!(store.put(b"session/a", b"second").expect("replace"), 2);
            assert_eq!(store.put(b"retained/x", b"payload").expect("put"), 3);
            assert_eq!(store.snapshot().expect("snapshot"), 3);
            assert_eq!(store.delete(b"retained/x").expect("delete"), 4);
        }
        let store = Store::open(directory.path()).expect("reopen");
        assert_eq!(store.sequence(), 4);
        assert_eq!(store.get(b"session/a"), Some(b"second".as_slice()));
        assert_eq!(store.get(b"retained/x"), None);
        assert_eq!(store.len(), 1);
    }

    #[test]
    fn refuses_second_writer() {
        let directory = tempdir().expect("tempdir");
        let _first = Store::open(directory.path()).expect("first writer");
        assert!(matches!(
            Store::open(directory.path()),
            Err(StorageError::AlreadyOpen)
        ));
    }

    #[test]
    fn discards_only_incomplete_wal_tail() {
        let directory = tempdir().expect("tempdir");
        {
            let mut store = Store::open(directory.path()).expect("open");
            store.put(b"committed", b"value").expect("commit");
        }
        let wal_path = directory.path().join(WAL_NAME);
        let valid_len = wal_path.metadata().expect("metadata").len();
        let mut wal = OpenOptions::new()
            .append(true)
            .open(&wal_path)
            .expect("append");
        wal.write_all(&[0x20, 0, 0, 0, 0, 0]).expect("torn record");
        wal.sync_all().expect("sync torn record");
        drop(wal);

        let store = Store::open(directory.path()).expect("recover torn tail");
        assert_eq!(store.get(b"committed"), Some(b"value".as_slice()));
        assert_eq!(wal_path.metadata().expect("metadata").len(), valid_len);
    }

    #[test]
    fn refuses_bad_checksum_in_complete_wal_record() {
        let directory = tempdir().expect("tempdir");
        {
            let mut store = Store::open(directory.path()).expect("open");
            store.put(b"key", b"value").expect("commit");
        }
        let wal_path = directory.path().join(WAL_NAME);
        let mut wal = OpenOptions::new()
            .read(true)
            .write(true)
            .open(wal_path)
            .expect("open WAL");
        wal.seek(SeekFrom::Start(
            (WAL_HEADER.len() + 4 + 8 + 1 + 2 + 4 + 3) as u64,
        ))
        .expect("seek value");
        wal.write_all(b"X").expect("corrupt value");
        wal.sync_all().expect("sync corruption");
        drop(wal);
        assert!(matches!(
            Store::open(directory.path()),
            Err(StorageError::Corrupt {
                component: "WAL",
                reason: "checksum mismatch"
            })
        ));
    }

    #[test]
    fn refuses_bad_snapshot_and_unknown_version() {
        let directory = tempdir().expect("tempdir");
        {
            let mut store = Store::open(directory.path()).expect("open");
            store.put(b"key", b"value").expect("commit");
            store.snapshot().expect("snapshot");
        }
        let snapshot_path = directory.path().join(SNAPSHOT_NAME);
        let mut snapshot = OpenOptions::new()
            .read(true)
            .write(true)
            .open(&snapshot_path)
            .expect("open snapshot");
        snapshot.seek(SeekFrom::Start(8)).expect("seek version");
        snapshot
            .write_all(&2_u16.to_le_bytes())
            .expect("change version");
        snapshot.sync_all().expect("sync version");
        drop(snapshot);
        assert!(matches!(
            Store::open(directory.path()),
            Err(StorageError::UnsupportedVersion {
                component: "snapshot",
                version: 2
            })
        ));

        let mut snapshot = OpenOptions::new()
            .read(true)
            .write(true)
            .open(&snapshot_path)
            .expect("reopen snapshot");
        snapshot.seek(SeekFrom::Start(8)).expect("seek version");
        snapshot
            .write_all(&1_u16.to_le_bytes())
            .expect("restore version");
        snapshot.seek(SeekFrom::End(-5)).expect("seek value");
        let mut byte = [0_u8; 1];
        snapshot.read_exact(&mut byte).expect("read value");
        snapshot.seek(SeekFrom::Current(-1)).expect("rewind");
        snapshot.write_all(&[byte[0] ^ 0xff]).expect("corrupt byte");
        snapshot.sync_all().expect("sync corruption");
        drop(snapshot);
        assert!(matches!(
            Store::open(directory.path()),
            Err(StorageError::Corrupt {
                component: "snapshot",
                reason: "checksum mismatch"
            })
        ));
    }

    #[test]
    fn recovers_snapshot_if_wal_header_was_torn_during_compaction() {
        let directory = tempdir().expect("tempdir");
        {
            let mut store = Store::open(directory.path()).expect("open");
            store.put(b"key", b"durable").expect("commit");
            store.snapshot().expect("snapshot");
        }
        let wal = OpenOptions::new()
            .write(true)
            .open(directory.path().join(WAL_NAME))
            .expect("open WAL");
        wal.set_len(4).expect("simulate torn header");
        wal.sync_all().expect("sync torn header");
        drop(wal);

        let store = Store::open(directory.path()).expect("recover snapshot");
        assert_eq!(store.sequence(), 1);
        assert_eq!(store.get(b"key"), Some(b"durable".as_slice()));
    }

    #[test]
    fn refuses_missing_wal_after_snapshot() {
        let directory = tempdir().expect("tempdir");
        {
            let mut store = Store::open(directory.path()).expect("open");
            store.put(b"key", b"durable").expect("commit");
            store.snapshot().expect("snapshot");
        }
        std::fs::remove_file(directory.path().join(WAL_NAME)).expect("remove test WAL");
        assert!(matches!(
            Store::open(directory.path()),
            Err(StorageError::Corrupt {
                component: "WAL",
                reason: "missing after a committed snapshot"
            })
        ));
    }

    #[test]
    fn initializes_empty_wal_left_by_first_startup_crash() {
        let directory = tempdir().expect("tempdir");
        File::create(directory.path().join(WAL_NAME)).expect("empty WAL");
        let mut store = Store::open(directory.path()).expect("initialize WAL");
        assert_eq!(store.put(b"key", b"value").expect("commit"), 1);
    }

    #[tokio::test]
    async fn actor_acks_after_commit() {
        let directory = tempdir().expect("tempdir");
        let actor = PersistenceHandle::start(directory.path()).expect("start actor");
        assert_eq!(
            actor
                .put(b"a".to_vec(), b"1".to_vec())
                .await
                .expect("commit"),
            1
        );
        assert_eq!(
            actor.get(b"a".to_vec()).await.expect("read"),
            Some(b"1".to_vec())
        );
        assert_eq!(actor.snapshot().await.expect("snapshot"), 1);
        actor.shutdown().await.expect("shutdown");
        assert_eq!(
            Store::open(directory.path()).expect("recover").get(b"a"),
            Some(b"1".as_slice())
        );
    }

    #[test]
    fn crash_probe() {
        let Ok(stage) = std::env::var("MQTT_STORAGE_CRASH_STAGE") else {
            return;
        };
        let directory = std::env::var("MQTT_STORAGE_CRASH_DIRECTORY").expect("test directory");
        let mut store = Store::open(directory).expect("open in child");
        if stage.starts_with("after_wal_append") || stage == "after_wal_fsync" {
            store
                .put(b"crash-key", b"new-value")
                .expect("crash before put returns");
        } else {
            store.snapshot().expect("crash before snapshot returns");
        }
        panic!("crash point {stage} did not fire");
    }

    #[test]
    fn recovers_after_process_exit_at_commit_and_snapshot_boundaries() {
        let stages = [
            "after_wal_append_before_fsync",
            "after_wal_fsync",
            "after_snapshot_temp_fsync",
            "after_snapshot_rename",
            "after_snapshot_dir_fsync",
            "after_wal_truncate",
        ];
        for stage in stages {
            let directory = tempdir().expect("tempdir");
            {
                let mut store = Store::open(directory.path()).expect("open");
                store.put(b"baseline", b"durable").expect("commit baseline");
            }

            let status = Command::new(std::env::current_exe().expect("test executable"))
                .arg("--exact")
                .arg("persistence::tests::crash_probe")
                .arg("--nocapture")
                .env("MQTT_STORAGE_CRASH_STAGE", stage)
                .env("MQTT_STORAGE_CRASH_DIRECTORY", directory.path())
                .stdout(Stdio::null())
                .stderr(Stdio::null())
                .status()
                .expect("spawn crash probe");
            assert_eq!(
                status.code(),
                Some(71),
                "crash point {stage} did not execute"
            );

            let store = Store::open(directory.path()).expect("recover after crash");
            assert_eq!(store.get(b"baseline"), Some(b"durable".as_slice()));
            if stage == "after_wal_fsync" {
                assert_eq!(store.get(b"crash-key"), Some(b"new-value".as_slice()));
            }
            if stage.starts_with("after_snapshot") || stage == "after_wal_truncate" {
                assert_eq!(store.sequence(), 1);
            }
        }
    }
}
