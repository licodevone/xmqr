//! Opt-in, local-only administrative transport. Initially exposes read-only status.
use std::{ffi::OsString, io, path::PathBuf};

#[derive(Clone)]
pub struct Config {
    pub socket: PathBuf,
    pub view_token_file: PathBuf,
    pub operator_token_file: PathBuf,
}

impl Config {
    /// Accept all three paths together, or disable the channel completely.
    /// # Errors
    /// Rejects partial, relative and identical paths.
    pub fn from_lookup(lookup: impl Fn(&str) -> Option<OsString>) -> io::Result<Option<Self>> {
        let paths = [
            lookup("MQTT_ADMIN_SOCKET"),
            lookup("MQTT_ADMIN_VIEW_TOKEN_FILE"),
            lookup("MQTT_ADMIN_OPERATOR_TOKEN_FILE"),
        ];
        if paths.iter().all(Option::is_none) {
            return Ok(None);
        }
        if paths.iter().any(Option::is_none) {
            return Err(invalid("admin channel requires three paths"));
        }
        let [
            Some(socket),
            Some(view_token_file),
            Some(operator_token_file),
        ] = paths
        else {
            unreachable!()
        };
        let config = Self {
            socket: socket.into(),
            view_token_file: view_token_file.into(),
            operator_token_file: operator_token_file.into(),
        };
        if !config.socket.is_absolute()
            || !config.view_token_file.is_absolute()
            || !config.operator_token_file.is_absolute()
            || config.socket == config.view_token_file
            || config.socket == config.operator_token_file
            || config.view_token_file == config.operator_token_file
        {
            return Err(invalid(
                "admin channel paths must be distinct absolute paths",
            ));
        }
        Ok(Some(config))
    }
}

fn invalid(message: &'static str) -> io::Error {
    io::Error::new(io::ErrorKind::InvalidInput, message)
}

#[cfg(target_os = "linux")]
mod linux {
    use super::{Config, invalid};
    use crate::{auth::AccessPolicy, mqtt::Router};
    use serde::Deserialize;
    use serde_json::json;
    use std::{
        fs::{self, OpenOptions},
        io::{self, Read},
        os::unix::fs::{FileTypeExt, MetadataExt, OpenOptionsExt, PermissionsExt},
        path::{Path, PathBuf},
        sync::Arc,
        time::Duration,
    };
    use subtle::ConstantTimeEq;
    use tokio::{
        io::{AsyncReadExt, AsyncWriteExt},
        net::{UnixListener, UnixStream},
        sync::Semaphore,
        task::JoinHandle,
        time::timeout,
    };
    use zeroize::Zeroizing;

    const REQUEST_LIMIT: usize = 16 * 1024;
    const CONNECTIONS: usize = 16;
    const DEADLINE: Duration = Duration::from_secs(2);

    #[derive(Deserialize)]
    #[serde(deny_unknown_fields)]
    struct Request {
        version: u8,
        #[serde(rename = "request_id")]
        id: String,
        operation: String,
        token: String,
    }

    struct Credentials {
        owner: u32,
        view: Zeroizing<Vec<u8>>,
        operator: Zeroizing<Vec<u8>>,
    }

    impl Credentials {
        fn role(&self, token: &str) -> Option<&'static str> {
            if token.len() != 64 || !token.bytes().all(|b| b.is_ascii_hexdigit()) {
                return None;
            }
            let view = bool::from(self.view.as_slice().ct_eq(token.as_bytes()));
            let operator = bool::from(self.operator.as_slice().ct_eq(token.as_bytes()));
            if operator {
                Some("operator")
            } else if view {
                Some("viewer")
            } else {
                None
            }
        }
    }

    pub struct AdminChannel {
        task: JoinHandle<()>,
        path: PathBuf,
        device: u64,
        inode: u64,
    }

    impl Drop for AdminChannel {
        fn drop(&mut self) {
            self.task.abort();
            if let Ok(metadata) = fs::symlink_metadata(&self.path)
                && metadata.file_type().is_socket()
                && metadata.dev() == self.device
                && metadata.ino() == self.inode
            {
                let _ = fs::remove_file(&self.path);
            }
        }
    }

    impl AdminChannel {
        /// Start the opt-in socket after the router exists, before MQTT serving.
        /// # Errors
        /// Rejects static security policies and insecure filesystem inputs.
        pub fn start(
            config: &Config,
            auth: Arc<AccessPolicy>,
            router: Arc<Router>,
        ) -> io::Result<Self> {
            if auth.security_generation() == 0 {
                return Err(invalid("admin channel requires dynamic security bundle"));
            }
            let parent = config
                .socket
                .parent()
                .ok_or_else(|| invalid("admin socket parent missing"))?;
            private_parent(parent)?;
            for path in [&config.view_token_file, &config.operator_token_file] {
                private_parent(
                    path.parent()
                        .ok_or_else(|| invalid("token parent missing"))?,
                )?;
            }
            let owner = fs::symlink_metadata(parent)?.uid();
            let credentials = Arc::new(Credentials {
                owner,
                view: read_token(&config.view_token_file, owner)?,
                operator: read_token(&config.operator_token_file, owner)?,
            });
            if credentials.view.as_slice() == credentials.operator.as_slice() {
                return Err(invalid("admin role tokens must differ"));
            }
            match fs::symlink_metadata(&config.socket) {
                Ok(_) => return Err(invalid("admin socket path already exists")),
                Err(error) if error.kind() == io::ErrorKind::NotFound => {}
                Err(error) => return Err(error),
            }
            let listener = UnixListener::bind(&config.socket)?;
            let metadata = (|| {
                fs::set_permissions(&config.socket, fs::Permissions::from_mode(0o600))?;
                let metadata = fs::symlink_metadata(&config.socket)?;
                if !metadata.file_type().is_socket() || metadata.uid() != owner {
                    return Err(invalid("admin socket owner mismatch"));
                }
                Ok(metadata)
            })();
            let Ok(metadata) = metadata else {
                let _ = fs::remove_file(&config.socket);
                return Err(invalid("admin socket setup failed"));
            };
            let task = tokio::spawn(async move {
                let permits = Arc::new(Semaphore::new(CONNECTIONS));
                while let Ok((stream, _)) = listener.accept().await {
                    let Ok(permit) = permits.clone().try_acquire_owned() else {
                        continue;
                    };
                    let credentials = credentials.clone();
                    let auth = auth.clone();
                    let router = router.clone();
                    tokio::spawn(async move {
                        let _permit = permit;
                        let _ =
                            timeout(DEADLINE, handle(stream, &credentials, &auth, &router)).await;
                    });
                }
            });
            Ok(Self {
                task,
                path: config.socket.clone(),
                device: metadata.dev(),
                inode: metadata.ino(),
            })
        }
    }

    async fn handle(
        mut stream: UnixStream,
        credentials: &Credentials,
        auth: &AccessPolicy,
        router: &Router,
    ) -> io::Result<()> {
        let peer = stream.peer_cred()?;
        if peer.uid() != credentials.owner {
            return Ok(());
        }
        let mut bytes = Zeroizing::new(Vec::with_capacity(512));
        let mut chunk = Zeroizing::new([0_u8; 1024]);
        loop {
            let count = stream.read(&mut *chunk).await?;
            if count == 0 || bytes.len() + count > REQUEST_LIMIT {
                return Ok(());
            }
            bytes.extend_from_slice(&chunk[..count]);
            if bytes.contains(&b'\n') {
                break;
            }
        }
        let Some(line_end) = bytes.iter().position(|b| *b == b'\n') else {
            return Ok(());
        };
        if bytes[line_end + 1..]
            .iter()
            .any(|b| !b.is_ascii_whitespace())
        {
            return Ok(());
        }
        let Ok(request) = serde_json::from_slice::<Request>(&bytes[..line_end]) else {
            return reply(&mut stream, json!({"ok":false,"error":"invalid_request"})).await;
        };
        let Request {
            version,
            id,
            operation,
            token,
        } = request;
        let token = Zeroizing::new(token);
        if version != 1 || id.len() != 32 || !id.bytes().all(|b| b.is_ascii_hexdigit()) {
            return reply(&mut stream, json!({"ok":false,"error":"invalid_request"})).await;
        }
        let Some(role) = credentials.role(&token) else {
            return reply(&mut stream, json!({"ok":false,"error":"unauthorized"})).await;
        };
        if operation != "status" {
            return reply(
                &mut stream,
                json!({"ok":false,"error":"unsupported_operation","request_id":id}),
            )
            .await;
        }
        let ready = router.probe().await;
        reply(
            &mut stream,
            json!({"ok":true,"request_id":id,"role":role,
            "security_generation":auth.security_generation(),"ready":ready}),
        )
        .await
    }

    async fn reply(stream: &mut UnixStream, value: serde_json::Value) -> io::Result<()> {
        let mut bytes = serde_json::to_vec(&value)
            .map_err(|_| io::Error::other("admin response encode failed"))?;
        bytes.push(b'\n');
        stream.write_all(&bytes).await
    }

    fn private_parent(path: &Path) -> io::Result<()> {
        let metadata = fs::symlink_metadata(path)?;
        if !metadata.is_dir() || metadata.permissions().mode() & 0o077 != 0 {
            return Err(invalid("admin directory must be private"));
        }
        Ok(())
    }

    fn read_token(path: &Path, owner: u32) -> io::Result<Zeroizing<Vec<u8>>> {
        let file = OpenOptions::new()
            .read(true)
            .custom_flags(libc::O_NOFOLLOW | libc::O_NONBLOCK)
            .open(path)?;
        let metadata = file.metadata()?;
        if !metadata.is_file()
            || metadata.uid() != owner
            || metadata.permissions().mode() & 0o777 != 0o600
        {
            return Err(invalid(
                "admin token file must be private and owned by broker",
            ));
        }
        let mut bytes = Zeroizing::new(Vec::new());
        file.take(129).read_to_end(&mut bytes)?;
        while bytes.last().is_some_and(u8::is_ascii_whitespace) {
            bytes.pop();
        }
        if bytes.len() != 64 || !bytes.iter().all(u8::is_ascii_hexdigit) {
            return Err(invalid("admin token must be 64 hexadecimal bytes"));
        }
        Ok(bytes)
    }

    #[cfg(test)]
    mod tests {
        use super::*;
        use crate::auth::DynamicPolicy;
        use argon2::password_hash::{PasswordHasher, SaltString};

        fn private_file(path: &Path, contents: &str) {
            fs::write(path, contents).unwrap();
            fs::set_permissions(path, fs::Permissions::from_mode(0o600)).unwrap();
        }

        async fn ask(socket: &Path, token: &str, operation: &str) -> serde_json::Value {
            let mut stream = UnixStream::connect(socket).await.unwrap();
            let request = json!({"version":1,"request_id":"0123456789abcdef0123456789abcdef",
                "operation":operation,"token":token});
            let mut bytes = serde_json::to_vec(&request).unwrap();
            bytes.push(b'\n');
            stream.write_all(&bytes).await.unwrap();
            let mut answer = Vec::new();
            stream.read_to_end(&mut answer).await.unwrap();
            serde_json::from_slice(&answer).unwrap()
        }

        #[tokio::test]
        async fn private_status_accepts_roles_and_rejects_bad_token_or_mutation() {
            let root = tempfile::tempdir().unwrap();
            fs::set_permissions(root.path(), fs::Permissions::from_mode(0o700)).unwrap();
            let bundle = root.path().join("bundle.toml");
            let salt = SaltString::encode_b64(b"sixteen-byte-salt").unwrap();
            let hash = crate::auth::argon2_context()
                .hash_password(b"fixture", &salt)
                .unwrap();
            private_file(
                &bundle,
                &format!(
                    "version=1\n[[users]]\nusername='fixture'\npassword_hash='{hash}'\ncert_sha256='sha256:{}'\n",
                    "00".repeat(32)
                ),
            );
            let auth = Arc::new(DynamicPolicy::load(bundle, true).await.unwrap());
            fs::create_dir(root.path().join("state")).unwrap();
            let router = Arc::new(
                Router::start(&root.path().join("state"), auth.clone())
                    .await
                    .unwrap(),
            );
            let config = Config {
                socket: root.path().join("admin.sock"),
                view_token_file: root.path().join("view.token"),
                operator_token_file: root.path().join("operator.token"),
            };
            private_file(&config.view_token_file, &"a".repeat(64));
            private_file(&config.operator_token_file, &"b".repeat(64));
            let channel = AdminChannel::start(&config, auth, router.clone()).unwrap();
            let viewer = ask(&config.socket, &"a".repeat(64), "status").await;
            assert_eq!(viewer["ok"], true);
            assert_eq!(viewer["role"], "viewer");
            assert_eq!(viewer["security_generation"], 1);
            let operator = ask(&config.socket, &"b".repeat(64), "status").await;
            assert_eq!(operator["role"], "operator");
            assert_eq!(
                ask(&config.socket, &"c".repeat(64), "status").await["error"],
                "unauthorized"
            );
            assert_eq!(
                ask(&config.socket, &"b".repeat(64), "reload").await["error"],
                "unsupported_operation"
            );
            let mut slow = UnixStream::connect(&config.socket).await.unwrap();
            slow.write_all(b"{").await.unwrap();
            let mut byte = [0_u8; 1];
            assert_eq!(
                timeout(Duration::from_secs(3), slow.read(&mut byte))
                    .await
                    .unwrap()
                    .unwrap(),
                0
            );
            drop(channel);
            assert!(!config.socket.exists());
            router.shutdown().await.unwrap();
        }

        #[test]
        fn partial_config_and_insecure_tokens_fail_closed() {
            assert!(
                Config::from_lookup(|name| if name == "MQTT_ADMIN_SOCKET" {
                    Some("/tmp/admin.sock".into())
                } else {
                    None
                })
                .is_err()
            );
            let root = tempfile::tempdir().unwrap();
            fs::set_permissions(root.path(), fs::Permissions::from_mode(0o700)).unwrap();
            let token = root.path().join("token");
            private_file(&token, &"a".repeat(64));
            let owner = fs::metadata(&token).unwrap().uid();
            assert!(read_token(&token, owner).is_ok());
            fs::set_permissions(&token, fs::Permissions::from_mode(0o644)).unwrap();
            assert!(read_token(&token, owner).is_err());
            let link = root.path().join("link");
            std::os::unix::fs::symlink(&token, &link).unwrap();
            assert!(read_token(&link, owner).is_err());
        }
    }
}

#[cfg(target_os = "linux")]
pub use linux::AdminChannel;

#[cfg(not(target_os = "linux"))]
pub struct AdminChannel;

#[cfg(not(target_os = "linux"))]
impl AdminChannel {
    /// # Errors
    /// This channel is Linux-only.
    pub fn start(
        _: &Config,
        _: std::sync::Arc<crate::auth::AccessPolicy>,
        _: std::sync::Arc<crate::mqtt::Router>,
    ) -> io::Result<Self> {
        Err(io::Error::new(
            io::ErrorKind::Unsupported,
            "admin channel requires Linux",
        ))
    }
}
