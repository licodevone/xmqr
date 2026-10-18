//! Versioned configuration snapshot. Never mutates the process environment.
use serde::Deserialize;
use std::{
    collections::BTreeMap,
    env,
    ffi::OsString,
    fs::File,
    io::{self, Read},
    path::{Path, PathBuf},
};

const MAX_CONFIG_BYTES: u64 = 64 * 1024;
const KEYS: &[&str] = &[
    "MQTT_MODE",
    "MQTT_BIND",
    "MQTT_WS_BIND",
    "MQTT_WSS_BIND",
    "MQTT_WSS_REMOTE_ENABLED",
    "MQTT_WSS_ALLOWED_ORIGINS",
    "MQTT_STATE_DIR",
    "MQTT_SERVER_CERT",
    "MQTT_SERVER_KEY",
    "MQTT_CLIENT_CA",
    "MQTT_CLIENT_CRL",
    "MQTT_SECURITY_BUNDLE",
    "MQTT_USERS_FILE",
    "MQTT_ACL_FILE",
    "MQTT_MONITOR_ENABLED",
    "MQTT_MONITOR_BIND",
    "MQTT_ADMIN_SOCKET",
    "MQTT_ADMIN_VIEW_TOKEN_FILE",
    "MQTT_ADMIN_OPERATOR_TOKEN_FILE",
    "MQTT_MAX_CONNECTIONS",
    "MQTT_MAX_SESSIONS",
    "MQTT_MAX_RETAINED",
    "MQTT_MAX_SUBSCRIPTIONS",
    "MQTT_MAX_OFFLINE",
    "MQTT_MAX_INFLIGHT",
    "MQTT_SERVER_KEEP_ALIVE_SECONDS",
];

/// Configuration file values overlaid with explicit process variables.
#[derive(Default)]
pub struct Configuration {
    values: BTreeMap<String, OsString>,
    additional_binds: Vec<String>,
    endpoint_policies: Vec<EndpointPolicyFiles>,
}

/// Static user/ACL files for one explicitly named mTLS listener.
#[derive(Clone)]
pub struct EndpointPolicyFiles {
    pub bind: std::net::SocketAddr,
    pub users_file: PathBuf,
    pub acl_file: PathBuf,
}

impl Configuration {
    /// Capture the environment and optionally read `MQTT_CONFIG`.
    /// # Errors
    /// Rejects unreadable, oversized or invalid configuration without echoing it.
    pub fn load() -> io::Result<Self> {
        let overrides = KEYS
            .iter()
            .filter_map(|key| env::var_os(key).map(|value| ((*key).to_owned(), value)))
            .collect();
        Self::load_with(
            env::var_os("MQTT_CONFIG").map(PathBuf::from).as_deref(),
            overrides,
        )
    }

    fn load_with(path: Option<&Path>, overrides: BTreeMap<String, OsString>) -> io::Result<Self> {
        let mut result = Self::default();
        if let Some(path) = path {
            let file = File::open(path).map_err(|_| invalid("cannot open MQTT_CONFIG"))?;
            if !file.metadata()?.is_file() {
                return Err(invalid("MQTT_CONFIG must be a regular file"));
            }
            let mut bytes = Vec::new();
            file.take(MAX_CONFIG_BYTES + 1).read_to_end(&mut bytes)?;
            if bytes.len() as u64 > MAX_CONFIG_BYTES {
                return Err(invalid("MQTT_CONFIG exceeds 64 KiB"));
            }
            let text =
                std::str::from_utf8(&bytes).map_err(|_| invalid("MQTT_CONFIG must be UTF-8"))?;
            result = Self::parse(text, path.parent().unwrap_or(Path::new(".")))?;
        }
        result.values.extend(overrides);
        Ok(result)
    }

    fn parse(text: &str, base: &Path) -> io::Result<Self> {
        let document: Document =
            toml::from_str(text).map_err(|_| invalid("MQTT_CONFIG syntax or schema invalid"))?;
        if document.version != 1 {
            return Err(invalid("unsupported MQTT_CONFIG version"));
        }
        let mut result = Self::default();
        for (name, value) in [
            ("MQTT_MAX_CONNECTIONS", document.limits.max_connections),
            ("MQTT_MAX_SESSIONS", document.limits.max_sessions),
            ("MQTT_MAX_RETAINED", document.limits.max_retained),
            ("MQTT_MAX_SUBSCRIPTIONS", document.limits.max_subscriptions),
            ("MQTT_MAX_OFFLINE", document.limits.max_offline),
            ("MQTT_MAX_INFLIGHT", document.limits.max_inflight),
            (
                "MQTT_SERVER_KEEP_ALIVE_SECONDS",
                document.broker.server_keep_alive_seconds.map(usize::from),
            ),
        ] {
            if let Some(value) = value {
                result
                    .values
                    .insert(name.to_owned(), value.to_string().into());
            }
        }
        insert_string_values(
            &mut result.values,
            [
                ("MQTT_MODE", document.broker.mode),
                ("MQTT_BIND", document.broker.bind),
                ("MQTT_WS_BIND", document.broker.ws_bind),
                ("MQTT_WSS_BIND", document.broker.wss_bind),
                ("MQTT_MONITOR_BIND", document.monitor.bind),
            ],
        );
        insert_bool_values(
            &mut result.values,
            [
                (
                    "MQTT_WSS_REMOTE_ENABLED",
                    document.broker.wss_remote_enabled,
                ),
                ("MQTT_MONITOR_ENABLED", document.monitor.enabled),
            ],
        );
        insert_wss_origins(&mut result.values, document.broker.wss_allowed_origins);
        for (name, value) in [
            ("MQTT_STATE_DIR", document.broker.state_dir),
            ("MQTT_SERVER_CERT", document.tls.server_cert),
            ("MQTT_SERVER_KEY", document.tls.server_key),
            ("MQTT_CLIENT_CA", document.tls.client_ca),
            ("MQTT_CLIENT_CRL", document.tls.client_crl),
            ("MQTT_SECURITY_BUNDLE", document.security.bundle),
            ("MQTT_USERS_FILE", document.security.users_file),
            ("MQTT_ACL_FILE", document.security.acl_file),
            ("MQTT_ADMIN_SOCKET", document.admin.socket),
            ("MQTT_ADMIN_VIEW_TOKEN_FILE", document.admin.view_token_file),
            (
                "MQTT_ADMIN_OPERATOR_TOKEN_FILE",
                document.admin.operator_token_file,
            ),
        ] {
            if let Some(path) = value {
                if path.as_os_str().is_empty() {
                    return Err(invalid("MQTT_CONFIG paths must not be empty"));
                }
                let resolved = if path.is_absolute() {
                    path
                } else {
                    base.join(path)
                };
                result
                    .values
                    .insert(name.to_owned(), resolved.into_os_string());
            }
        }
        result.additional_binds = document.broker.additional_binds;
        if result.additional_binds.len() > 3 {
            return Err(invalid("at most three additional binds are supported"));
        }
        for entry in document.endpoint_policies {
            let bind = entry
                .bind
                .parse()
                .map_err(|_| invalid("invalid endpoint policy bind"))?;
            let resolve = |path: PathBuf| -> io::Result<PathBuf> {
                if path.as_os_str().is_empty() {
                    Err(invalid("endpoint policy path must not be empty"))
                } else if path.is_absolute() {
                    Ok(path)
                } else {
                    Ok(base.join(path))
                }
            };
            result.endpoint_policies.push(EndpointPolicyFiles {
                bind,
                users_file: resolve(entry.users_file)?,
                acl_file: resolve(entry.acl_file)?,
            });
        }
        Ok(result)
    }

    /// Return one static policy for each listener, in bind order, if enabled.
    /// # Errors
    /// Rejects partial, duplicate or foreign endpoint mappings.
    pub fn endpoint_policies(
        &self,
        primary: std::net::SocketAddr,
        additional: &[std::net::SocketAddr],
    ) -> io::Result<Vec<EndpointPolicyFiles>> {
        if self.endpoint_policies.is_empty() {
            return Ok(Vec::new());
        }
        let mut ordered = Vec::with_capacity(1 + additional.len());
        for bind in std::iter::once(&primary).chain(additional) {
            let entries: Vec<_> = self
                .endpoint_policies
                .iter()
                .filter(|p| p.bind == *bind)
                .collect();
            if entries.len() != 1 {
                return Err(invalid(
                    "endpoint policy mapping must cover each listener once",
                ));
            }
            ordered.push(entries[0].clone());
        }
        if ordered.len() != self.endpoint_policies.len() {
            return Err(invalid(
                "endpoint policy mapping contains an unknown listener",
            ));
        }
        Ok(ordered)
    }

    /// Resolve additional mTLS endpoints sharing the primary endpoint's policy.
    /// # Errors
    /// Rejects invalid, duplicate, wildcard or ephemeral additional endpoints.
    pub fn additional_binds(
        &self,
        primary: std::net::SocketAddr,
    ) -> io::Result<Vec<std::net::SocketAddr>> {
        let mut addresses = vec![primary];
        for value in &self.additional_binds {
            let address: std::net::SocketAddr = value
                .parse()
                .map_err(|_| invalid("invalid additional bind"))?;
            if address.port() == 0
                || address.ip().is_unspecified()
                || addresses.contains(&address)
                || (address.port() == primary.port() && primary.ip().is_unspecified())
            {
                return Err(invalid(
                    "additional bind duplicates or overlaps another endpoint",
                ));
            }
            addresses.push(address);
        }
        if addresses.len() > 1 && primary.port() == 0 {
            return Err(invalid(
                "primary bind must have an explicit port with additional binds",
            ));
        }
        Ok(addresses.into_iter().skip(1).collect())
    }

    /// Read a textual value with the same missing/non-Unicode semantics as env.
    /// # Errors
    /// Returns `VarError` for missing or non-Unicode values.
    pub fn var(&self, key: &str) -> Result<String, env::VarError> {
        self.var_os(key)
            .ok_or(env::VarError::NotPresent)?
            .into_string()
            .map_err(env::VarError::NotUnicode)
    }

    /// Read an optional native path or value from the immutable snapshot.
    #[must_use]
    pub fn var_os(&self, key: &str) -> Option<OsString> {
        self.values.get(key).cloned()
    }

    /// Resolve immutable state quotas, honoring explicit environment overrides.
    /// # Errors
    /// Rejects malformed, non-Unicode, zero or excessive quota values.
    pub fn state_limits(&self) -> io::Result<crate::mqtt::StateLimits> {
        let read = |name: &str, default: usize| -> io::Result<usize> {
            match self.var(name) {
                Ok(value) => value
                    .parse()
                    .map_err(|_| invalid("invalid MQTT state quota")),
                Err(env::VarError::NotPresent) => Ok(default),
                Err(env::VarError::NotUnicode(_)) => Err(invalid("invalid MQTT state quota")),
            }
        };
        crate::mqtt::StateLimits::new(
            read("MQTT_MAX_SESSIONS", 64)?,
            read("MQTT_MAX_RETAINED", 256)?,
            read("MQTT_MAX_SUBSCRIPTIONS", 256)?,
            read("MQTT_MAX_OFFLINE", 64)?,
            read("MQTT_MAX_INFLIGHT", 32)?,
        )
    }

    /// Admission ceiling for the executable; independent of durable session quotas.
    /// # Errors
    /// Rejects invalid explicit values instead of falling back to defaults.
    pub fn max_connections(&self) -> io::Result<usize> {
        let value = match self.var("MQTT_MAX_CONNECTIONS") {
            Ok(value) => value
                .parse::<usize>()
                .map_err(|_| invalid("invalid MQTT_MAX_CONNECTIONS"))?,
            Err(env::VarError::NotPresent) => 64,
            Err(env::VarError::NotUnicode(_)) => {
                return Err(invalid("invalid MQTT_MAX_CONNECTIONS"));
            }
        };
        if !(1..=64).contains(&value) {
            return Err(invalid("MQTT_MAX_CONNECTIONS must be between 1 and 64"));
        }
        Ok(value)
    }

    /// Optional MQTT 5 keep-alive ceiling advertised in CONNACK.
    /// # Errors
    /// Rejects zero, malformed and non-Unicode overrides at startup.
    pub fn server_keep_alive_seconds(&self) -> io::Result<Option<u16>> {
        match self.var("MQTT_SERVER_KEEP_ALIVE_SECONDS") {
            Ok(value) => match value.parse::<u16>() {
                Ok(seconds @ 1..=u16::MAX) => Ok(Some(seconds)),
                _ => Err(invalid("MQTT_SERVER_KEEP_ALIVE_SECONDS must be 1..65535")),
            },
            Err(env::VarError::NotPresent) => Ok(None),
            Err(env::VarError::NotUnicode(_)) => {
                Err(invalid("invalid MQTT_SERVER_KEEP_ALIVE_SECONDS"))
            }
        }
    }
}

#[derive(Default, Deserialize)]
#[serde(deny_unknown_fields)]
#[allow(clippy::struct_field_names)] // Field names match the versioned TOML quota contract.
struct Limits {
    max_connections: Option<usize>,
    max_sessions: Option<usize>,
    max_retained: Option<usize>,
    max_subscriptions: Option<usize>,
    max_offline: Option<usize>,
    max_inflight: Option<usize>,
}

#[derive(Default, Deserialize)]
#[serde(deny_unknown_fields)]
struct Broker {
    mode: Option<String>,
    bind: Option<String>,
    ws_bind: Option<String>,
    wss_bind: Option<String>,
    wss_remote_enabled: Option<bool>,
    wss_allowed_origins: Option<Vec<String>>,
    state_dir: Option<PathBuf>,
    server_keep_alive_seconds: Option<u16>,
    #[serde(default)]
    additional_binds: Vec<String>,
}
#[derive(Default, Deserialize)]
#[serde(deny_unknown_fields)]
struct Tls {
    server_cert: Option<PathBuf>,
    server_key: Option<PathBuf>,
    client_ca: Option<PathBuf>,
    client_crl: Option<PathBuf>,
}
#[derive(Default, Deserialize)]
#[serde(deny_unknown_fields)]
struct Security {
    bundle: Option<PathBuf>,
    users_file: Option<PathBuf>,
    acl_file: Option<PathBuf>,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct EndpointPolicyEntry {
    bind: String,
    users_file: PathBuf,
    acl_file: PathBuf,
}
#[derive(Default, Deserialize)]
#[serde(deny_unknown_fields)]
struct Monitor {
    enabled: Option<bool>,
    bind: Option<String>,
}
#[derive(Default, Deserialize)]
#[serde(deny_unknown_fields)]
struct Admin {
    socket: Option<PathBuf>,
    view_token_file: Option<PathBuf>,
    operator_token_file: Option<PathBuf>,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Document {
    version: u32,
    #[serde(default)]
    limits: Limits,
    #[serde(default)]
    broker: Broker,
    #[serde(default)]
    tls: Tls,
    #[serde(default)]
    security: Security,
    #[serde(default)]
    endpoint_policies: Vec<EndpointPolicyEntry>,
    #[serde(default)]
    monitor: Monitor,
    #[serde(default)]
    admin: Admin,
}
fn insert_string_values<const N: usize>(
    values: &mut BTreeMap<String, OsString>,
    entries: [(&'static str, Option<String>); N],
) {
    for (name, value) in entries {
        if let Some(value) = value {
            values.insert(name.to_owned(), value.into());
        }
    }
}

fn insert_bool_values<const N: usize>(
    values: &mut BTreeMap<String, OsString>,
    entries: [(&'static str, Option<bool>); N],
) {
    for (name, value) in entries {
        if let Some(value) = value {
            values.insert(name.to_owned(), value.to_string().into());
        }
    }
}

fn insert_wss_origins(values: &mut BTreeMap<String, OsString>, origins: Option<Vec<String>>) {
    if let Some(origins) = origins {
        values.insert(
            "MQTT_WSS_ALLOWED_ORIGINS".to_owned(),
            origins.join(",").into(),
        );
    }
}

fn invalid(message: &'static str) -> io::Error {
    io::Error::new(io::ErrorKind::InvalidInput, message)
}

#[cfg(test)]
mod tests {
    #[test]
    fn wss_origin_list_toml_and_environment_precedence() {
        let text = "version=1\n[broker]\nwss_bind='127.0.0.1:8443'\nwss_allowed_origins=['https://a.example', 'https://b.example:8443']";
        let config = Configuration::parse(text, Path::new(".")).unwrap();
        assert_eq!(
            config.var("MQTT_WSS_ALLOWED_ORIGINS").unwrap(),
            "https://a.example,https://b.example:8443"
        );
        let mut overridden = config;
        overridden.values.insert(
            "MQTT_WSS_ALLOWED_ORIGINS".to_owned(),
            "https://override.example".into(),
        );
        assert_eq!(
            overridden.var("MQTT_WSS_ALLOWED_ORIGINS").unwrap(),
            "https://override.example"
        );
        assert!(
            Configuration::parse(
                "version=1\n[broker]\nwss_allowed_origins='https://a.example'",
                Path::new(".")
            )
            .is_err()
        );
    }
    #[test]
    fn remote_wss_setting_is_boolean_and_overridable() {
        let text = "version=1\n[broker]\nwss_bind='0.0.0.0:8443'\nwss_remote_enabled=true";
        let config = Configuration::parse(text, Path::new(".")).unwrap();
        assert_eq!(config.var("MQTT_WSS_BIND").unwrap(), "0.0.0.0:8443");
        assert_eq!(config.var("MQTT_WSS_REMOTE_ENABLED").unwrap(), "true");
        for invalid in ["'true'", "1", "'secret'"] {
            assert!(
                Configuration::parse(
                    &format!("version=1\n[broker]\nwss_remote_enabled={invalid}"),
                    Path::new(".")
                )
                .is_err()
            );
        }
        let mut overridden = Configuration::parse(text, Path::new(".")).unwrap();
        overridden
            .values
            .insert("MQTT_WSS_REMOTE_ENABLED".to_owned(), "false".into());
        assert_eq!(overridden.var("MQTT_WSS_REMOTE_ENABLED").unwrap(), "false");
    }

    #[test]
    fn server_keep_alive_is_optional_bounded_and_overridable() {
        assert_eq!(
            Configuration::default()
                .server_keep_alive_seconds()
                .unwrap(),
            None
        );
        for seconds in [1, u16::MAX] {
            let config = Configuration::parse(
                &format!("version=1\n[broker]\nserver_keep_alive_seconds={seconds}"),
                Path::new("."),
            )
            .unwrap();
            assert_eq!(config.server_keep_alive_seconds().unwrap(), Some(seconds));
        }
        let mut config = Configuration::parse(
            "version=1\n[broker]\nserver_keep_alive_seconds=30",
            Path::new("."),
        )
        .unwrap();
        config
            .values
            .insert("MQTT_SERVER_KEEP_ALIVE_SECONDS".into(), "2".into());
        assert_eq!(config.server_keep_alive_seconds().unwrap(), Some(2));
        for value in ["0", "65536", "-1", "bad", ""] {
            config
                .values
                .insert("MQTT_SERVER_KEEP_ALIVE_SECONDS".into(), value.into());
            assert!(config.server_keep_alive_seconds().is_err());
        }
        assert!(
            Configuration::parse(
                "version=1\n[broker]\nserver_keep_alive_seconds=65536",
                Path::new("."),
            )
            .is_err()
        );
    }

    #[test]
    fn additional_endpoints_validate_without_changing_defaults() {
        let primary = "127.0.0.1:8883".parse().unwrap();
        assert_eq!(
            Configuration::default().additional_binds(primary).unwrap(),
            Vec::<std::net::SocketAddr>::new()
        );
        let config = Configuration::parse(
            "version=1\n[broker]\nadditional_binds=['127.0.0.1:8884']",
            Path::new("."),
        )
        .unwrap();
        assert_eq!(
            config.additional_binds(primary).unwrap(),
            vec!["127.0.0.1:8884".parse::<std::net::SocketAddr>().unwrap()]
        );
        for extra in ["127.0.0.1:8883", "127.0.0.1:0", "0.0.0.0:8884", "invalid"] {
            let text = format!("version=1\n[broker]\nadditional_binds=['{extra}']");
            assert!(
                Configuration::parse(&text, Path::new("."))
                    .unwrap()
                    .additional_binds(primary)
                    .is_err()
            );
        }
        for entries in [
            "'127.0.0.1:8884','127.0.0.1:8884'",
            "'127.0.0.1:1','127.0.0.1:2','127.0.0.1:3','127.0.0.1:4'",
        ] {
            let text = format!("version=1\n[broker]\nadditional_binds=[{entries}]");
            assert!(
                Configuration::parse(&text, Path::new("."))
                    .and_then(|config| config.additional_binds(primary))
                    .is_err()
            );
        }
    }

    #[test]
    fn state_quota_defaults_precedence_and_invalid_values() {
        assert_eq!(
            Configuration::default().state_limits().unwrap(),
            crate::mqtt::StateLimits::default()
        );
        for (field, key, ceiling) in [
            ("max_sessions", "MQTT_MAX_SESSIONS", 64),
            ("max_retained", "MQTT_MAX_RETAINED", 256),
            ("max_subscriptions", "MQTT_MAX_SUBSCRIPTIONS", 256),
            ("max_offline", "MQTT_MAX_OFFLINE", 64),
            ("max_inflight", "MQTT_MAX_INFLIGHT", 32),
        ] {
            let text = format!("version=1\n[limits]\n{field}=1");
            let from_file = Configuration::parse(&text, Path::new(".")).unwrap();
            assert!(from_file.state_limits().is_ok());
            let mut overridden = Configuration::parse(&text, Path::new(".")).unwrap();
            overridden
                .values
                .insert(key.into(), ceiling.to_string().into());
            assert_eq!(
                overridden.state_limits().unwrap(),
                crate::mqtt::StateLimits::default()
            );
            for invalid_value in [
                "0".to_owned(),
                (ceiling + 1).to_string(),
                "-1".into(),
                "bad".into(),
                String::new(),
                "18446744073709551616".into(),
            ] {
                overridden.values.insert(key.into(), invalid_value.into());
                assert!(overridden.state_limits().is_err());
            }
            for bad_type in ["-1", "true", "'1'", "1.5"] {
                assert!(
                    Configuration::parse(
                        &format!("version=1\n[limits]\n{field}={bad_type}"),
                        Path::new(".")
                    )
                    .is_err()
                );
            }
        }
    }

    #[cfg(unix)]
    #[test]
    fn non_unicode_state_quotas_are_rejected() {
        use std::os::unix::ffi::OsStringExt;
        for name in [
            "MQTT_MAX_SESSIONS",
            "MQTT_MAX_RETAINED",
            "MQTT_MAX_SUBSCRIPTIONS",
            "MQTT_MAX_OFFLINE",
            "MQTT_MAX_INFLIGHT",
        ] {
            let config = Configuration {
                values: BTreeMap::from([(name.to_owned(), OsString::from_vec(vec![255]))]),
                ..Configuration::default()
            };
            assert!(config.state_limits().is_err());
        }
    }

    #[test]
    fn connection_limit_default_boundaries_and_override() {
        assert_eq!(Configuration::default().max_connections().unwrap(), 64);
        let directory = tempfile::tempdir().unwrap();
        let path = directory.path().join("broker.toml");
        std::fs::write(&path, "version=1\n[limits]\nmax_connections=1").unwrap();
        let config = Configuration::load_with(Some(&path), BTreeMap::new()).unwrap();
        assert_eq!(config.max_connections().unwrap(), 1);
        for value in ["0", "65", "-1", "bad", "", "18446744073709551616"] {
            let config = Configuration::load_with(
                Some(&path),
                BTreeMap::from([("MQTT_MAX_CONNECTIONS".to_owned(), value.into())]),
            )
            .unwrap();
            assert!(config.max_connections().is_err());
        }
        let config = Configuration::load_with(
            Some(&path),
            BTreeMap::from([("MQTT_MAX_CONNECTIONS".to_owned(), "64".into())]),
        )
        .unwrap();
        assert_eq!(config.max_connections().unwrap(), 64);
        for value in ["-1", "'1'", "true"] {
            assert!(
                Configuration::parse(
                    &format!("version=1\n[limits]\nmax_connections={value}"),
                    Path::new(".")
                )
                .is_err()
            );
        }
    }

    #[cfg(unix)]
    #[test]
    fn non_unicode_connection_limit_is_rejected() {
        use std::os::unix::ffi::OsStringExt;
        let config = Configuration::load_with(
            None,
            BTreeMap::from([(
                "MQTT_MAX_CONNECTIONS".to_owned(),
                OsString::from_vec(vec![255]),
            )]),
        )
        .unwrap();
        assert!(config.max_connections().is_err());
    }

    use super::*;
    #[test]
    fn strict_schema_and_redacted_errors() {
        for text in [
            "version=2",
            "version=1\nunknown='secret'",
            "version=1\n[tls]\npassword='secret'",
            "version=1\n[monitor]\nenabled='true'",
            "version=1\n[broker]\nstate_dir=''",
            "secret invalid toml",
        ] {
            let error = Configuration::parse(text, Path::new("base")).err().unwrap();
            assert!(!error.to_string().contains("secret"));
        }
    }
    #[test]
    fn file_paths_resolve_but_environment_paths_keep_legacy_semantics() {
        let directory = tempfile::tempdir().unwrap();
        let path = directory.path().join("broker.toml");
        std::fs::write(&path, "version=1\n[broker]\nstate_dir='state'\nbind='127.0.0.1:1883'\n[monitor]\nenabled=false").unwrap();
        let config = Configuration::load_with(Some(&path), BTreeMap::new()).unwrap();
        assert_eq!(
            config.var_os("MQTT_STATE_DIR").unwrap(),
            directory.path().join("state")
        );
        let overrides = BTreeMap::from([
            (
                "MQTT_STATE_DIR".to_owned(),
                OsString::from("legacy-relative"),
            ),
            ("MQTT_BIND".to_owned(), OsString::from("invalid")),
        ]);
        let config = Configuration::load_with(Some(&path), overrides).unwrap();
        assert_eq!(config.var("MQTT_STATE_DIR").unwrap(), "legacy-relative");
        assert_eq!(config.var("MQTT_BIND").unwrap(), "invalid");
    }
    #[test]
    fn legacy_missing_and_oversized_configuration() {
        let config = Configuration::load_with(None, BTreeMap::new()).unwrap();
        assert!(matches!(
            config.var("MQTT_MODE"),
            Err(env::VarError::NotPresent)
        ));
        let directory = tempfile::tempdir().unwrap();
        let path = directory.path().join("large.toml");
        std::fs::write(
            &path,
            vec![b' '; usize::try_from(MAX_CONFIG_BYTES).unwrap() + 1],
        )
        .unwrap();
        assert!(Configuration::load_with(Some(&path), BTreeMap::new()).is_err());
    }
}
