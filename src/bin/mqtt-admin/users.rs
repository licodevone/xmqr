use std::{
    fs::{self, File, OpenOptions},
    io::{self, Read, Write},
    path::{Path, PathBuf},
};

use fs2::FileExt;
use mqtt_broker::auth::AuthPolicy;
use serde::{Deserialize, Serialize};

const MAX_CONFIG_BYTES: u64 = 1_048_576;
const MAX_USERS: usize = 1_024;
const MAX_USERNAME_BYTES: usize = 128;

#[derive(Default, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct UsersFile {
    users: Vec<UserRecord>,
}

#[derive(Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct UserRecord {
    username: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    cert_sha256: Option<String>,
    password_hash: String,
}

pub fn create_user(path: &Path, username: &str, password_hash: &str) -> io::Result<()> {
    validate_username(username)?;
    modify(path, true, |file| {
        if file.users.iter().any(|user| user.username == username) {
            return Err(invalid("user already exists"));
        }
        if file.users.len() >= MAX_USERS {
            return Err(invalid("user count exceeds limit"));
        }
        file.users.push(UserRecord {
            username: username.to_owned(),
            cert_sha256: None,
            password_hash: password_hash.to_owned(),
        });
        Ok(())
    })
}

pub fn update_password(path: &Path, username: &str, password_hash: &str) -> io::Result<()> {
    validate_username(username)?;
    modify(path, false, |file| {
        let user = file
            .users
            .iter_mut()
            .find(|user| user.username == username)
            .ok_or_else(|| invalid("user does not exist"))?;
        password_hash.clone_into(&mut user.password_hash);
        Ok(())
    })
}

pub fn delete_user(path: &Path, username: &str) -> io::Result<()> {
    validate_username(username)?;
    modify(path, false, |file| {
        let before = file.users.len();
        file.users.retain(|user| user.username != username);
        if file.users.len() == before {
            return Err(invalid("user does not exist"));
        }
        Ok(())
    })
}

pub fn list_users(path: &Path) -> io::Result<Vec<String>> {
    with_lock(path, || {
        let mut file = read_users(path, false)?;
        file.users
            .sort_by(|left, right| left.username.cmp(&right.username));
        Ok(file.users.into_iter().map(|user| user.username).collect())
    })
}

fn modify(
    path: &Path,
    allow_missing: bool,
    operation: impl FnOnce(&mut UsersFile) -> io::Result<()>,
) -> io::Result<()> {
    with_lock(path, || {
        let mut file = read_users(path, allow_missing)?;
        operation(&mut file)?;
        file.users
            .sort_by(|left, right| left.username.cmp(&right.username));
        write_atomic(path, &file)
    })
}

fn with_lock<T>(path: &Path, operation: impl FnOnce() -> io::Result<T>) -> io::Result<T> {
    let parent = path
        .parent()
        .filter(|parent| !parent.as_os_str().is_empty())
        .unwrap_or_else(|| Path::new("."));
    fs::create_dir_all(parent)?;
    let lock_path = lock_path(path)?;
    reject_symlink(&lock_path)?;
    let lock_file = open_private(&lock_path, false)?;
    ensure_private_permissions(&lock_file.metadata()?)?;
    FileExt::lock_exclusive(&lock_file)?;
    let result = operation();
    let unlock_result = FileExt::unlock(&lock_file);
    match result {
        Ok(value) => {
            unlock_result?;
            Ok(value)
        }
        Err(error) => {
            let _ = unlock_result;
            Err(error)
        }
    }
}

fn read_users(path: &Path, allow_missing: bool) -> io::Result<UsersFile> {
    match fs::symlink_metadata(path) {
        Ok(metadata) => {
            if metadata.file_type().is_symlink() || !metadata.is_file() {
                return Err(invalid("users file must be a regular non-symlink file"));
            }
            ensure_private_permissions(&metadata)?;
        }
        Err(error) if error.kind() == io::ErrorKind::NotFound && allow_missing => {
            return Ok(UsersFile::default());
        }
        Err(error) => return Err(error),
    }
    let mut input = String::new();
    File::open(path)?
        .take(MAX_CONFIG_BYTES + 1)
        .read_to_string(&mut input)?;
    if input.len() as u64 > MAX_CONFIG_BYTES {
        return Err(invalid("users file exceeds size limit"));
    }
    let file: UsersFile = toml::from_str(&input).map_err(|_| invalid("invalid users TOML"))?;
    if file.users.len() > MAX_USERS {
        return Err(invalid("user count exceeds limit"));
    }
    Ok(file)
}

fn write_atomic(path: &Path, users: &UsersFile) -> io::Result<()> {
    let parent = path
        .parent()
        .filter(|parent| !parent.as_os_str().is_empty())
        .unwrap_or_else(|| Path::new("."));
    let file_name = path
        .file_name()
        .and_then(|name| name.to_str())
        .ok_or_else(|| invalid("users file name must be UTF-8"))?;
    let contents =
        toml::to_string_pretty(users).map_err(|_| invalid("cannot encode users TOML"))?;
    if contents.len() as u64 > MAX_CONFIG_BYTES {
        return Err(invalid("users file exceeds size limit"));
    }

    let mut temporary = None;
    for attempt in 0..16_u8 {
        let candidate = parent.join(format!(
            ".{file_name}.tmp.{}.{}",
            std::process::id(),
            attempt
        ));
        match open_private(&candidate, true) {
            Ok(mut file) => {
                file.write_all(contents.as_bytes())?;
                file.flush()?;
                file.sync_all()?;
                temporary = Some(candidate);
                break;
            }
            Err(error) if error.kind() == io::ErrorKind::AlreadyExists => {}
            Err(error) => return Err(error),
        }
    }
    let temporary = temporary.ok_or_else(|| io::Error::other("cannot create temporary file"))?;
    let result = (|| {
        AuthPolicy::load_passwords(&temporary)
            .map_err(|_| invalid("generated users configuration failed validation"))?;
        fs::rename(&temporary, path)?;
        sync_directory(parent)
    })();
    if result.is_err() {
        let _ = fs::remove_file(&temporary);
    }
    result
}

fn lock_path(path: &Path) -> io::Result<PathBuf> {
    let file_name = path
        .file_name()
        .and_then(|name| name.to_str())
        .ok_or_else(|| invalid("users file name must be UTF-8"))?;
    Ok(path.with_file_name(format!(".{file_name}.lock")))
}

fn reject_symlink(path: &Path) -> io::Result<()> {
    match fs::symlink_metadata(path) {
        Ok(metadata) if metadata.file_type().is_symlink() => {
            Err(invalid("lock file cannot be a symlink"))
        }
        Ok(_) => Ok(()),
        Err(error) if error.kind() == io::ErrorKind::NotFound => Ok(()),
        Err(error) => Err(error),
    }
}

#[cfg(unix)]
fn open_private(path: &Path, create_new: bool) -> io::Result<File> {
    use std::os::unix::fs::OpenOptionsExt;
    let mut options = OpenOptions::new();
    options.read(true).write(true).mode(0o600);
    if create_new {
        options.create_new(true);
    } else {
        options.create(true);
    }
    options.open(path)
}

#[cfg(not(unix))]
fn open_private(_path: &Path, _create_new: bool) -> io::Result<File> {
    Err(io::Error::new(
        io::ErrorKind::Unsupported,
        "atomic user administration currently requires Linux/WSL",
    ))
}

#[cfg(unix)]
fn ensure_private_permissions(metadata: &fs::Metadata) -> io::Result<()> {
    use std::os::unix::fs::PermissionsExt;
    if metadata.permissions().mode() & 0o077 != 0 {
        return Err(io::Error::new(
            io::ErrorKind::PermissionDenied,
            "users file must have permission 0600",
        ));
    }
    Ok(())
}

#[cfg(not(unix))]
fn ensure_private_permissions(_metadata: &fs::Metadata) -> io::Result<()> {
    Err(io::Error::new(
        io::ErrorKind::Unsupported,
        "user administration currently requires Linux/WSL",
    ))
}

#[cfg(unix)]
fn sync_directory(path: &Path) -> io::Result<()> {
    File::open(path)?.sync_all()
}

#[cfg(not(unix))]
fn sync_directory(_path: &Path) -> io::Result<()> {
    Err(io::Error::new(
        io::ErrorKind::Unsupported,
        "atomic directory sync currently requires Linux/WSL",
    ))
}

fn validate_username(username: &str) -> io::Result<()> {
    if username.is_empty()
        || username.len() > MAX_USERNAME_BYTES
        || username.chars().any(char::is_control)
    {
        return Err(invalid(
            "username must contain 1 to 128 UTF-8 bytes without controls",
        ));
    }
    Ok(())
}

fn invalid(message: &'static str) -> io::Error {
    io::Error::new(io::ErrorKind::InvalidInput, message)
}

#[cfg(test)]
mod tests {
    use super::*;
    use argon2::password_hash::{PasswordHasher, SaltString};
    use mqtt_broker::auth::argon2_context;
    use std::sync::Arc;

    fn hash(password: &[u8]) -> String {
        let salt = SaltString::encode_b64(b"sixteen-byte-salt").unwrap();
        argon2_context()
            .hash_password(password, &salt)
            .unwrap()
            .to_string()
    }

    #[test]
    fn create_list_update_and_delete_preserve_valid_file() {
        let directory = tempfile::tempdir().unwrap();
        let path = directory.path().join("users.toml");
        create_user(&path, "student", &hash(b"first-password")).unwrap();
        assert_eq!(list_users(&path).unwrap(), ["student"]);
        let first = AuthPolicy::load_passwords(&path).unwrap();
        let runtime = tokio::runtime::Runtime::new().unwrap();
        assert!(
            runtime
                .block_on(first.authenticate_password("student", b"first-password"))
                .unwrap()
                .is_some()
        );

        update_password(&path, "student", &hash(b"second-password")).unwrap();
        let updated = AuthPolicy::load_passwords(&path).unwrap();
        assert!(
            runtime
                .block_on(updated.authenticate_password("student", b"second-password"))
                .unwrap()
                .is_some()
        );
        delete_user(&path, "student").unwrap();
        assert_eq!(list_users(&path).unwrap(), [] as [String; 0]);
        assert!(AuthPolicy::load_passwords(&path).is_ok());
    }

    #[test]
    fn duplicate_or_missing_user_keeps_original_bytes() {
        let directory = tempfile::tempdir().unwrap();
        let path = directory.path().join("users.toml");
        let password_hash = hash(b"password");
        create_user(&path, "student", &password_hash).unwrap();
        let original = fs::read(&path).unwrap();
        assert!(create_user(&path, "student", &password_hash).is_err());
        assert!(delete_user(&path, "missing").is_err());
        assert_eq!(fs::read(&path).unwrap(), original);
    }

    #[test]
    fn concurrent_writers_do_not_lose_updates() {
        let directory = tempfile::tempdir().unwrap();
        let path = Arc::new(directory.path().join("users.toml"));
        create_user(&path, "first", &hash(b"password")).unwrap();
        let hash = Arc::new(hash(b"password"));
        let handles: Vec<_> = ["second", "third"]
            .into_iter()
            .map(|username| {
                let path = Arc::clone(&path);
                let hash = Arc::clone(&hash);
                std::thread::spawn(move || create_user(&path, username, &hash))
            })
            .collect();
        for handle in handles {
            handle.join().unwrap().unwrap();
        }
        assert_eq!(list_users(&path).unwrap(), ["first", "second", "third"]);
    }

    #[cfg(unix)]
    #[test]
    fn users_file_is_private_and_symlinks_are_rejected() {
        use std::os::unix::fs::{PermissionsExt, symlink};
        let directory = tempfile::tempdir().unwrap();
        let path = directory.path().join("users.toml");
        create_user(&path, "student", &hash(b"password")).unwrap();
        assert_eq!(
            fs::metadata(&path).unwrap().permissions().mode() & 0o777,
            0o600
        );
        let lock = lock_path(&path).unwrap();
        assert_eq!(
            fs::metadata(lock).unwrap().permissions().mode() & 0o777,
            0o600
        );

        let link = directory.path().join("link.toml");
        symlink(&path, &link).unwrap();
        assert!(list_users(&link).is_err());
    }
}
