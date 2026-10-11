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
    "MQTT_MAX_CONNECTIONS",
];

/// Configuration file values overlaid with explicit process variables.
#[derive(Default)]
pub struct Configuration {
    values: BTreeMap<String, OsString>,
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
        if let Some(value) = document.limits.max_connections {
            result
                .values
                .insert("MQTT_MAX_CONNECTIONS".to_owned(), value.to_string().into());
        }
        for (name, value) in [
            ("MQTT_MODE", document.broker.mode),
            ("MQTT_BIND", document.broker.bind),
            ("MQTT_MONITOR_BIND", document.monitor.bind),
        ] {
            if let Some(value) = value {
                result.values.insert(name.to_owned(), value.into());
            }
        }
        if let Some(enabled) = document.monitor.enabled {
            result.values.insert(
                "MQTT_MONITOR_ENABLED".to_owned(),
                enabled.to_string().into(),
            );
        }
        for (name, value) in [
            ("MQTT_STATE_DIR", document.broker.state_dir),
            ("MQTT_SERVER_CERT", document.tls.server_cert),
            ("MQTT_SERVER_KEY", document.tls.server_key),
            ("MQTT_CLIENT_CA", document.tls.client_ca),
            ("MQTT_CLIENT_CRL", document.tls.client_crl),
            ("MQTT_SECURITY_BUNDLE", document.security.bundle),
            ("MQTT_USERS_FILE", document.security.users_file),
            ("MQTT_ACL_FILE", document.security.acl_file),
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
        Ok(result)
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

    /// Admission ceiling for the executable; durable session quotas stay fixed.
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
}

#[derive(Default, Deserialize)]
#[serde(deny_unknown_fields)]
struct Limits {
    max_connections: Option<usize>,
}

#[derive(Default, Deserialize)]
#[serde(deny_unknown_fields)]
struct Broker {
    mode: Option<String>,
    bind: Option<String>,
    state_dir: Option<PathBuf>,
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
#[derive(Default, Deserialize)]
#[serde(deny_unknown_fields)]
struct Monitor {
    enabled: Option<bool>,
    bind: Option<String>,
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
    monitor: Monitor,
}
fn invalid(message: &'static str) -> io::Error {
    io::Error::new(io::ErrorKind::InvalidInput, message)
}

#[cfg(test)]
mod tests {
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
