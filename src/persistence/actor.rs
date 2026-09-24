//! Bounded Tokio-facing mailbox backed by a dedicated filesystem thread.

use std::{io, path::Path, thread};

use tokio::sync::{mpsc, oneshot};

use super::{StorageError, Store};

const MAILBOX_CAPACITY: usize = 256;

enum Command {
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
}

fn closed() -> StorageError {
    StorageError::Io(io::Error::new(
        io::ErrorKind::BrokenPipe,
        "persistence writer is unavailable",
    ))
}
