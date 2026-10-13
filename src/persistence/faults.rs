// SPDX-License-Identifier: MIT
//! Per-store deterministic I/O doubles. This entire module is test-only.

use std::{
    fs::File,
    io::{self, Write},
};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum Point {
    WalAppend,
    WalSync,
    SnapshotCreate,
    SnapshotWrite,
    SnapshotSync,
    SnapshotRename,
    DirectorySync,
    WalTruncate,
    WalHeaderWrite,
    WalCompactSync,
}

#[derive(Clone, Copy, Debug)]
pub(crate) enum Action {
    Error(i32),
    ErrorAfter(usize, i32),
    ZeroAfter(usize),
    Short(usize),
    Interrupted,
}

#[derive(Clone, Copy, Debug)]
pub(crate) struct Fault {
    pub point: Point,
    pub action: Action,
}

#[derive(Default)]
pub(super) struct Faults {
    pending: Option<Fault>,
}

impl Faults {
    pub fn arm(&mut self, fault: Fault) {
        assert!(
            self.pending.replace(fault).is_none(),
            "unconsumed test fault"
        );
    }

    fn take(&mut self, point: Point) -> Option<Action> {
        if self.pending.is_some_and(|fault| fault.point == point) {
            self.pending.take().map(|fault| fault.action)
        } else {
            None
        }
    }

    pub fn check(&mut self, point: Point) -> io::Result<()> {
        match self.take(point) {
            None => Ok(()),
            Some(Action::Error(code)) => Err(io::Error::from_raw_os_error(code)),
            Some(_) => panic!("write action supplied to a non-write boundary"),
        }
    }

    pub fn write_all(&mut self, point: Point, file: &mut File, bytes: &[u8]) -> io::Result<()> {
        let Some(action) = self.take(point) else {
            return file.write_all(bytes);
        };
        ControlledWriter {
            file,
            action,
            written: 0,
            interrupted: false,
        }
        .write_all(bytes)
    }
}

struct ControlledWriter<'a> {
    file: &'a mut File,
    action: Action,
    written: usize,
    interrupted: bool,
}

impl Write for ControlledWriter<'_> {
    fn write(&mut self, bytes: &[u8]) -> io::Result<usize> {
        let limit = match self.action {
            Action::Error(code) => return Err(io::Error::from_raw_os_error(code)),
            Action::ErrorAfter(limit, code) => {
                if self.written >= limit {
                    return Err(io::Error::from_raw_os_error(code));
                }
                limit - self.written
            }
            Action::ZeroAfter(limit) => {
                if self.written >= limit {
                    return Ok(0);
                }
                limit - self.written
            }
            Action::Short(limit) => {
                assert!(limit > 0);
                limit
            }
            Action::Interrupted if !self.interrupted => {
                self.interrupted = true;
                return Err(io::ErrorKind::Interrupted.into());
            }
            Action::Interrupted => bytes.len(),
        };
        let count = self.file.write(&bytes[..bytes.len().min(limit)])?;
        self.written += count;
        Ok(count)
    }

    fn flush(&mut self) -> io::Result<()> {
        self.file.flush()
    }
}
