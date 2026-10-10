//! Offline, versioned backups of the durable MQTT state.

use std::{
    error::Error,
    fs::{self, File, OpenOptions},
    io::{self, Read, Write},
    path::{Path, PathBuf},
    sync::atomic::{AtomicU64, Ordering},
};

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use super::{SNAPSHOT_NAME, Store, WAL_NAME};

const MANIFEST_NAME: &str = "manifest.toml";
const FORMAT_VERSION: u16 = 1;
const STATE_FORMAT_VERSION: u16 = 1;
const MAX_MANIFEST_BYTES: u64 = 16 * 1024;
const MAX_BACKUP_FILE_BYTES: u64 = 80 * 1024 * 1024;
static NEXT_STAGING_ID: AtomicU64 = AtomicU64::new(0);

type Result<T> = std::result::Result<T, Box<dyn Error>>;

#[derive(Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Manifest {
    format_version: u16,
    state_format_version: u16,
    store_sequence: u64,
    files: Vec<FileEntry>,
}

#[derive(Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct FileEntry {
    name: String,
    length: u64,
    sha256: String,
}

/// Create a compacted backup while holding the store's exclusive lock.
///
/// # Errors
///
/// Returns an error if the broker owns the state lock, state recovery or
/// compaction fails, the destination exists, or durable publication fails.
pub fn create(state_dir: &Path, destination: &Path) -> Result<u64> {
    let destination = new_destination(destination)?;
    reject_overlap(state_dir, &destination)?;
    let mut store = Store::open(state_dir)?;
    let sequence = store.snapshot()?;
    let parent = destination
        .parent()
        .ok_or_else(|| invalid_data("destination parent is missing"))?;
    let staging = StagingDir::create(parent, "backup")?;
    let mut files = Vec::new();
    for name in [SNAPSHOT_NAME, WAL_NAME] {
        let path = staging.path.join(name);
        copy_regular_file(&state_dir.join(name), &path)?;
        files.push(file_entry(&path, name)?);
    }
    write_manifest(
        &staging.path,
        &Manifest {
            format_version: FORMAT_VERSION,
            state_format_version: STATE_FORMAT_VERSION,
            store_sequence: sequence,
            files,
        },
    )?;
    sync_directory(&staging.path)?;
    drop(store);
    staging.publish(&destination)?;
    Ok(sequence)
}

/// Check manifest, digests, and recoverability in an isolated temporary copy.
///
/// # Errors
///
/// Returns an error if the manifest, files, hashes, or recovered state are
/// invalid, or temporary storage is unavailable.
pub fn verify(backup: &Path) -> Result<u64> {
    let manifest = read_manifest(backup)?;
    validate_files(backup, &manifest)?;
    let temporary = StagingDir::create(&std::env::temp_dir(), "verify")?;
    copy_manifest_files(backup, &temporary.path, &manifest)?;
    let store = Store::open(&temporary.path)?;
    if store.sequence() != manifest.store_sequence {
        return Err(invalid_data("backup sequence does not match manifest").into());
    }
    Ok(store.sequence())
}

/// Restore into a new directory, publishing only after its copied state recovers.
///
/// # Errors
///
/// Returns an error if the backup is invalid, the destination exists, or the
/// copied state cannot be recovered and durably published.
pub fn restore(backup: &Path, state_dir: &Path) -> Result<u64> {
    let destination = new_destination(state_dir)?;
    reject_overlap(backup, &destination)?;
    let manifest = read_manifest(backup)?;
    validate_files(backup, &manifest)?;
    let parent = destination
        .parent()
        .ok_or_else(|| invalid_data("destination parent is missing"))?;
    let staging = StagingDir::create(parent, "restore")?;
    copy_manifest_files(backup, &staging.path, &manifest)?;
    let store = Store::open(&staging.path)?;
    let sequence = store.sequence();
    if sequence != manifest.store_sequence {
        return Err(invalid_data("backup sequence does not match manifest").into());
    }
    drop(store);
    sync_directory(&staging.path)?;
    staging.publish(&destination)?;
    Ok(sequence)
}

fn read_manifest(directory: &Path) -> Result<Manifest> {
    ensure_directory(directory)?;
    let path = directory.join(MANIFEST_NAME);
    ensure_regular_file(&path)?;
    if fs::metadata(&path)?.len() > MAX_MANIFEST_BYTES {
        return Err(invalid_data("backup manifest exceeds size limit").into());
    }
    let contents = fs::read_to_string(path)?;
    let manifest: Manifest = toml::from_str(&contents)?;
    if manifest.format_version != FORMAT_VERSION
        || manifest.state_format_version != STATE_FORMAT_VERSION
    {
        return Err(invalid_data("unsupported backup format version").into());
    }
    let names = [SNAPSHOT_NAME, WAL_NAME];
    if manifest.files.len() != names.len()
        || manifest.files.iter().zip(names).any(|(entry, expected)| {
            entry.name != expected
                || entry.sha256.len() != 64
                || !entry.sha256.bytes().all(|byte| byte.is_ascii_hexdigit())
                || entry.length > MAX_BACKUP_FILE_BYTES
        })
    {
        return Err(invalid_data("backup manifest file list is invalid").into());
    }
    Ok(manifest)
}

fn validate_files(directory: &Path, manifest: &Manifest) -> Result<()> {
    for entry in &manifest.files {
        let path = directory.join(&entry.name);
        ensure_regular_file(&path)?;
        if fs::metadata(&path)?.len() != entry.length || digest(&path)? != entry.sha256 {
            return Err(invalid_data("backup file digest or length mismatch").into());
        }
    }
    let mut actual = fs::read_dir(directory)?
        .map(|entry| entry.map(|entry| entry.file_name()))
        .collect::<io::Result<Vec<_>>>()?;
    actual.sort();
    let mut expected = [
        std::ffi::OsString::from(MANIFEST_NAME),
        std::ffi::OsString::from(SNAPSHOT_NAME),
        std::ffi::OsString::from(WAL_NAME),
    ];
    expected.sort();
    if actual != expected {
        return Err(invalid_data("backup directory contains unexpected files").into());
    }
    Ok(())
}

fn copy_manifest_files(source: &Path, destination: &Path, manifest: &Manifest) -> Result<()> {
    for entry in &manifest.files {
        copy_regular_file(&source.join(&entry.name), &destination.join(&entry.name))?;
    }
    Ok(())
}

fn file_entry(path: &Path, name: &str) -> Result<FileEntry> {
    Ok(FileEntry {
        name: name.to_owned(),
        length: fs::metadata(path)?.len(),
        sha256: digest(path)?,
    })
}

fn digest(path: &Path) -> Result<String> {
    let mut file = File::open(path)?;
    let mut hasher = Sha256::new();
    let mut buffer = [0_u8; 16 * 1024];
    loop {
        let read = file.read(&mut buffer)?;
        if read == 0 {
            break;
        }
        hasher.update(&buffer[..read]);
    }
    Ok(format!("{:x}", hasher.finalize()))
}

fn write_manifest(directory: &Path, manifest: &Manifest) -> Result<()> {
    let contents = toml::to_string(manifest)?;
    let path = directory.join(MANIFEST_NAME);
    let mut file = OpenOptions::new().write(true).create_new(true).open(path)?;
    set_private_file(&file)?;
    file.write_all(contents.as_bytes())?;
    file.sync_all()?;
    Ok(())
}

fn copy_regular_file(source: &Path, destination: &Path) -> Result<()> {
    ensure_regular_file(source)?;
    let input = File::open(source)?;
    if !input.metadata()?.is_file() || input.metadata()?.len() > MAX_BACKUP_FILE_BYTES {
        return Err(invalid_data("backup file is not regular or exceeds size limit").into());
    }
    let mut output = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(destination)?;
    set_private_file(&output)?;
    io::copy(&mut input.take(MAX_BACKUP_FILE_BYTES), &mut output)?;
    output.sync_all()?;
    Ok(())
}

fn ensure_directory(path: &Path) -> Result<()> {
    let metadata = fs::symlink_metadata(path)?;
    if metadata.file_type().is_symlink() || !metadata.is_dir() {
        return Err(invalid_data("backup path must be a real directory").into());
    }
    Ok(())
}

fn ensure_regular_file(path: &Path) -> Result<()> {
    let metadata = fs::symlink_metadata(path)?;
    if metadata.file_type().is_symlink() || !metadata.is_file() {
        return Err(invalid_data("backup entry must be a regular file").into());
    }
    Ok(())
}

fn new_destination(path: &Path) -> Result<PathBuf> {
    if path.exists() || fs::symlink_metadata(path).is_ok() {
        return Err(invalid_data("destination already exists").into());
    }
    let file_name = path
        .file_name()
        .filter(|name| !name.is_empty())
        .ok_or_else(|| invalid_data("destination must name a new directory"))?;
    let parent = path
        .parent()
        .filter(|parent| !parent.as_os_str().is_empty())
        .unwrap_or(Path::new("."));
    let parent = fs::canonicalize(parent)?;
    if !parent.is_dir() {
        return Err(invalid_data("destination parent must be a directory").into());
    }
    Ok(parent.join(file_name))
}

fn reject_overlap(source: &Path, destination: &Path) -> Result<()> {
    let source = fs::canonicalize(source)?;
    if destination.starts_with(&source) || source.starts_with(destination) {
        return Err(invalid_data("source and destination directories overlap").into());
    }
    Ok(())
}

struct StagingDir {
    path: PathBuf,
    published: bool,
}

impl StagingDir {
    fn create(parent: &Path, purpose: &str) -> Result<Self> {
        for _ in 0..100 {
            let id = NEXT_STAGING_ID.fetch_add(1, Ordering::Relaxed);
            let path = parent.join(format!(".xmqr-{purpose}-{}-{id}.tmp", std::process::id()));
            match fs::create_dir(&path) {
                Ok(()) => {
                    if let Err(error) = set_private_directory(&path) {
                        let _ = fs::remove_dir(&path);
                        return Err(error.into());
                    }
                    return Ok(Self {
                        path,
                        published: false,
                    });
                }
                Err(error) if error.kind() == io::ErrorKind::AlreadyExists => {}
                Err(error) => return Err(error.into()),
            }
        }
        Err(io::Error::new(
            io::ErrorKind::AlreadyExists,
            "cannot allocate staging directory",
        )
        .into())
    }

    fn publish(mut self, destination: &Path) -> Result<()> {
        if destination.exists() || fs::symlink_metadata(destination).is_ok() {
            return Err(invalid_data("destination already exists").into());
        }
        fs::rename(&self.path, destination)?;
        self.published = true;
        let parent = destination
            .parent()
            .ok_or_else(|| invalid_data("destination parent is missing"))?;
        sync_directory(parent)?;
        Ok(())
    }
}

impl Drop for StagingDir {
    fn drop(&mut self) {
        if !self.published {
            let _ = fs::remove_dir_all(&self.path);
        }
    }
}

#[cfg(unix)]
fn set_private_directory(path: &Path) -> io::Result<()> {
    use std::os::unix::fs::PermissionsExt;
    fs::set_permissions(path, fs::Permissions::from_mode(0o700))
}

#[cfg(not(unix))]
fn set_private_directory(_path: &Path) -> io::Result<()> {
    Ok(())
}

#[cfg(unix)]
fn set_private_file(file: &File) -> io::Result<()> {
    use std::os::unix::fs::PermissionsExt;
    file.set_permissions(fs::Permissions::from_mode(0o600))
}

#[cfg(not(unix))]
fn set_private_file(_file: &File) -> io::Result<()> {
    Ok(())
}

#[cfg(unix)]
fn sync_directory(path: &Path) -> io::Result<()> {
    File::open(path)?.sync_all()
}

#[cfg(not(unix))]
fn sync_directory(_path: &Path) -> io::Result<()> {
    Err(io::Error::new(
        io::ErrorKind::Unsupported,
        "durable directory sync is supported on Unix only",
    ))
}

fn invalid_data(message: &'static str) -> io::Error {
    io::Error::new(io::ErrorKind::InvalidData, message)
}

#[cfg(all(test, unix))]
mod tests {
    use std::{
        fs::{self, OpenOptions},
        io::{Seek, SeekFrom, Write},
    };

    use tempfile::tempdir;

    use super::{create, restore, verify};
    use crate::persistence::Store;

    #[test]
    fn backup_verify_and_restore_preserve_state_and_refuse_existing_destination() {
        let directory = tempdir().unwrap();
        let source = directory.path().join("source");
        let backup = directory.path().join("backup");
        let restored = directory.path().join("restored");
        fs::create_dir(&source).unwrap();
        let mut store = Store::open(&source).unwrap();
        store.put(b"mqtt-state", b"opaque payload").unwrap();
        drop(store);

        create(&source, &backup).unwrap();
        assert_eq!(verify(&backup).unwrap(), 1);
        assert!(create(&source, &backup).is_err());
        assert_eq!(restore(&backup, &restored).unwrap(), 1);
        let restored_store = Store::open(&restored).unwrap();
        assert_eq!(
            restored_store.get(b"mqtt-state"),
            Some(&b"opaque payload"[..])
        );
        assert!(restore(&backup, &restored).is_err());
    }

    #[test]
    fn verification_rejects_modified_state_without_rewriting_backup() {
        let directory = tempdir().unwrap();
        let source = directory.path().join("source");
        let backup = directory.path().join("backup");
        fs::create_dir(&source).unwrap();
        drop(Store::open(&source).unwrap());
        create(&source, &backup).unwrap();
        let wal = backup.join("state.wal");
        let mut file = OpenOptions::new().write(true).open(&wal).unwrap();
        file.seek(SeekFrom::Start(0)).unwrap();
        file.write_all(b"broken!!!").unwrap();
        file.sync_all().unwrap();
        let before = fs::read(&wal).unwrap();
        assert!(verify(&backup).is_err());
        assert_eq!(fs::read(wal).unwrap(), before);
    }

    #[test]
    fn backup_refuses_an_active_store_lock() {
        let directory = tempdir().unwrap();
        let source = directory.path().join("source");
        let backup = directory.path().join("backup");
        fs::create_dir(&source).unwrap();
        let store = Store::open(&source).unwrap();
        assert!(create(&source, &backup).is_err());
        assert!(!backup.exists());
        drop(store);
    }

    #[test]
    fn restore_refuses_existing_directory_without_modifying_it() {
        let directory = tempdir().unwrap();
        let source = directory.path().join("source");
        let backup = directory.path().join("backup");
        let target = directory.path().join("target");
        fs::create_dir(&source).unwrap();
        drop(Store::open(&source).unwrap());
        create(&source, &backup).unwrap();
        fs::create_dir(&target).unwrap();
        fs::write(target.join("sentinel"), b"keep").unwrap();
        assert!(restore(&backup, &target).is_err());
        assert_eq!(fs::read(target.join("sentinel")).unwrap(), b"keep");
    }
}
