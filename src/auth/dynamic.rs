//! Opt-in private, versioned security bundles and local administrative reload.
#[cfg(target_os = "linux")]
use super::MAX_CONFIG_BYTES;
use super::{
    AccessPolicy, AclFile, AclRule, AuthError, AuthPolicy, MAX_PARALLEL_HASHES, MAX_USERS,
    UserRecord, UsersFile, valid_username,
};
use crate::mqtt::Router;
use serde::Deserialize;
use std::{
    collections::{BTreeSet, HashMap},
    io,
    path::{Path, PathBuf},
    sync::{
        Arc, RwLock,
        atomic::{AtomicU64, Ordering},
    },
};
#[cfg(target_os = "linux")]
use std::{fs::File, io::Read};
use tokio::{sync::Semaphore, task::JoinHandle};

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Bundle {
    version: u32,
    users: Vec<BundleUser>,
    #[serde(default)]
    roles: Vec<Role>,
    #[serde(default)]
    groups: Vec<Group>,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct BundleUser {
    username: String,
    password_hash: String,
    #[serde(default)]
    cert_sha256: Option<String>,
    #[serde(default)]
    disabled: bool,
    #[serde(default)]
    publish: Vec<String>,
    #[serde(default)]
    subscribe: Vec<String>,
    #[serde(default)]
    roles: Vec<String>,
    #[serde(default)]
    groups: Vec<String>,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Role {
    name: String,
    #[serde(default)]
    publish: Vec<String>,
    #[serde(default)]
    subscribe: Vec<String>,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Group {
    name: String,
    roles: Vec<String>,
}

fn unique(values: &[String]) -> bool {
    values.iter().collect::<BTreeSet<_>>().len() == values.len()
}

fn validate_role(role: &Role) -> Result<(), AuthError> {
    if !valid_username(&role.name)
        || role.publish.len() > 256
        || role.subscribe.len() > 256
        || role
            .publish
            .iter()
            .any(|t| !crate::mqtt::topic::valid_topic_name(t))
        || role
            .subscribe
            .iter()
            .any(|t| !crate::mqtt::topic::valid_topic_filter(t))
    {
        return Err(AuthError::Config("invalid security role"));
    }
    Ok(())
}

fn compile(
    text: &str,
    secure: bool,
    slots: Arc<Semaphore>,
    dummy: Option<String>,
) -> Result<AuthPolicy, AuthError> {
    let bundle: Bundle =
        toml::from_str(text).map_err(|_| AuthError::Config("security bundle syntax"))?;
    if bundle.version != 1
        || bundle.users.len() > MAX_USERS
        || bundle.roles.len() > 128
        || bundle.groups.len() > 128
    {
        return Err(AuthError::Config("security bundle version or quota"));
    }
    let mut roles = HashMap::new();
    for role in bundle.roles {
        validate_role(&role)?;
        if roles.insert(role.name.clone(), role).is_some() {
            return Err(AuthError::Config("duplicate security role"));
        }
    }
    let mut groups = HashMap::new();
    for group in bundle.groups {
        if !valid_username(&group.name)
            || group.roles.len() > 64
            || !unique(&group.roles)
            || group.roles.iter().any(|r| !roles.contains_key(r))
        {
            return Err(AuthError::Config("invalid security group"));
        }
        if groups.insert(group.name, group.roles).is_some() {
            return Err(AuthError::Config("duplicate security group"));
        }
    }
    let mut users = Vec::new();
    let mut grants_by_user = Vec::new();
    for user in bundle.users {
        if user.roles.len() > 64
            || user.groups.len() > 64
            || user.publish.len() > 256
            || user.subscribe.len() > 256
            || !unique(&user.roles)
            || !unique(&user.groups)
            || user
                .publish
                .iter()
                .any(|t| !crate::mqtt::topic::valid_topic_name(t))
            || user
                .subscribe
                .iter()
                .any(|t| !crate::mqtt::topic::valid_topic_filter(t))
        {
            return Err(AuthError::Config("security membership quota"));
        }
        let mut effective = BTreeSet::new();
        for role in user.roles {
            effective.insert(role);
        }
        for group in user.groups {
            let assigned = groups
                .get(&group)
                .ok_or(AuthError::Config("unknown security group"))?;
            effective.extend(assigned.iter().cloned());
        }
        let mut publish: BTreeSet<String> = user.publish.into_iter().collect();
        let mut subscribe: BTreeSet<String> = user.subscribe.into_iter().collect();
        for name in effective {
            let role = roles
                .get(&name)
                .ok_or(AuthError::Config("unknown security role"))?;
            publish.extend(role.publish.iter().cloned());
            subscribe.extend(role.subscribe.iter().cloned());
        }
        if user.disabled {
            publish.clear();
            subscribe.clear();
        }
        grants_by_user.push(AclRule {
            username: user.username.clone(),
            publish: publish.into_iter().collect(),
            subscribe: subscribe.into_iter().collect(),
        });
        users.push(UserRecord {
            username: user.username,
            password_hash: user.password_hash,
            cert_sha256: user.cert_sha256,
            disabled: user.disabled,
        });
    }
    AuthPolicy::from_files(
        UsersFile { users },
        AclFile {
            rules: grants_by_user,
        },
        secure,
        slots,
        dummy,
    )
}

fn read_private(path: &Path) -> Result<String, AuthError> {
    #[cfg(not(target_os = "linux"))]
    {
        let _ = path;
        Err(AuthError::Config("dynamic security requires Linux/WSL"))
    }
    #[cfg(target_os = "linux")]
    {
        use std::os::unix::fs::{MetadataExt, OpenOptionsExt};
        let before = std::fs::symlink_metadata(path)?;
        if !before.is_file() {
            return Err(AuthError::Config(
                "security bundle requires private regular file",
            ));
        }
        // Linux O_NOFOLLOW | O_NONBLOCK also rejects symlink/FIFO swaps before open.
        let file = File::options()
            .read(true)
            .custom_flags(0x20000 | 0x800)
            .open(path)?;
        let metadata = file.metadata()?;
        let uid = std::fs::read_to_string("/proc/self/status")?
            .lines()
            .find_map(|line| {
                line.strip_prefix("Uid:")
                    .and_then(|v| v.split_whitespace().nth(1))
                    .and_then(|v| v.parse::<u32>().ok())
            })
            .ok_or(AuthError::Config("effective uid unavailable"))?;
        if !before.is_file()
            || !metadata.is_file()
            || before.ino() != metadata.ino()
            || before.dev() != metadata.dev()
            || metadata.uid() != uid
            || metadata.mode() & 0o7777 != 0o600
            || metadata.len() > MAX_CONFIG_BYTES
        {
            return Err(AuthError::Config(
                "security bundle requires private regular file",
            ));
        }
        let mut text = String::new();
        file.take(MAX_CONFIG_BYTES + 1).read_to_string(&mut text)?;
        if u64::try_from(text.len()).unwrap_or(u64::MAX) > MAX_CONFIG_BYTES {
            return Err(AuthError::Config("security bundle exceeds limit"));
        }
        Ok(text)
    }
}

/// One process-global policy snapshot; no lock is held across async operations.
pub struct DynamicPolicy {
    policy: RwLock<AuthPolicy>,
    generation: AtomicU64,
    #[cfg_attr(not(unix), allow(dead_code))]
    slots: Arc<Semaphore>,
    #[cfg_attr(not(unix), allow(dead_code))]
    path: PathBuf,
    secure: bool,
}
impl DynamicPolicy {
    /// Load an opt-in private bundle outside the async runtime workers.
    /// # Errors
    /// Rejects invalid permissions, identities, roles, grants, or configuration.
    pub async fn load(path: PathBuf, secure: bool) -> Result<AccessPolicy, AuthError> {
        let slots = Arc::new(Semaphore::new(MAX_PARALLEL_HASHES));
        let candidate_path = path.clone();
        let candidate_slots = slots.clone();
        let policy = tokio::task::spawn_blocking(move || {
            compile(
                &read_private(&candidate_path)?,
                secure,
                candidate_slots,
                None,
            )
        })
        .await
        .map_err(|_| AuthError::Worker)??;
        Ok(AccessPolicy::Dynamic(Arc::new(Self {
            policy: RwLock::new(policy),
            generation: AtomicU64::new(1),
            slots,
            path,
            secure,
        })))
    }
    pub(crate) fn snapshot(&self) -> Option<AuthPolicy> {
        self.policy.read().ok().map(|p| p.clone())
    }
    pub(crate) fn generation(&self) -> u64 {
        self.generation.load(Ordering::Acquire)
    }
    pub(crate) fn view(&self, policy: AuthPolicy) -> AccessPolicy {
        if self.secure {
            AccessPolicy::secure(policy)
        } else {
            AccessPolicy::acl_lab(policy)
        }
    }
    pub(crate) fn publish(&self, policy: AuthPolicy) -> Result<u64, AuthError> {
        let generation = self
            .generation()
            .checked_add(1)
            .ok_or(AuthError::Config("security generation exhausted"))?;
        *self.policy.write().map_err(|_| AuthError::Worker)? = policy;
        self.generation.store(generation, Ordering::Release);
        Ok(generation)
    }
    #[cfg(unix)]
    pub(crate) async fn candidate(&self) -> Result<AuthPolicy, AuthError> {
        let path = self.path.clone();
        let secure = self.secure;
        let slots = self.slots.clone();
        let dummy = self
            .snapshot()
            .ok_or(AuthError::Worker)?
            .0
            .dummy_hash
            .clone();
        tokio::task::spawn_blocking(move || {
            compile(&read_private(&path)?, secure, slots, Some(dummy))
        })
        .await
        .map_err(|_| AuthError::Worker)?
    }
    pub(crate) async fn authenticate(
        &self,
        cert: Option<&[u8]>,
        username: Option<&str>,
        password: Option<&[u8]>,
    ) -> Result<Option<String>, AuthError> {
        let Some(policy) = self.snapshot() else {
            return Err(AuthError::Worker);
        };
        let (Some(username), Some(password)) = (username, password) else {
            return Ok(None);
        };
        if self.secure {
            let Some(cert) = cert else {
                return Ok(None);
            };
            policy.authenticate(cert, username, password).await
        } else if cert.is_none() {
            policy.authenticate_password(username, password).await
        } else {
            Ok(None)
        }
    }
}

/// Lifetime guard for the local signal-based administrative interface.
pub struct SecurityWatcher {
    task: JoinHandle<()>,
}
impl Drop for SecurityWatcher {
    fn drop(&mut self) {
        self.task.abort();
    }
}
/// Watch SIGHUP only for an explicitly enabled dynamic bundle.
/// # Errors
/// Returns signal registration errors; legacy policies create no task.
pub fn watch_security(
    auth: &AccessPolicy,
    router: Arc<Router>,
) -> io::Result<Option<SecurityWatcher>> {
    let Some(policy) = auth.dynamic() else {
        return Ok(None);
    };
    #[cfg(not(unix))]
    {
        let _ = (policy, router);
        Err(io::Error::new(
            io::ErrorKind::Unsupported,
            "dynamic security requires Unix",
        ))
    }
    #[cfg(unix)]
    {
        let mut signals = tokio::signal::unix::signal(tokio::signal::unix::SignalKind::hangup())?;
        let task = tokio::spawn(async move {
            while signals.recv().await.is_some() {
                let Ok(candidate) = policy.candidate().await else {
                    tracing::warn!("security reload rejected; previous policy retained");
                    continue;
                };
                let result = router.reload_security(candidate).await;
                match result {
                    Ok(generation) => tracing::info!(
                        generation,
                        "security reload committed; reauthentication required"
                    ),
                    Err(_) => {
                        tracing::warn!("security reload failed; no successful policy publication");
                    }
                }
            }
        });
        Ok(Some(SecurityWatcher { task }))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use argon2::password_hash::{PasswordHasher, SaltString};

    fn hash() -> String {
        super::super::argon2_context()
            .hash_password(
                b"fixture-pass",
                &SaltString::encode_b64(b"sixteen-byte-salt").unwrap(),
            )
            .unwrap()
            .to_string()
    }
    fn bundle(hash: &str) -> String {
        format!(
            "version=1\n[[roles]]\nname='writer'\npublish=['sensor/value']\nsubscribe=['sensor/#']\n[[groups]]\nname='devices'\nroles=['writer']\n[[users]]\nusername='device'\npassword_hash='{hash}'\ngroups=['devices']\n"
        )
    }
    #[tokio::test]
    async fn groups_grants_and_disabled_users_deny_by_default() {
        let phc = hash();
        let text = bundle(&phc);
        let slots = Arc::new(Semaphore::new(4));
        let policy = compile(&text, false, slots.clone(), Some(phc.clone())).unwrap();
        assert!(policy.allowed_publish("device", "sensor/value"));
        assert!(!policy.allowed_publish("device", "sensor/other"));
        assert!(policy.allowed_subscribe("device", "sensor/#"));
        assert!(!policy.allowed_subscribe("device", "#"));
        assert!(policy.allowed_delivery("device", "sensor/other"));
        assert!(!policy.allowed_delivery("device", "$SYS/hidden"));
        assert_eq!(
            policy
                .authenticate_password("device", b"fixture-pass")
                .await
                .unwrap()
                .as_deref(),
            Some("device")
        );
        let disabled =
            compile(&(text + "disabled=true\n"), false, slots.clone(), Some(phc)).unwrap();
        assert!(Arc::ptr_eq(&policy.0.hash_slots, &disabled.0.hash_slots));
        assert!(Arc::ptr_eq(&slots, &disabled.0.hash_slots));
        assert!(
            disabled
                .authenticate_password("device", b"fixture-pass")
                .await
                .unwrap()
                .is_none()
        );
        assert!(!disabled.allowed_delivery("device", "sensor/value"));
    }
    #[test]
    fn malformed_references_versions_and_memberships_are_rejected() {
        let phc = hash();
        let text = bundle(&phc);
        for invalid in [
            text.replace("version=1", "version=2"),
            text.replace("groups=['devices']", "groups=['missing']"),
            text.replace("roles=['writer']", "roles=['missing']"),
            text.replace("groups=['devices']", "groups=['devices','devices']"),
            text.replace("publish=['sensor/value']", "publish=['sensor/#']"),
            text.clone() + "unknown=true\n",
        ] {
            assert!(
                compile(
                    &invalid,
                    false,
                    Arc::new(Semaphore::new(4)),
                    Some(phc.clone())
                )
                .is_err()
            );
        }
        assert!(
            compile(
                &(text + "disabled=true\npublish=['invalid/#']\n"),
                false,
                Arc::new(Semaphore::new(4)),
                Some(phc)
            )
            .is_err()
        );
    }
    #[cfg(target_os = "linux")]
    #[tokio::test]
    async fn candidate_failure_keeps_generation_and_private_file_is_required() {
        use std::os::unix::fs::PermissionsExt;
        let directory = tempfile::tempdir().unwrap();
        let path = directory.path().join("policy.toml");
        std::fs::write(&path, bundle(&hash())).unwrap();
        std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o600)).unwrap();
        let auth = DynamicPolicy::load(path.clone(), false).await.unwrap();
        let dynamic = auth.dynamic().unwrap();
        std::fs::write(&path, "version=999\nusers=[]\n").unwrap();
        assert!(dynamic.candidate().await.is_err());
        assert_eq!(auth.security_generation(), 1);
        assert!(auth.allowed_publish("device", "sensor/value"));
        std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o644)).unwrap();
        assert!(read_private(&path).is_err());
        let link = directory.path().join("symlink");
        std::os::unix::fs::symlink(&path, &link).unwrap();
        assert!(read_private(&link).is_err());
    }
    #[tokio::test]
    async fn secure_bundle_requires_bound_certificate_and_correct_password() {
        use sha2::{Digest, Sha256};
        use std::fmt::Write;
        let certificate = b"fixture-certificate";
        let mut fingerprint = String::new();
        for byte in Sha256::digest(certificate) {
            write!(&mut fingerprint, "{byte:02x}").unwrap();
        }
        let phc = hash();
        let text = bundle(&phc);
        let slots = Arc::new(Semaphore::new(4));
        assert!(
            compile(
                "version=1\nusers=[]\n",
                true,
                slots.clone(),
                Some(phc.clone())
            )
            .is_err()
        );
        assert!(compile(&text, true, slots.clone(), Some(phc.clone())).is_err());
        let text = format!("{text}cert_sha256='sha256:{fingerprint}'\n");
        let policy = compile(&text, true, slots, Some(phc)).unwrap();
        assert!(
            policy
                .authenticate(certificate, "device", b"fixture-pass")
                .await
                .unwrap()
                .is_some()
        );
        assert!(
            policy
                .authenticate(b"wrong-cert", "device", b"fixture-pass")
                .await
                .unwrap()
                .is_none()
        );
        assert!(
            policy
                .authenticate(certificate, "device", b"wrong-pass")
                .await
                .unwrap()
                .is_none()
        );
        assert!(
            policy
                .authenticate(certificate, "unknown", b"fixture-pass")
                .await
                .unwrap()
                .is_none()
        );
    }
}
