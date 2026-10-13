//! Bounded Tokio-facing mailbox backed by a dedicated filesystem thread.

use std::{io, path::Path, thread};

use tokio::sync::{mpsc, oneshot};

use super::{StorageError, Store};

const MAILBOX_CAPACITY: usize = 256;

enum Command {
    #[cfg(test)]
    Inject {
        fault: super::faults::Fault,
        reply: oneshot::Sender<()>,
    },
    Probe {
        reply: oneshot::Sender<Result<(), StorageError>>,
    },
    Put {
        key: Vec<u8>,
        value: Vec<u8>,
        reply: oneshot::Sender<Result<u64, StorageError>>,
    },
    Delete {
        key: Vec<u8>,
        reply: oneshot::Sender<Result<u64, StorageError>>,
    },
    Get {
        key: Vec<u8>,
        reply: oneshot::Sender<Result<Option<Vec<u8>>, StorageError>>,
    },
    Snapshot {
        reply: oneshot::Sender<Result<u64, StorageError>>,
    },
    Shutdown {
        reply: oneshot::Sender<()>,
    },
}

/// Cloneable producer for the single storage writer.
///
/// The bounded mailbox applies backpressure. `put`/`delete` resolve only after
/// WAL `fsync`, so a caller may safely use a successful result as a durability
/// barrier before sending an MQTT acknowledgment.
#[derive(Clone)]
pub struct PersistenceHandle {
    sender: mpsc::Sender<Command>,
}

impl PersistenceHandle {
    /// Open durable state, then start one dedicated blocking writer thread.
    ///
    /// # Errors
    ///
    /// Returns a recovery, lock, or thread-creation error.
    pub fn start(directory: impl AsRef<Path>) -> Result<Self, StorageError> {
        let mut store = Store::open(directory)?;
        let (sender, mut receiver) = mpsc::channel(MAILBOX_CAPACITY);
        thread::Builder::new()
            .name("mqtt-persistence".to_owned())
            .spawn(move || {
                while let Some(command) = receiver.blocking_recv() {
                    match command {
                        #[cfg(test)]
                        Command::Inject { fault, reply } => {
                            store.faults.arm(fault);
                            let _ = reply.send(());
                        }
                        Command::Probe { reply } => {
                            let _ = reply.send(store.ensure_writable());
                        }
                        Command::Put { key, value, reply } => {
                            let _ = reply.send(store.put(&key, &value));
                        }
                        Command::Delete { key, reply } => {
                            let _ = reply.send(store.delete(&key));
                        }
                        Command::Get { key, reply } => {
                            let value = store
                                .ensure_writable()
                                .map(|()| store.get(&key).map(ToOwned::to_owned));
                            let _ = reply.send(value);
                        }
                        Command::Snapshot { reply } => {
                            let _ = reply.send(store.snapshot());
                        }
                        Command::Shutdown { reply } => {
                            drop(store);
                            let _ = reply.send(());
                            return;
                        }
                    }
                }
            })
            .map_err(StorageError::Io)?;
        Ok(Self { sender })
    }

    /// Check the existing writer's availability and last writable state.
    /// # Errors
    /// Returns a fatal writer error or a closed mailbox; performs no disk write.
    pub async fn probe(&self) -> Result<(), StorageError> {
        let (reply, result) = oneshot::channel();
        self.send(Command::Probe { reply }).await?;
        result.await.map_err(|_| closed())?
    }

    /// Commit an upsert; successful return means the WAL has been synced.
    ///
    /// # Errors
    ///
    /// Returns the writer's storage error or a closed-mailbox error.
    pub async fn put(&self, key: Vec<u8>, value: Vec<u8>) -> Result<u64, StorageError> {
        let (reply, result) = oneshot::channel();
        self.send(Command::Put { key, value, reply }).await?;
        result.await.map_err(|_| closed())?
    }

    /// Commit a deletion; successful return means the WAL has been synced.
    ///
    /// # Errors
    ///
    /// Returns the writer's storage error or a closed-mailbox error.
    pub async fn delete(&self, key: Vec<u8>) -> Result<u64, StorageError> {
        let (reply, result) = oneshot::channel();
        self.send(Command::Delete { key, reply }).await?;
        result.await.map_err(|_| closed())?
    }

    /// Read the writer's current committed view.
    ///
    /// # Errors
    ///
    /// Returns a closed-mailbox error when the writer is unavailable.
    pub async fn get(&self, key: Vec<u8>) -> Result<Option<Vec<u8>>, StorageError> {
        let (reply, result) = oneshot::channel();
        self.send(Command::Get { key, reply }).await?;
        result.await.map_err(|_| closed())?
    }

    /// Publish and sync a versioned snapshot, then compact the WAL.
    ///
    /// # Errors
    ///
    /// Returns the writer's storage error or a closed-mailbox error.
    pub async fn snapshot(&self) -> Result<u64, StorageError> {
        let (reply, result) = oneshot::channel();
        self.send(Command::Snapshot { reply }).await?;
        result.await.map_err(|_| closed())?
    }

    /// Drain earlier commands, stop the writer, and release the storage lock.
    ///
    /// # Errors
    ///
    /// Returns a closed-mailbox error if the writer already exited.
    pub async fn shutdown(self) -> Result<(), StorageError> {
        let (reply, result) = oneshot::channel();
        self.send(Command::Shutdown { reply }).await?;
        result.await.map_err(|_| closed())
    }

    async fn send(&self, command: Command) -> Result<(), StorageError> {
        self.sender.send(command).await.map_err(|_| closed())
    }

    #[cfg(test)]
    pub(crate) async fn inject_for_test(
        &self,
        fault: super::faults::Fault,
    ) -> Result<(), StorageError> {
        let (reply, result) = oneshot::channel();
        self.send(Command::Inject { fault, reply }).await?;
        result.await.map_err(|_| closed())
    }
}

fn closed() -> StorageError {
    StorageError::Io(io::Error::new(
        io::ErrorKind::BrokenPipe,
        "persistence writer is unavailable",
    ))
}

#[cfg(test)]
mod tests {
    use super::*;
    #[cfg(unix)]
    #[tokio::test]
    async fn failed_writer_refuses_reads_probes_and_mutations_until_reopen() {
        use crate::persistence::faults::{Action, Fault, Point};
        let directory = tempfile::tempdir().unwrap();
        let writer = PersistenceHandle::start(directory.path()).unwrap();
        writer
            .put(b"key".to_vec(), b"committed".to_vec())
            .await
            .unwrap();
        writer
            .inject_for_test(Fault {
                point: Point::WalAppend,
                action: Action::Error(28),
            })
            .await
            .unwrap();
        assert!(matches!(
            writer.put(b"key".to_vec(), b"candidate".to_vec()).await,
            Err(StorageError::Io(_))
        ));
        assert!(matches!(writer.probe().await, Err(StorageError::Poisoned)));
        assert!(matches!(
            writer.get(b"key".to_vec()).await,
            Err(StorageError::Poisoned)
        ));
        assert!(matches!(
            writer.delete(b"key".to_vec()).await,
            Err(StorageError::Poisoned)
        ));
        assert!(matches!(
            writer.snapshot().await,
            Err(StorageError::Poisoned)
        ));
        writer.shutdown().await.unwrap();
        let recovered = PersistenceHandle::start(directory.path()).unwrap();
        assert_eq!(
            recovered.get(b"key".to_vec()).await.unwrap(),
            Some(b"committed".to_vec())
        );
        recovered.probe().await.unwrap();
        recovered.shutdown().await.unwrap();
    }
    #[tokio::test]
    async fn probe_detects_writer_shutdown_without_copying_or_writing_state() {
        let directory = tempfile::tempdir().unwrap();
        let writer = PersistenceHandle::start(directory.path()).unwrap();
        writer.probe().await.unwrap();
        writer.clone().shutdown().await.unwrap();
        assert!(writer.probe().await.is_err());
    }
}
