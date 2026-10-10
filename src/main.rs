use std::{
    env, fs, io,
    net::SocketAddr,
    path::{Path, PathBuf},
    sync::Arc,
};

use mqtt_broker::{
    auth::{AccessPolicy, AuthPolicy, DynamicPolicy, watch_security},
    monitoring::{Config as MonitorConfig, Metrics, Monitor},
    mqtt::{self, Router},
    transport::{
        MtlsFiles, OpenLabTransport, SecureTransport, TransportLimits, load_mtls_server_config,
    },
};
use tracing::{info, warn};
use tracing_subscriber::EnvFilter;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env())
        .with_target(false)
        .compact()
        .init();

    let monitor_config = MonitorConfig::from_env()?;
    let metrics = Arc::new(Metrics::default());
    let mode = BrokerMode::from_env()?;
    validate_security_environment(mode)?;
    let bind_address: SocketAddr = env::var("MQTT_BIND")
        .unwrap_or_else(|_| mode.default_bind().to_owned())
        .parse()?;
    if mode.is_plain_lab() {
        validate_open_lab_bind(bind_address)?;
        mode.validate_environment()?;
    }
    let state_directory = required_path("MQTT_STATE_DIR")?;
    ensure_state_profile(&state_directory, mode.profile_name())?;
    let limits = TransportLimits {
        max_concurrent_connections: 64,
    };

    serve(
        mode,
        bind_address,
        state_directory,
        limits,
        monitor_config,
        metrics,
    )
    .await
}

#[allow(clippy::too_many_lines)] // Keep each security profile's startup and stop boundary explicit.
async fn serve(
    mode: BrokerMode,
    bind_address: SocketAddr,
    state_directory: PathBuf,
    limits: TransportLimits,
    monitor_config: MonitorConfig,
    metrics: Arc<Metrics>,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    match mode {
        BrokerMode::SecureMtls => {
            let tls_config = load_mtls_server_config(&MtlsFiles {
                server_certificate_chain: required_path("MQTT_SERVER_CERT")?,
                server_private_key: required_path("MQTT_SERVER_KEY")?,
                client_ca_certificate: required_path("MQTT_CLIENT_CA")?,
                client_crl: env::var_os("MQTT_CLIENT_CRL").map(PathBuf::from),
            })?;
            let auth = load_policy(true).await?;
            let router = start_router(&state_directory, &auth, &metrics).await?;
            let _security = watch_security(&auth, router.clone())?;
            let transport = SecureTransport::bind_observed(
                bind_address,
                tls_config,
                limits,
                Some(metrics.clone()),
            )
            .await?;
            metrics.set_listener_ready(true);
            let _monitor = Monitor::start(&monitor_config, metrics.clone(), router.clone()).await?;
            info!(%bind_address, "secure MQTT listener started");
            let shutdown_router = router.clone();
            run_until_shutdown(
                transport.serve(move |connection| {
                    let auth = Arc::clone(&auth);
                    let router = Arc::clone(&router);
                    async move { mqtt::serve_connection(connection, auth, router).await }
                }),
                shutdown_router,
                metrics.clone(),
            )
            .await?;
        }
        BrokerMode::OpenLab => {
            let auth = Arc::new(AccessPolicy::open_lab());
            let router = start_router(&state_directory, &auth, &metrics).await?;
            let _security = watch_security(&auth, router.clone())?;
            let transport =
                OpenLabTransport::bind_observed(bind_address, limits, Some(metrics.clone()))
                    .await?;
            metrics.set_listener_ready(true);
            let _monitor = Monitor::start(&monitor_config, metrics.clone(), router.clone()).await?;
            warn!(%bind_address, "OPEN LAB listener started without TLS, authentication or ACL; loopback only");
            let shutdown_router = router.clone();
            run_until_shutdown(
                transport.serve(move |connection| {
                    let auth = Arc::clone(&auth);
                    let router = Arc::clone(&router);
                    async move { mqtt::serve_connection(connection, auth, router).await }
                }),
                shutdown_router,
                metrics.clone(),
            )
            .await?;
        }
        BrokerMode::PasswordLab => {
            let auth = Arc::new(AccessPolicy::password_lab(AuthPolicy::load_passwords(
                &required_path("MQTT_USERS_FILE")?,
            )?));
            let router = start_router(&state_directory, &auth, &metrics).await?;
            let _security = watch_security(&auth, router.clone())?;
            let transport =
                OpenLabTransport::bind_observed(bind_address, limits, Some(metrics.clone()))
                    .await?;
            metrics.set_listener_ready(true);
            let _monitor = Monitor::start(&monitor_config, metrics.clone(), router.clone()).await?;
            warn!(%bind_address, "PASSWORD LAB listener started without TLS or ACL; credentials are plaintext on the wire; loopback only");
            let shutdown_router = router.clone();
            run_until_shutdown(
                transport.serve(move |connection| {
                    let auth = Arc::clone(&auth);
                    let router = Arc::clone(&router);
                    async move { mqtt::serve_connection(connection, auth, router).await }
                }),
                shutdown_router,
                metrics.clone(),
            )
            .await?;
        }
        BrokerMode::AclLab => {
            let auth = load_policy(false).await?;
            let router = start_router(&state_directory, &auth, &metrics).await?;
            let _security = watch_security(&auth, router.clone())?;
            let transport =
                OpenLabTransport::bind_observed(bind_address, limits, Some(metrics.clone()))
                    .await?;
            metrics.set_listener_ready(true);
            let _monitor = Monitor::start(&monitor_config, metrics.clone(), router.clone()).await?;
            warn!(%bind_address, "ACL LAB listener started without TLS; credentials are plaintext on the wire; loopback only");
            let shutdown_router = router.clone();
            run_until_shutdown(
                transport.serve(move |connection| {
                    let auth = Arc::clone(&auth);
                    let router = Arc::clone(&router);
                    async move { mqtt::serve_connection(connection, auth, router).await }
                }),
                shutdown_router,
                metrics.clone(),
            )
            .await?;
        }
    }

    Ok(())
}

async fn shutdown_signal() -> io::Result<()> {
    #[cfg(unix)]
    {
        let mut terminate =
            tokio::signal::unix::signal(tokio::signal::unix::SignalKind::terminate())?;
        tokio::select! {
            result = tokio::signal::ctrl_c() => result,
            _ = terminate.recv() => Ok(()),
        }
    }
    #[cfg(not(unix))]
    tokio::signal::ctrl_c().await
}

async fn run_until_shutdown(
    serving: impl std::future::Future<Output = io::Result<()>>,
    router: Arc<Router>,
    metrics: Arc<Metrics>,
) -> Result<(), mqtt_broker::transport::HandlerError> {
    // Drop the accept loop/listener before queuing the actor shutdown barrier.
    {
        tokio::pin!(serving);
        tokio::select! {
            biased;
            signal = shutdown_signal() => signal?,
            result = &mut serving => result?,
        }
    }
    metrics.set_listener_ready(false);
    info!("stopping listener and durable session actor");
    tokio::time::timeout(std::time::Duration::from_secs(15), router.shutdown())
        .await
        .map_err(|_| io::Error::new(io::ErrorKind::TimedOut, "broker shutdown timed out"))??;
    info!("durable broker shutdown complete");
    Ok(())
}

fn validate_security_environment(mode: BrokerMode) -> Result<(), io::Error> {
    if env::var_os("MQTT_SECURITY_BUNDLE").is_some() {
        if !matches!(mode, BrokerMode::SecureMtls | BrokerMode::AclLab) {
            return Err(io::Error::new(
                io::ErrorKind::InvalidInput,
                "security bundle requires secure-mtls or acl-lab",
            ));
        }
        reject_variables(
            &["MQTT_USERS_FILE", "MQTT_ACL_FILE"],
            "security bundle rejects legacy users/ACL variables",
        )?;
    }
    Ok(())
}

async fn load_policy(
    secure: bool,
) -> Result<Arc<AccessPolicy>, mqtt_broker::transport::HandlerError> {
    if let Some(path) = env::var_os("MQTT_SECURITY_BUNDLE") {
        return DynamicPolicy::load(PathBuf::from(path), secure)
            .await
            .map(Arc::new)
            .map_err(Into::into);
    }
    let policy = if secure {
        AccessPolicy::secure(AuthPolicy::load(
            &required_path("MQTT_USERS_FILE")?,
            &required_path("MQTT_ACL_FILE")?,
        )?)
    } else {
        AccessPolicy::acl_lab(AuthPolicy::load_passwords_with_acl(
            &required_path("MQTT_USERS_FILE")?,
            &required_path("MQTT_ACL_FILE")?,
        )?)
    };
    Ok(Arc::new(policy))
}

async fn start_router(
    directory: &Path,
    auth: &Arc<AccessPolicy>,
    metrics: &Arc<Metrics>,
) -> Result<Arc<Router>, mqtt_broker::transport::HandlerError> {
    Router::start_observed(directory, auth.clone(), metrics.clone())
        .await
        .map(Arc::new)
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum BrokerMode {
    SecureMtls,
    OpenLab,
    PasswordLab,
    AclLab,
}

impl BrokerMode {
    fn from_env() -> Result<Self, io::Error> {
        match env::var("MQTT_MODE") {
            Ok(value) => Self::parse(Some(&value)),
            Err(env::VarError::NotPresent) => Self::parse(None),
            Err(env::VarError::NotUnicode(_)) => Err(io::Error::new(
                io::ErrorKind::InvalidInput,
                "MQTT_MODE must be secure-mtls, open-lab, password-lab or acl-lab",
            )),
        }
    }

    fn parse(value: Option<&str>) -> Result<Self, io::Error> {
        match value {
            Some("open-lab") => Ok(Self::OpenLab),
            Some("password-lab") => Ok(Self::PasswordLab),
            Some("acl-lab") => Ok(Self::AclLab),
            Some("secure-mtls") | None => Ok(Self::SecureMtls),
            Some(_) => Err(io::Error::new(
                io::ErrorKind::InvalidInput,
                "MQTT_MODE must be secure-mtls, open-lab, password-lab or acl-lab",
            )),
        }
    }

    const fn default_bind(self) -> &'static str {
        match self {
            Self::SecureMtls => "192.168.0.100:8883",
            Self::OpenLab | Self::PasswordLab | Self::AclLab => "127.0.0.1:1883",
        }
    }

    const fn profile_name(self) -> &'static str {
        match self {
            Self::SecureMtls => "secure-mtls",
            Self::OpenLab => "open-lab",
            Self::PasswordLab => "password-lab",
            Self::AclLab => "acl-lab",
        }
    }

    const fn is_plain_lab(self) -> bool {
        !matches!(self, Self::SecureMtls)
    }

    fn validate_environment(self) -> Result<(), io::Error> {
        const TLS_VARIABLES: [&str; 4] = [
            "MQTT_SERVER_CERT",
            "MQTT_SERVER_KEY",
            "MQTT_CLIENT_CA",
            "MQTT_CLIENT_CRL",
        ];
        reject_variables(
            &TLS_VARIABLES,
            "plain laboratory mode rejects TLS variables",
        )?;
        match self {
            Self::OpenLab => reject_variables(
                &["MQTT_USERS_FILE", "MQTT_ACL_FILE"],
                "open-lab rejects authentication and ACL variables",
            ),
            Self::PasswordLab => {
                reject_variables(&["MQTT_ACL_FILE"], "password-lab rejects MQTT_ACL_FILE")
            }
            Self::AclLab | Self::SecureMtls => Ok(()),
        }
    }
}

fn reject_variables(names: &[&str], message: &'static str) -> Result<(), io::Error> {
    if names.iter().any(|name| env::var_os(name).is_some()) {
        return Err(io::Error::new(io::ErrorKind::InvalidInput, message));
    }
    Ok(())
}

fn validate_open_lab_bind(address: SocketAddr) -> Result<(), io::Error> {
    if address.ip().is_loopback() {
        Ok(())
    } else {
        Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            "open-lab mode requires a loopback MQTT_BIND address",
        ))
    }
}

fn ensure_state_profile(directory: &Path, expected: &str) -> Result<(), io::Error> {
    const MARKER: &str = ".mqtt-broker-profile";
    fs::create_dir_all(directory)?;
    let marker = directory.join(MARKER);
    match fs::read_to_string(&marker) {
        Ok(found) if found.trim() == expected => Ok(()),
        Ok(_) => Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            "MQTT_STATE_DIR belongs to a different listener profile",
        )),
        Err(error) if error.kind() == io::ErrorKind::NotFound => {
            let has_durable_state =
                directory.join("state.wal").exists() || directory.join("state.snapshot").exists();
            if has_durable_state && expected != "secure-mtls" {
                return Err(io::Error::new(
                    io::ErrorKind::InvalidInput,
                    "unmarked MQTT_STATE_DIR with existing state is treated as secure-mtls",
                ));
            }
            fs::write(marker, format!("{expected}\n"))
        }
        Err(error) => Err(error),
    }
}

fn required_path(name: &'static str) -> Result<PathBuf, Box<dyn std::error::Error + Send + Sync>> {
    env::var_os(name).map(PathBuf::from).ok_or_else(|| {
        std::io::Error::new(
            std::io::ErrorKind::InvalidInput,
            format!("required environment variable {name} is not set"),
        )
        .into()
    })
}

#[cfg(test)]
mod tests {
    use super::{BrokerMode, ensure_state_profile, validate_open_lab_bind};

    #[test]
    fn secure_mode_is_default_and_unknown_values_fail_closed() {
        assert_eq!(BrokerMode::parse(None).unwrap(), BrokerMode::SecureMtls);
        assert_eq!(
            BrokerMode::parse(Some("open-lab")).unwrap(),
            BrokerMode::OpenLab
        );
        assert_eq!(
            BrokerMode::parse(Some("password-lab")).unwrap(),
            BrokerMode::PasswordLab
        );
        assert_eq!(
            BrokerMode::parse(Some("acl-lab")).unwrap(),
            BrokerMode::AclLab
        );
        assert!(BrokerMode::parse(Some("open")).is_err());
    }

    #[test]
    fn state_directory_cannot_cross_listener_profiles() {
        let directory = tempfile::tempdir().unwrap();
        ensure_state_profile(directory.path(), "open-lab").unwrap();
        assert!(ensure_state_profile(directory.path(), "secure-mtls").is_err());
    }

    #[test]
    fn existing_unmarked_state_is_treated_as_secure() {
        let directory = tempfile::tempdir().unwrap();
        std::fs::write(directory.path().join("state.wal"), b"existing").unwrap();
        assert!(ensure_state_profile(directory.path(), "open-lab").is_err());
        ensure_state_profile(directory.path(), "secure-mtls").unwrap();
    }

    #[test]
    fn open_lab_bind_is_loopback_only() {
        assert!(validate_open_lab_bind("127.0.0.1:1883".parse().unwrap()).is_ok());
        assert!(validate_open_lab_bind("0.0.0.0:1883".parse().unwrap()).is_err());
        assert!(validate_open_lab_bind("192.168.0.10:1883".parse().unwrap()).is_err());
    }
}
