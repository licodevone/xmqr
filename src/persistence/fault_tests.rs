// SPDX-License-Identifier: MIT
//! B06: isolated storage fault campaign; never fills a filesystem.

use super::{
    faults::{Action, Fault, Point},
    *,
};

struct ShortThenError {
    first: bool,
}

impl Read for ShortThenError {
    fn read(&mut self, bytes: &mut [u8]) -> io::Result<usize> {
        if self.first {
            self.first = false;
            bytes[..2].copy_from_slice(&[32, 0]);
            Ok(2)
        } else {
            Err(io::Error::from_raw_os_error(5))
        }
    }
}

#[test]
fn real_read_error_after_short_length_is_not_a_torn_tail() {
    let error = read_record_length(&mut ShortThenError { first: true }).unwrap_err();
    assert_eq!(error.raw_os_error(), Some(5));
    assert_ne!(error.kind(), io::ErrorKind::UnexpectedEof);
}

#[test]
fn record_length_distinguishes_eof_partial_and_complete() {
    assert_eq!(read_record_length(&mut io::Cursor::new([])).unwrap(), None);
    for prefix in 1..4 {
        assert_eq!(
            read_record_length(&mut io::Cursor::new(vec![0; prefix]))
                .unwrap_err()
                .kind(),
            io::ErrorKind::UnexpectedEof
        );
    }
    assert_eq!(
        read_record_length(&mut io::Cursor::new([32, 0, 0, 0])).unwrap(),
        Some([32, 0, 0, 0])
    );
}

fn assert_poisoned(store: &mut Store) {
    assert!(matches!(
        store.ensure_writable(),
        Err(StorageError::Poisoned)
    ));
    assert!(matches!(
        store.put(b"later", b"refused"),
        Err(StorageError::Poisoned)
    ));
    assert!(matches!(store.delete(b"key"), Err(StorageError::Poisoned)));
    assert!(matches!(store.snapshot(), Err(StorageError::Poisoned)));
}

#[test]
fn append_errors_and_write_zero_preserve_memory_and_recover_only_complete_records() {
    for action in [
        Action::Error(28),
        Action::Error(5),
        Action::ErrorAfter(2, 28),
        Action::ErrorAfter(6, 5),
        Action::ZeroAfter(6),
    ] {
        let directory = tempfile::tempdir().unwrap();
        let mut store = Store::open(directory.path()).unwrap();
        store.put(b"key", b"committed").unwrap();
        let committed_length = store.wal.metadata().unwrap().len();
        store.faults.arm(Fault {
            point: Point::WalAppend,
            action,
        });
        let error = store.put(b"key", b"candidate").unwrap_err();
        assert!(matches!(error, StorageError::Io(_)));
        if let Action::ZeroAfter(_) = action {
            let StorageError::Io(error) = error else {
                unreachable!()
            };
            assert_eq!(error.kind(), io::ErrorKind::WriteZero);
        }
        assert_eq!(store.sequence(), 1);
        assert_eq!(store.get(b"key"), Some(b"committed".as_slice()));
        assert_poisoned(&mut store);
        drop(store);
        let mut recovered = Store::open(directory.path()).unwrap();
        assert_eq!(recovered.sequence(), 1);
        assert_eq!(recovered.get(b"key"), Some(b"committed".as_slice()));
        assert_eq!(recovered.wal.metadata().unwrap().len(), committed_length);
        assert_eq!(recovered.put(b"key", b"retry").unwrap(), 2);
    }
}

#[test]
fn short_writes_and_interrupted_write_complete_before_success() {
    for action in [Action::Short(1), Action::Short(3), Action::Interrupted] {
        let directory = tempfile::tempdir().unwrap();
        let mut store = Store::open(directory.path()).unwrap();
        store.faults.arm(Fault {
            point: Point::WalAppend,
            action,
        });
        assert_eq!(store.put(b"key", b"value").unwrap(), 1);
        assert!(store.ensure_writable().is_ok());
        drop(store);
        let recovered = Store::open(directory.path()).unwrap();
        assert_eq!(recovered.sequence(), 1);
        assert_eq!(recovered.get(b"key"), Some(b"value".as_slice()));
    }
}

#[test]
fn sync_error_is_uncertain_and_complete_unacknowledged_record_can_reappear() {
    for delete in [false, true] {
        let directory = tempfile::tempdir().unwrap();
        let mut store = Store::open(directory.path()).unwrap();
        store.put(b"key", b"committed").unwrap();
        store.faults.arm(Fault {
            point: Point::WalSync,
            action: Action::Error(5),
        });
        let result = if delete {
            store.delete(b"key")
        } else {
            store.put(b"key", b"candidate")
        };
        assert!(matches!(result, Err(StorageError::Io(_))));
        assert_eq!(store.sequence(), 1);
        assert_eq!(store.get(b"key"), Some(b"committed".as_slice()));
        assert_poisoned(&mut store);
        drop(store);
        let recovered = Store::open(directory.path()).unwrap();
        assert_eq!(recovered.sequence(), 2);
        assert_eq!(
            recovered.get(b"key"),
            if delete {
                None
            } else {
                Some(b"candidate".as_slice())
            }
        );
    }
}

#[test]
fn snapshot_boundary_failures_keep_all_previously_acknowledged_state() {
    for point in [
        Point::SnapshotCreate,
        Point::SnapshotWrite,
        Point::SnapshotSync,
        Point::SnapshotRename,
        Point::DirectorySync,
        Point::WalTruncate,
        Point::WalHeaderWrite,
        Point::WalCompactSync,
    ] {
        for code in [5, 28] {
            let directory = tempfile::tempdir().unwrap();
            let mut store = Store::open(directory.path()).unwrap();
            store.put(b"key", b"old").unwrap();
            store.snapshot().unwrap();
            store.put(b"key", b"new").unwrap();
            store.put(b"other", b"kept").unwrap();
            store.faults.arm(Fault {
                point,
                action: Action::Error(code),
            });
            assert!(matches!(store.snapshot(), Err(StorageError::Io(_))));
            assert_eq!(store.sequence(), 3);
            assert_poisoned(&mut store);
            drop(store);
            let mut recovered = Store::open(directory.path()).unwrap();
            assert_eq!(recovered.sequence(), 3);
            assert_eq!(recovered.get(b"key"), Some(b"new".as_slice()));
            assert_eq!(recovered.get(b"other"), Some(b"kept".as_slice()));
            assert!(!directory.path().join(SNAPSHOT_TEMP_NAME).exists());
            recovered.snapshot().unwrap();
            assert_eq!(recovered.put(b"next", b"valid").unwrap(), 4);
        }
    }
}

#[test]
fn partial_snapshot_write_is_never_promoted() {
    let directory = tempfile::tempdir().unwrap();
    let mut store = Store::open(directory.path()).unwrap();
    store.put(b"key", b"kept").unwrap();
    store.faults.arm(Fault {
        point: Point::SnapshotWrite,
        action: Action::ErrorAfter(7, 28),
    });
    assert!(store.snapshot().is_err());
    assert!(!directory.path().join(SNAPSHOT_NAME).exists());
    drop(store);
    let recovered = Store::open(directory.path()).unwrap();
    assert_eq!(recovered.sequence(), 1);
    assert_eq!(recovered.get(b"key"), Some(b"kept".as_slice()));
    assert!(!directory.path().join(SNAPSHOT_TEMP_NAME).exists());
}

#[test]
fn complete_invalid_wal_is_rejected_without_truncating_evidence() {
    for case in 0..7 {
        let directory = tempfile::tempdir().unwrap();
        let mut bytes = WAL_HEADER.to_vec();
        bytes.extend(encode_record(1, 1, b"key", b"committed").unwrap());
        match case {
            0 => bytes.extend(encode_record(3, 1, b"next", b"gap").unwrap()),
            1 => bytes.extend(encode_record(1, 2, b"key", &[]).unwrap()),
            2 => bytes[9] ^= 1,
            3 => bytes[10..14].copy_from_slice(&u32::MAX.to_le_bytes()),
            4 => *bytes.last_mut().unwrap() ^= 1,
            5 | 6 => {
                let mut record = encode_record(2, 1, b"next", b"data").unwrap();
                if case == 5 {
                    record[12] = 99;
                } else {
                    record[15..19].copy_from_slice(&u32::MAX.to_le_bytes());
                }
                let split = record.len() - 4;
                let checksum = crc32fast::hash(&record[4..split]);
                record[split..].copy_from_slice(&checksum.to_le_bytes());
                bytes.extend(record);
            }
            _ => unreachable!(),
        }
        let path = directory.path().join(WAL_NAME);
        fs::write(&path, &bytes).unwrap();
        assert!(
            matches!(
                Store::open(directory.path()),
                Err(StorageError::Corrupt { .. })
            ),
            "case {case}"
        );
        assert_eq!(fs::read(path).unwrap(), bytes, "case {case}");
    }
}
