//! Local MQTT 3.1.1 authentication and topic authorization.
//!
//! A successful TLS handshake is necessary but insufficient: each MQTT CONNECT
//! must also present a configured username/password and the matching client
//! certificate. Access to topics is denied unless explicitly granted.

use std::{
    collections::{HashMap, HashSet},
    fs::File,
    io::{self, Read},
    path::Path,
    sync::Arc,
};

use argon2::{
    Algorithm, Argon2, Params, Version,
    password_hash::{PasswordHash, PasswordHasher, PasswordVerifier, SaltString},
};
use serde::Deserialize;
use sha2::{Digest, Sha256};
use subtle::ConstantTimeEq;
use thiserror::Error;
use tokio::sync::Semaphore;
use zeroize::Zeroizing;

use crate::mqtt::topic::{matches_filter, valid_topic_filter, valid_topic_name};

const MAX_CONFIG_BYTES: u64 = 1_048_576;
const MAX_USERS: usize = 1_024;
const MAX_RULES: usize = 1_024;
const MAX_TOPICS_PER_RULE: usize = 256;
const MAX_USERNAME_BYTES: usize = 128;
const MAX_PASSWORD_BYTES: usize = 1_024;
const MAX_CERT_DER_BYTES: usize = 65_536;
const MAX_PARALLEL_HASHES: usize = 4;
const ARGON_MEMORY_KIB: u32 = 19_456;
const ARGON_ITERATIONS: u32 = 2;
const ARGON_LANES: u32 = 1;

/// A non-client-facing authentication/configuration error. Never put its
/// detail into an MQTT packet or log credentials alongside it.
#[derive(Debug, Error)]
pub enum AuthError {
    #[error("unable to read authentication configuration")]
    Io(#[from] io::Error),
    #[error("invalid authentication configuration: {0}")]
    Config(&'static str),
    #[error("authentication service busy")]
    Busy,
    #[error("authentication worker failed")]
    Worker,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct UsersFile {
    users: Vec<UserRecord>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct UserRecord {
    username: String,
    #[serde(default)]
    cert_sha256: Option<String>,
    password_hash: String,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct AclFile {
    rules: Vec<AclRule>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct AclRule {
    username: String,
    #[serde(default)]
    publish: Vec<String>,
    #[serde(default)]
    subscribe: Vec<String>,
}

struct User {
    cert_fingerprint: Option<[u8; 32]>,
    password_hash: String,
}

struct Grants {
    publish: HashSet<String>,
    subscribe: HashSet<String>,
}

struct Inner {
    users: HashMap<String, User>,
    acl: HashMap<String, Grants>,
    dummy_hash: String,
    hash_slots: Arc<Semaphore>,
}

/// Immutable, shareable authorization policy. `authenticate` reserves one of
/// four Argon2 worker slots before scheduling a blocking hash. If all slots
/// are occupied it fails closed, so the runtime and memory use stay bounded.
#[derive(Clone)]
pub struct AuthPolicy(Arc<Inner>);

const OPEN_LAB_PRINCIPAL: &str = "__open_lab__";

/// Connection-level access policy selected once at broker startup.
///
/// `OpenLab` is intentionally not configurable with users or ACLs and accepts
/// only anonymous MQTT CONNECT packets. The listener separately guarantees
/// that this mode can bind only to a loopback address.
#[derive(Clone)]
pub enum AccessPolicy {
    Secure(AuthPolicy),
    OpenLab,
    PasswordLab(AuthPolicy),
    AclLab(AuthPolicy),
}

impl AccessPolicy {
    #[must_use]
    pub const fn open_lab() -> Self {
        Self::OpenLab
    }

    #[must_use]
    pub fn secure(policy: AuthPolicy) -> Self {
        Self::Secure(policy)
    }

    #[must_use]
    pub fn password_lab(policy: AuthPolicy) -> Self {
        Self::PasswordLab(policy)
    }

    #[must_use]
    pub fn acl_lab(policy: AuthPolicy) -> Self {
        Self::AclLab(policy)
    }

    /// Authenticate a CONNECT according to the startup-selected policy.
    ///
    /// # Errors
    /// Forwards bounded authentication worker errors from the secure policy.
    pub async fn authenticate(
        &self,
        cert_der: Option<&[u8]>,
        username: Option<&str>,
        password: Option<&[u8]>,
    ) -> Result<Option<String>, AuthError> {
        match self {
            Self::Secure(policy) => {
                let (Some(cert_der), Some(username), Some(password)) =
                    (cert_der, username, password)
                else {
                    return Ok(None);
                };
                policy.authenticate(cert_der, username, password).await
            }
            Self::OpenLab => Ok(
                (cert_der.is_none() && username.is_none() && password.is_none())
                    .then(|| OPEN_LAB_PRINCIPAL.to_owned()),
            ),
            Self::PasswordLab(policy) | Self::AclLab(policy) => {
                if cert_der.is_some() {
                    return Ok(None);
                }
                let (Some(username), Some(password)) = (username, password) else {
                    return Ok(None);
                };
                policy.authenticate_password(username, password).await
            }
        }
    }

    #[must_use]
    pub fn allowed_publish(&self, principal: &str, topic: &str) -> bool {
        match self {
            Self::OpenLab => principal == OPEN_LAB_PRINCIPAL && valid_topic_name(topic),
            Self::PasswordLab(policy) => {
                policy.contains_principal(principal) && valid_topic_name(topic)
            }
            Self::Secure(policy) | Self::AclLab(policy) => policy.allowed_publish(principal, topic),
        }
    }

    #[must_use]
    pub fn allowed_subscribe(&self, principal: &str, filter: &str) -> bool {
        match self {
            Self::OpenLab => principal == OPEN_LAB_PRINCIPAL && valid_topic_filter(filter),
            Self::PasswordLab(policy) => {
                policy.contains_principal(principal) && valid_topic_filter(filter)
            }
            Self::Secure(policy) | Self::AclLab(policy) => {
                policy.allowed_subscribe(principal, filter)
            }
        }
    }

    /// Revalidate a concrete publication topic immediately before delivery.
    #[must_use]
    pub fn allowed_delivery(&self, principal: &str, topic: &str) -> bool {
        match self {
            Self::Secure(policy) | Self::AclLab(policy) => {
                policy.allowed_delivery(principal, topic)
            }
            Self::OpenLab => principal == OPEN_LAB_PRINCIPAL && valid_topic_name(topic),
            Self::PasswordLab(policy) => {
                policy.contains_principal(principal) && valid_topic_name(topic)
            }
        }
    }

    #[must_use]
    pub fn contains_principal(&self, principal: &str) -> bool {
        match self {
            Self::Secure(policy) => policy.contains_principal(principal),
            Self::OpenLab => principal == OPEN_LAB_PRINCIPAL,
            Self::PasswordLab(policy) | Self::AclLab(policy) => {
                policy.contains_principal(principal)
            }
        }
    }
}

impl AuthPolicy {
    /// Load both local TOML files. Any malformed, missing, duplicate or
    /// oversized policy fails broker startup instead of silently weakening it.
    ///
    /// # Errors
    /// Returns [`AuthError`] for unreadable files, malformed hashes, duplicate
    /// identities or invalid ACL rules.
    pub fn load(users_path: &Path, acl_path: &Path) -> Result<Self, AuthError> {
        Self::load_internal(users_path, Some(acl_path), true)
    }

    /// Load password identities for a loopback lab without topic ACLs.
    ///
    /// # Errors
    /// Returns [`AuthError`] for unreadable or invalid user configuration.
    pub fn load_passwords(users_path: &Path) -> Result<Self, AuthError> {
        Self::load_internal(users_path, None, false)
    }

    /// Load password identities plus exact-topic ACLs for a loopback lab.
    ///
    /// # Errors
    /// Returns [`AuthError`] for unreadable or invalid user/ACL configuration.
    pub fn load_passwords_with_acl(users_path: &Path, acl_path: &Path) -> Result<Self, AuthError> {
        Self::load_internal(users_path, Some(acl_path), false)
    }

    fn load_internal(
        users_path: &Path,
        acl_path: Option<&Path>,
        require_certificate: bool,
    ) -> Result<Self, AuthError> {
        let users_text = read_bounded(users_path)?;
        let users_file: UsersFile =
            toml::from_str(&users_text).map_err(|_| AuthError::Config("users TOML syntax"))?;
        let acl_file = acl_path
            .map(|path| {
                let text = read_bounded(path)?;
                toml::from_str::<AclFile>(&text).map_err(|_| AuthError::Config("ACL TOML syntax"))
            })
            .transpose()?
            .unwrap_or(AclFile { rules: Vec::new() });

        if (require_certificate && users_file.users.is_empty())
            || users_file.users.len() > MAX_USERS
        {
            return Err(AuthError::Config("user count is outside allowed range"));
        }
        if acl_file.rules.len() > MAX_RULES {
            return Err(AuthError::Config("ACL rule count exceeds limit"));
        }

        let mut users = HashMap::with_capacity(users_file.users.len());
        let mut fingerprints = HashSet::with_capacity(users_file.users.len());
        for record in users_file.users {
            if !valid_username(&record.username) {
                return Err(AuthError::Config("invalid username"));
            }
            let cert_fingerprint = record
                .cert_sha256
                .as_deref()
                .map(parse_fingerprint)
                .transpose()?;
            if require_certificate && cert_fingerprint.is_none() {
                return Err(AuthError::Config(
                    "secure-mtls user requires certificate fingerprint",
                ));
            }
            if let Some(fingerprint) = cert_fingerprint
                && !fingerprints.insert(fingerprint)
            {
                return Err(AuthError::Config(
                    "one certificate cannot belong to multiple users",
                ));
            }
            validate_phc(&record.password_hash)?;
            if users
                .insert(
                    record.username,
                    User {
                        cert_fingerprint,
                        password_hash: record.password_hash,
                    },
                )
                .is_some()
            {
                return Err(AuthError::Config("duplicate username"));
            }
        }

        let mut acl = HashMap::with_capacity(acl_file.rules.len());
        for rule in acl_file.rules {
            if !users.contains_key(&rule.username) {
                return Err(AuthError::Config("ACL references unknown user"));
            }
            if rule.publish.len() > MAX_TOPICS_PER_RULE
                || rule.subscribe.len() > MAX_TOPICS_PER_RULE
            {
                return Err(AuthError::Config("too many topics in ACL rule"));
            }
            if rule.publish.iter().any(|topic| !valid_topic_name(topic)) {
                return Err(AuthError::Config(
                    "ACL topic must be an exact MQTT topic name",
                ));
            }
            if rule
                .subscribe
                .iter()
                .any(|filter| !valid_topic_filter(filter))
            {
                return Err(AuthError::Config("ACL subscription filter is invalid"));
            }
            let grants = Grants {
                publish: rule.publish.into_iter().collect(),
                subscribe: rule.subscribe.into_iter().collect(),
            };
            if acl.insert(rule.username, grants).is_some() {
                return Err(AuthError::Config("duplicate ACL rule for user"));
            }
        }

        // Unknown usernames perform one real Argon2 check against a fixed,
        // valid dummy hash, avoiding the obvious fast-fail enumeration path.
        let dummy_salt = SaltString::encode_b64(b"mqtt-broker-dummy")
            .map_err(|_| AuthError::Config("unable to initialize auth"))?;
        let dummy_hash = argon2_context()
            .hash_password(b"not-a-user-secret", &dummy_salt)
            .map_err(|_| AuthError::Config("unable to initialize auth"))?
            .to_string();

        Ok(Self(Arc::new(Inner {
            users,
            acl,
            dummy_hash,
            hash_slots: Arc::new(Semaphore::new(MAX_PARALLEL_HASHES)),
        })))
    }

    /// Return the authenticated principal (username) or `None` for any
    /// credential mismatch. `cert_der` must be the DER leaf certificate
    /// already validated by the mTLS transport. Never trust a certificate
    /// fingerprint supplied inside an MQTT packet.
    ///
    /// # Errors
    /// Returns [`AuthError::Busy`] if all bounded hash workers are occupied,
    /// or [`AuthError::Worker`] if a blocking verification task fails.
    pub async fn authenticate(
        &self,
        cert_der: &[u8],
        username: &str,
        password: &[u8],
    ) -> Result<Option<String>, AuthError> {
        if cert_der.is_empty() || cert_der.len() > MAX_CERT_DER_BYTES {
            return Ok(None);
        }
        let fingerprint: [u8; 32] = Sha256::digest(cert_der).into();
        let cert_matches = self
            .0
            .users
            .get(username)
            .and_then(|user| user.cert_fingerprint.as_ref())
            .is_some_and(|configured| bool::from(configured.ct_eq(&fingerprint)));
        let password_matches = self.verify_password(username, password).await?;
        Ok((cert_matches && password_matches).then(|| username.to_owned()))
    }

    /// Authenticate with username/password only. Intended solely for the
    /// loopback-restricted password and ACL teaching modes.
    ///
    /// # Errors
    /// Returns [`AuthError::Busy`] if all bounded hash workers are occupied,
    /// or [`AuthError::Worker`] if a blocking verification task fails.
    pub async fn authenticate_password(
        &self,
        username: &str,
        password: &[u8],
    ) -> Result<Option<String>, AuthError> {
        let matches = self.verify_password(username, password).await?;
        Ok(matches.then(|| username.to_owned()))
    }

    async fn verify_password(&self, username: &str, password: &[u8]) -> Result<bool, AuthError> {
        if !valid_username(username) || password.is_empty() || password.len() > MAX_PASSWORD_BYTES {
            return Ok(false);
        }
        let permit = self
            .0
            .hash_slots
            .clone()
            .try_acquire_owned()
            .map_err(|_| AuthError::Busy)?;
        let (hash, user_exists) = self.0.users.get(username).map_or_else(
            || (self.0.dummy_hash.clone(), false),
            |user| (user.password_hash.clone(), true),
        );
        let secret = Zeroizing::new(password.to_vec());
        let password_matches = tokio::task::spawn_blocking(move || {
            let _permit = permit;
            let Ok(phc) = PasswordHash::new(&hash) else {
                return false;
            };
            argon2_context().verify_password(&secret, &phc).is_ok()
        })
        .await
        .map_err(|_| AuthError::Worker)?;
        Ok(user_exists && password_matches)
    }

    /// Permit a PUBLISH only for an authenticated principal with an exact
    /// matching topic grant. No wildcard or prefix interpretation occurs.
    #[must_use]
    pub fn allowed_publish(&self, principal: &str, topic: &str) -> bool {
        self.0
            .acl
            .get(principal)
            .is_some_and(|rule| rule.publish.contains(topic))
    }

    /// Permit a SUBSCRIBE only when the requested filter is explicitly present
    /// in the principal's ACL. Exact grants do not imply broader wildcards.
    #[must_use]
    pub fn allowed_subscribe(&self, principal: &str, topic: &str) -> bool {
        self.0
            .acl
            .get(principal)
            .is_some_and(|rule| rule.subscribe.contains(topic))
    }

    /// Permit delivery when a configured subscription grant matches the
    /// concrete publication topic.
    #[must_use]
    pub fn allowed_delivery(&self, principal: &str, topic: &str) -> bool {
        valid_topic_name(topic)
            && self.0.acl.get(principal).is_some_and(|rule| {
                rule.subscribe
                    .iter()
                    .any(|filter| matches_filter(filter, topic))
            })
    }

    /// Whether a principal is still configured; used to remove orphaned
    /// persistent sessions during startup after an administrator revokes it.
    #[must_use]
    pub fn contains_principal(&self, principal: &str) -> bool {
        self.0.users.contains_key(principal)
    }
}

fn read_bounded(path: &Path) -> Result<String, AuthError> {
    let file = File::open(path)?;
    if !file.metadata()?.is_file() {
        return Err(AuthError::Config(
            "configuration path is not a regular file",
        ));
    }
    let mut text = String::new();
    file.take(MAX_CONFIG_BYTES + 1).read_to_string(&mut text)?;
    if text.len() as u64 > MAX_CONFIG_BYTES {
        return Err(AuthError::Config("configuration file exceeds size limit"));
    }
    Ok(text)
}

fn valid_username(name: &str) -> bool {
    !name.is_empty() && name.len() <= MAX_USERNAME_BYTES && !name.chars().any(char::is_control)
}

fn parse_fingerprint(value: &str) -> Result<[u8; 32], AuthError> {
    let hex = value.strip_prefix("sha256:").ok_or(AuthError::Config(
        "certificate fingerprint must use sha256: prefix",
    ))?;
    if hex.len() != 64 {
        return Err(AuthError::Config(
            "certificate fingerprint must be 32 bytes",
        ));
    }
    let mut bytes = [0u8; 32];
    for (index, byte) in bytes.iter_mut().enumerate() {
        let chunk = hex
            .as_bytes()
            .get(index * 2..index * 2 + 2)
            .ok_or(AuthError::Config("invalid certificate fingerprint"))?;
        let pair = std::str::from_utf8(chunk)
            .map_err(|_| AuthError::Config("invalid certificate fingerprint"))?;
        *byte = u8::from_str_radix(pair, 16)
            .map_err(|_| AuthError::Config("invalid certificate fingerprint"))?;
    }
    Ok(bytes)
}

fn validate_phc(value: &str) -> Result<(), AuthError> {
    if value.len() > 256 {
        return Err(AuthError::Config("password hash exceeds size limit"));
    }
    let phc = PasswordHash::new(value).map_err(|_| AuthError::Config("invalid password hash"))?;
    if phc.algorithm.as_str() != "argon2id"
        || phc.version != Some(19)
        || phc.salt.is_none()
        || phc.hash.is_none()
    {
        return Err(AuthError::Config(
            "only Argon2id v19 password hashes are accepted",
        ));
    }
    let params =
        Params::try_from(&phc).map_err(|_| AuthError::Config("invalid Argon2 parameters"))?;
    if phc
        .hash
        .as_ref()
        .is_none_or(|hash| hash.as_bytes().len() != 32)
    {
        return Err(AuthError::Config("password hash output must be 32 bytes"));
    }
    let mut decoded_salt = [0u8; 32];
    let salt_len = phc
        .salt
        .as_ref()
        .expect("checked above")
        .decode_b64(&mut decoded_salt)
        .map_err(|_| AuthError::Config("invalid password salt"))?
        .len();
    if !(16..=32).contains(&salt_len) {
        return Err(AuthError::Config("password salt must be 16 to 32 bytes"));
    }
    if params.m_cost() != ARGON_MEMORY_KIB
        || params.t_cost() != ARGON_ITERATIONS
        || params.p_cost() != ARGON_LANES
        || params.output_len().unwrap_or(32) != 32
        || !params.keyid().is_empty()
        || !params.data().is_empty()
    {
        return Err(AuthError::Config(
            "password hash parameters do not match the bounded profile",
        ));
    }
    Ok(())
}

/// The sole supported password-hash profile, shared by the loader and admin CLI.
///
/// # Panics
/// Cannot panic with the hard-coded, valid Argon2id parameter tuple.
#[must_use]
pub fn argon2_context() -> Argon2<'static> {
    let params = Params::new(ARGON_MEMORY_KIB, ARGON_ITERATIONS, ARGON_LANES, None)
        .expect("fixed Argon2 profile is valid");
    Argon2::new(Algorithm::Argon2id, Version::V0x13, params)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::{fmt::Write, fs};
    use tempfile::TempDir;

    fn fixtures() -> (TempDir, AuthPolicy, Vec<u8>) {
        let dir = tempfile::tempdir().unwrap();
        let cert = b"valid-leaf-der".to_vec();
        let fingerprint = Sha256::digest(&cert);
        let fingerprint = fingerprint.iter().fold(String::new(), |mut out, byte| {
            write!(&mut out, "{byte:02x}").unwrap();
            out
        });
        let salt = SaltString::encode_b64(b"sixteen-byte-salt").unwrap();
        let hash = argon2_context()
            .hash_password(b"correct-pass", &salt)
            .unwrap()
            .to_string();
        fs::write(dir.path().join("users.toml"), format!(
            "[[users]]\nusername = 'sensor1'\ncert_sha256 = 'sha256:{fingerprint}'\npassword_hash = '{hash}'\n"
        )).unwrap();
        fs::write(dir.path().join("acl.toml"),
            "[[rules]]\nusername = 'sensor1'\npublish = ['sensors/one']\nsubscribe = ['commands/one']\n").unwrap();
        let policy =
            AuthPolicy::load(&dir.path().join("users.toml"), &dir.path().join("acl.toml")).unwrap();
        (dir, policy, cert)
    }

    #[tokio::test]
    async fn accepts_only_full_three_factor_match() {
        let (_dir, policy, cert) = fixtures();
        assert_eq!(
            policy
                .authenticate(&cert, "sensor1", b"correct-pass")
                .await
                .unwrap(),
            Some("sensor1".into())
        );
        assert_eq!(
            policy
                .authenticate(&cert, "sensor1", b"wrong-pass")
                .await
                .unwrap(),
            None
        );
        assert_eq!(
            policy
                .authenticate(b"other-leaf", "sensor1", b"correct-pass")
                .await
                .unwrap(),
            None
        );
        assert_eq!(
            policy
                .authenticate(&cert, "unknown", b"correct-pass")
                .await
                .unwrap(),
            None
        );
        assert_eq!(
            policy
                .authenticate(&[], "sensor1", b"correct-pass")
                .await
                .unwrap(),
            None
        );
        assert_eq!(
            policy
                .authenticate(&cert, "sensor1", &[b'x'; MAX_PASSWORD_BYTES + 1])
                .await
                .unwrap(),
            None
        );
    }

    #[tokio::test]
    async fn bounded_hash_workers_fail_closed() {
        let (_dir, policy, cert) = fixtures();
        let mut permits = Vec::new();
        for _ in 0..MAX_PARALLEL_HASHES {
            permits.push(policy.0.hash_slots.clone().try_acquire_owned().unwrap());
        }
        assert!(matches!(
            policy.authenticate(&cert, "sensor1", b"correct-pass").await,
            Err(AuthError::Busy)
        ));
        drop(permits);
        assert!(
            policy
                .authenticate(&cert, "sensor1", b"correct-pass")
                .await
                .unwrap()
                .is_some()
        );
    }

    #[test]
    fn acl_is_explicit_and_denies_by_default() {
        let (dir, policy, _) = fixtures();
        assert!(policy.allowed_publish("sensor1", "sensors/one"));
        assert!(policy.allowed_subscribe("sensor1", "commands/one"));
        assert!(policy.allowed_delivery("sensor1", "commands/one"));
        assert!(!policy.allowed_publish("sensor1", "sensors/one/extra"));
        assert!(!policy.allowed_publish("sensor1", "commands/one"));
        assert!(!policy.allowed_subscribe("sensor1", "commands/+"));
        assert!(!policy.allowed_subscribe("unknown", "commands/one"));

        fs::write(
            dir.path().join("acl.toml"),
            "[[rules]]\nusername = 'sensor1'\npublish = ['sensors/one']\nsubscribe = ['commands/+']\n",
        )
        .unwrap();
        let wildcard =
            AuthPolicy::load(&dir.path().join("users.toml"), &dir.path().join("acl.toml")).unwrap();
        assert!(wildcard.allowed_subscribe("sensor1", "commands/+"));
        assert!(!wildcard.allowed_subscribe("sensor1", "commands/one"));
        assert!(wildcard.allowed_delivery("sensor1", "commands/one"));
        assert!(!wildcard.allowed_delivery("sensor1", "commands/one/extra"));
    }

    #[tokio::test]
    async fn open_lab_accepts_only_anonymous_connections() {
        let policy = AccessPolicy::open_lab();
        let principal = policy
            .authenticate(None, None, None)
            .await
            .unwrap()
            .expect("anonymous lab connection");
        assert!(policy.allowed_publish(&principal, "test/message"));
        assert!(policy.allowed_subscribe(&principal, "test/message"));
        assert!(
            policy
                .authenticate(None, Some("user"), Some(b"password"))
                .await
                .unwrap()
                .is_none()
        );
        assert!(policy.allowed_subscribe(&principal, "test/+"));
        assert!(policy.allowed_delivery(&principal, "test/one"));
        assert!(!policy.allowed_publish(&principal, "test/+"));
    }

    #[tokio::test]
    async fn password_lab_accepts_users_without_certificates() {
        let directory = tempfile::tempdir().unwrap();
        let salt = SaltString::encode_b64(b"sixteen-byte-salt").unwrap();
        let hash = argon2_context()
            .hash_password(b"correct-pass", &salt)
            .unwrap()
            .to_string();
        let users = directory.path().join("users.toml");
        let acl = directory.path().join("acl.toml");
        fs::write(
            &users,
            format!("[[users]]\nusername = 'student'\npassword_hash = '{hash}'\n"),
        )
        .unwrap();
        fs::write(
            &acl,
            "[[rules]]\nusername = 'student'\npublish = ['allowed/topic']\nsubscribe = ['allowed/topic']\n",
        )
        .unwrap();

        assert!(AuthPolicy::load(&users, &acl).is_err());

        let passwords = AuthPolicy::load_passwords(&users).unwrap();
        let principal = passwords
            .authenticate_password("student", b"correct-pass")
            .await
            .unwrap()
            .unwrap();
        let password_lab = AccessPolicy::password_lab(passwords);
        assert!(password_lab.allowed_publish(&principal, "any/exact/topic"));
        assert!(!password_lab.allowed_publish("unknown", "any/exact/topic"));

        let acl_lab =
            AccessPolicy::acl_lab(AuthPolicy::load_passwords_with_acl(&users, &acl).unwrap());
        assert!(acl_lab.allowed_publish(&principal, "allowed/topic"));
        assert!(!acl_lab.allowed_publish(&principal, "denied/topic"));
        assert!(
            acl_lab
                .authenticate(None, Some("student"), Some(b"wrong-pass"))
                .await
                .unwrap()
                .is_none()
        );
    }

    #[test]
    fn rejects_bad_or_unbounded_config() {
        let (dir, _, _) = fixtures();
        let users = dir.path().join("users.toml");
        let acl = dir.path().join("acl.toml");
        let original = fs::read_to_string(&users).unwrap();
        fs::write(&users, original.replace("m=19456", "m=999999999")).unwrap();
        assert!(AuthPolicy::load(&users, &acl).is_err());
        fs::write(&users, original).unwrap();
        fs::write(
            &acl,
            "[[rules]]\nusername = 'sensor1'\npublish = ['sensors/+']\n",
        )
        .unwrap();
        assert!(AuthPolicy::load(&users, &acl).is_err());
    }
}
