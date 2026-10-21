#[cfg(any(test, all(windows, feature = "windows-service-runtime")))]
mod windows_launch;
#[cfg(all(windows, feature = "windows-service-runtime"))]
mod windows_service;

use std::{
    env, fs, io,
    net::SocketAddr,
    path::{Path, PathBuf},
    sync::Arc,
};

use mqtt_broker::{
    admin_channel::{AdminChannel, Config as AdminChannelConfig},
    auth::{AccessPolicy, AuthPolicy, DynamicPolicy, watch_security},
    configuration::Configuration,
    monitoring::{Config as MonitorConfig, Metrics, Monitor},
    mqtt::{self, Router},
    transport::{
        ConnectionDrain, MtlsFiles, OpenLabTransport, SecureTransport, TlsFiles, TransportLimits,
        watch_tls,
    },
};
use tracing::{info, warn};
use tracing_subscriber::EnvFilter;

fn main() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    #[cfg(all(windows, feature = "windows-service-runtime"))]
    if env::args_os().len() == 2
        && env::args_os()
            .nth(1)
            .is_some_and(|arg| arg == "--windows-service-capabilities")
    {
        println!(r#"{{"schema":1,"component":"broker","service_entrypoint":true}}"#);
        return Ok(());
    }
    #[cfg(all(windows, feature = "windows-service-runtime"))]
    if env::args_os()
        .nth(1)
        .is_some_and(|arg| arg == "--windows-service")
    {
        let launch = windows_launch::Launch::parse(&env::args_os().skip(1).collect::<Vec<_>>())?;
        windows_service::dispatch(launch.service_name, launch.logs, || match run() {
            Ok(()) => true,
            Err(error) => {
                windows_service::report_failure(error.as_ref());
                false
            }
        })?;
        return Ok(());
    }
    let mut arguments = env::args_os().skip(1);
    match (arguments.next(), arguments.next()) {
        (None, None) => run(),
        (Some(argument), None) if argument == "--version" || argument == "-V" => {
            println!("mqtt-broker {}", env!("CARGO_PKG_VERSION"));
            Ok(())
        }
        _ => {
            eprintln!("Argumento inválido. Use mqtt-broker --version ou execute sem argumentos.");
            std::process::exit(2);
        }
    }
}

#[tokio::main]
async fn run() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env())
        .with_target(false)
        .compact()
        .init();

    let config = load_configuration()?;
    let monitor_config = MonitorConfig::from_lookup(|name| config.var(name))?;
    let admin_config = AdminChannelConfig::from_lookup(|name| config.var_os(name))?;
    if admin_config.is_some() && config.var_os("MQTT_SECURITY_BUNDLE").is_none() {
        return Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            "admin channel requires security bundle",
        )
        .into());
    }
    let metrics = Arc::new(Metrics::default());
    let mode = BrokerMode::from_config(&config)?;
    validate_security_environment(mode, &config)?;
    let bind_address: SocketAddr = match config.var("MQTT_BIND") {
        Ok(value) => value,
        Err(env::VarError::NotPresent) => mode.default_bind().to_owned(),
        Err(env::VarError::NotUnicode(_)) => {
            return Err(io::Error::new(io::ErrorKind::InvalidInput, "invalid MQTT_BIND").into());
        }
    }
    .parse()?;
    let lab_websocket_bind = parse_ws_bind(&config, mode, bind_address)?;
    let additional_binds = config.additional_binds(bind_address)?;
    let secure_websocket_bind = parse_wss_bind(&config, mode, bind_address, &additional_binds)?;
    let endpoint_policies = config.endpoint_policies(bind_address, &additional_binds)?;
    if secure_websocket_bind.is_some() && !endpoint_policies.is_empty() {
        return Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            "MQTT_WSS_BIND requires a shared secure-mtls policy",
        )
        .into());
    }
    if mode != BrokerMode::SecureMtls && !additional_binds.is_empty() {
        return Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            "additional binds require secure-mtls",
        )
        .into());
    }
    if !endpoint_policies.is_empty()
        && (mode != BrokerMode::SecureMtls
            || config.var_os("MQTT_SECURITY_BUNDLE").is_some()
            || config.var_os("MQTT_USERS_FILE").is_some()
            || config.var_os("MQTT_ACL_FILE").is_some())
    {
        return Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            "endpoint policies require static secure-mtls without shared security files",
        )
        .into());
    }
    if mode.is_plain_lab() {
        validate_open_lab_bind(bind_address)?;
    }
    mode.validate_environment(&config)?;
    let state_directory = required_path(&config, "MQTT_STATE_DIR")?;
    let required: &[&str] = match mode {
        BrokerMode::SecureMtls => &["MQTT_SERVER_CERT", "MQTT_SERVER_KEY", "MQTT_CLIENT_CA"],
        BrokerMode::TlsPassword => &["MQTT_SERVER_CERT", "MQTT_SERVER_KEY"],
        BrokerMode::PasswordLab => &["MQTT_USERS_FILE"],
        BrokerMode::OpenLab | BrokerMode::AclLab => &[],
    };
    for name in required {
        required_path(&config, name)?;
    }
    if matches!(
        mode,
        BrokerMode::SecureMtls | BrokerMode::TlsPassword | BrokerMode::AclLab
    ) && config.var_os("MQTT_SECURITY_BUNDLE").is_none()
        && endpoint_policies.is_empty()
    {
        required_path(&config, "MQTT_USERS_FILE")?;
        required_path(&config, "MQTT_ACL_FILE")?;
    }
    let state_limits = config.state_limits()?;
    let limits = TransportLimits {
        max_concurrent_connections: config.max_connections()?,
    };

    serve(
        &config,
        mode,
        (
            bind_address,
            additional_binds,
            lab_websocket_bind,
            secure_websocket_bind,
        ),
        state_directory,
        (limits, state_limits),
        (monitor_config, admin_config),
        metrics,
    )
    .await
}

type ListenerBinds = (
    SocketAddr,
    Vec<SocketAddr>,
    Option<SocketAddr>,
    Option<(SocketAddr, bool)>,
);

#[allow(clippy::too_many_lines)] // Keep each security profile's startup and stop boundary explicit.
async fn serve(
    config: &Configuration,
    mode: BrokerMode,
    bind_addresses: ListenerBinds,
    state_directory: PathBuf,
    limits: (TransportLimits, mqtt::StateLimits),
    operational_configs: (MonitorConfig, Option<AdminChannelConfig>),
    metrics: Arc<Metrics>,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let (bind_address, additional_binds, lab_websocket_bind, secure_websocket_bind) =
        bind_addresses;
    let wss_allowed_origins = parse_wss_allowed_origins(config, secure_websocket_bind.is_some())?;
    let (monitor_config, admin_config) = operational_configs;
    let endpoint_policies = config.endpoint_policies(bind_address, &additional_binds)?;
    let (limits, state_limits) = limits;
    let server_keep_alive_seconds = config.server_keep_alive_seconds()?;
    match mode {
        BrokerMode::SecureMtls | BrokerMode::TlsPassword => {
            let tls_files = if mode == BrokerMode::SecureMtls {
                TlsFiles::Mtls(MtlsFiles {
                    server_certificate_chain: required_path(config, "MQTT_SERVER_CERT")?,
                    server_private_key: required_path(config, "MQTT_SERVER_KEY")?,
                    client_ca_certificate: required_path(config, "MQTT_CLIENT_CA")?,
                    client_crl: config.var_os("MQTT_CLIENT_CRL").map(PathBuf::from),
                })
            } else {
                TlsFiles::Password {
                    certificate_chain: required_path(config, "MQTT_SERVER_CERT")?,
                    private_key: required_path(config, "MQTT_SERVER_KEY")?,
                }
            };
            let tls_config = tls_files.load()?;
            let scoped = if endpoint_policies.is_empty() {
                None
            } else {
                let policies = endpoint_policies
                    .iter()
                    .map(|entry| AuthPolicy::load(&entry.users_file, &entry.acl_file))
                    .collect::<Result<Vec<_>, _>>()?;
                Some(Arc::new(policies))
            };
            let auth = if let Some(policies) = &scoped {
                Arc::new(AccessPolicy::scoped(policies.clone(), None))
            } else {
                load_policy(config, mode).await?
            };
            ensure_state_profile(
                &state_directory,
                if scoped.is_some() {
                    "secure-mtls-scoped"
                } else {
                    mode.profile_name()
                },
            )?;
            let router = start_router(
                &state_directory,
                &auth,
                &metrics,
                state_limits,
                server_keep_alive_seconds,
            )
            .await?;
            let _security = watch_security(&auth, router.clone())?;
            let _admin = admin_config
                .as_ref()
                .map(|config| AdminChannel::start(config, auth.clone(), router.clone()))
                .transpose()?;
            let transport = if mode == BrokerMode::SecureMtls {
                SecureTransport::bind_observed(
                    bind_address,
                    tls_config,
                    limits,
                    Some(metrics.clone()),
                )
                .await?
            } else {
                SecureTransport::bind_password_observed(
                    bind_address,
                    tls_config,
                    limits,
                    Some(metrics.clone()),
                )
                .await?
            };
            let mut transports = Vec::new();
            for address in additional_binds {
                transports.push(transport.bind_additional(address).await?);
            }
            let wss_transport = if let Some((address, remote_enabled)) = secure_websocket_bind {
                Some(
                    transport
                        .bind_websocket_secure(address, remote_enabled, wss_allowed_origins)
                        .await?,
                )
            } else {
                None
            };
            let _tls_watch = watch_tls(tls_files, transport.tls_reloader())?;
            metrics.set_listener_ready(true);
            let _monitor = Monitor::start(&monitor_config, metrics.clone(), router.clone()).await?;
            info!(%bind_address, "secure MQTT listener started");
            let shutdown_router = router.clone();
            let connections = transport.drain_handle();
            transports.insert(0, transport);
            run_until_shutdown(
                async move {
                    let mut listeners: Vec<
                        std::pin::Pin<Box<dyn std::future::Future<Output = io::Result<()>> + Send>>,
                    > = Vec::new();
                    for (index, transport) in transports.into_iter().enumerate() {
                        let auth = scoped.as_ref().map_or_else(
                            || Arc::clone(&auth),
                            |policies| Arc::new(AccessPolicy::scoped(policies.clone(), Some(index))));
                        let router = Arc::clone(&router);
                        listeners.push(Box::pin(async move {
                            transport.serve(move |connection| {
                                let auth = Arc::clone(&auth);
                                let router = Arc::clone(&router);
                                async move { mqtt::serve_connection(connection, auth, router).await }
                            }).await
                        }));
                    }
                    if let Some(wss_transport) = wss_transport {
                        let auth = Arc::clone(&auth);
                        let router = Arc::clone(&router);
                        listeners.push(Box::pin(async move {
                            wss_transport.serve(move |connection| {
                                let auth = Arc::clone(&auth);
                                let router = Arc::clone(&router);
                                async move { mqtt::serve_connection(connection, auth, router).await }
                            }).await
                        }));
                    }
                    // All accept futures are owned here: cancellation drops every
                    // listener synchronously before the router shutdown barrier.
                    std::future::poll_fn(move |context| {
                        for listener in &mut listeners {
                            if let std::task::Poll::Ready(result) = listener.as_mut().poll(context) {
                                return std::task::Poll::Ready(result);
                            }
                        }
                        std::task::Poll::Pending
                    }).await
                },
                shutdown_router,
                metrics.clone(),
                connections,
            )
            .await?;
        }
        BrokerMode::OpenLab => {
            let auth = Arc::new(AccessPolicy::open_lab());
            ensure_state_profile(&state_directory, mode.profile_name())?;
            let router = start_router(
                &state_directory,
                &auth,
                &metrics,
                state_limits,
                server_keep_alive_seconds,
            )
            .await?;
            let _security = watch_security(&auth, router.clone())?;
            let transport =
                OpenLabTransport::bind_observed(bind_address, limits, Some(metrics.clone()))
                    .await?;
            let ws_transport = if let Some(address) = lab_websocket_bind {
                Some(transport.bind_websocket(address).await?)
            } else {
                None
            };
            metrics.set_listener_ready(true);
            let _monitor = Monitor::start(&monitor_config, metrics.clone(), router.clone()).await?;
            warn!(%bind_address, "OPEN LAB listener started without TLS, authentication or ACL; loopback only");
            let shutdown_router = router.clone();
            let connections = transport.drain_handle();
            let serving = async move {
                let tcp_auth = Arc::clone(&auth);
                let tcp_router = Arc::clone(&router);
                let tcp = transport.serve(move |connection| {
                    let auth = Arc::clone(&tcp_auth);
                    let router = Arc::clone(&tcp_router);
                    async move { mqtt::serve_connection(connection, auth, router).await }
                });
                if let Some(ws_transport) = ws_transport {
                    let ws = ws_transport.serve(move |connection| {
                        let auth = Arc::clone(&auth);
                        let router = Arc::clone(&router);
                        async move { mqtt::serve_connection(connection, auth, router).await }
                    });
                    tokio::select! { result = tcp => result, result = ws => result }
                } else {
                    tcp.await
                }
            };
            run_until_shutdown(serving, shutdown_router, metrics.clone(), connections).await?;
        }
        BrokerMode::PasswordLab => {
            let auth = Arc::new(AccessPolicy::password_lab(AuthPolicy::load_passwords(
                &required_path(config, "MQTT_USERS_FILE")?,
            )?));
            ensure_state_profile(&state_directory, mode.profile_name())?;
            let router = start_router(
                &state_directory,
                &auth,
                &metrics,
                state_limits,
                server_keep_alive_seconds,
            )
            .await?;
            let _security = watch_security(&auth, router.clone())?;
            let transport =
                OpenLabTransport::bind_observed(bind_address, limits, Some(metrics.clone()))
                    .await?;
            metrics.set_listener_ready(true);
            let _monitor = Monitor::start(&monitor_config, metrics.clone(), router.clone()).await?;
            warn!(%bind_address, "PASSWORD LAB listener started without TLS or ACL; credentials are plaintext on the wire; loopback only");
            let shutdown_router = router.clone();
            let connections = transport.drain_handle();
            run_until_shutdown(
                transport.serve(move |connection| {
                    let auth = Arc::clone(&auth);
                    let router = Arc::clone(&router);
                    async move { mqtt::serve_connection(connection, auth, router).await }
                }),
                shutdown_router,
                metrics.clone(),
                connections,
            )
            .await?;
        }
        BrokerMode::AclLab => {
            let auth = load_policy(config, mode).await?;
            ensure_state_profile(&state_directory, mode.profile_name())?;
            let router = start_router(
                &state_directory,
                &auth,
                &metrics,
                state_limits,
                server_keep_alive_seconds,
            )
            .await?;
            let _security = watch_security(&auth, router.clone())?;
            let _admin = admin_config
                .as_ref()
                .map(|config| AdminChannel::start(config, auth.clone(), router.clone()))
                .transpose()?;
            let transport =
                OpenLabTransport::bind_observed(bind_address, limits, Some(metrics.clone()))
                    .await?;
            metrics.set_listener_ready(true);
            let _monitor = Monitor::start(&monitor_config, metrics.clone(), router.clone()).await?;
            warn!(%bind_address, "ACL LAB listener started without TLS; credentials are plaintext on the wire; loopback only");
            let shutdown_router = router.clone();
            let connections = transport.drain_handle();
            run_until_shutdown(
                transport.serve(move |connection| {
                    let auth = Arc::clone(&auth);
                    let router = Arc::clone(&router);
                    async move { mqtt::serve_connection(connection, auth, router).await }
                }),
                shutdown_router,
                metrics.clone(),
                connections,
            )
            .await?;
        }
    }

    Ok(())
}

fn parse_ws_bind(
    config: &Configuration,
    mode: BrokerMode,
    tcp_bind: SocketAddr,
) -> io::Result<Option<SocketAddr>> {
    let value = match config.var("MQTT_WS_BIND") {
        Ok(value) => value,
        Err(env::VarError::NotPresent) => return Ok(None),
        Err(env::VarError::NotUnicode(_)) => {
            return Err(io::Error::new(
                io::ErrorKind::InvalidInput,
                "invalid MQTT_WS_BIND",
            ));
        }
    };
    let address: SocketAddr = value
        .parse()
        .map_err(|_| io::Error::new(io::ErrorKind::InvalidInput, "invalid MQTT_WS_BIND"))?;
    if mode != BrokerMode::OpenLab
        || !address.ip().is_loopback()
        || address.port() == 0
        || address == tcp_bind
    {
        return Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            "MQTT_WS_BIND requires open-lab, a distinct loopback IP and nonzero port",
        ));
    }
    Ok(Some(address))
}

fn parse_wss_bind(
    config: &Configuration,
    mode: BrokerMode,
    tcp_bind: SocketAddr,
    additional_binds: &[SocketAddr],
) -> io::Result<Option<(SocketAddr, bool)>> {
    let remote_setting = config.var("MQTT_WSS_REMOTE_ENABLED");
    let remote_enabled = match remote_setting.as_ref() {
        Ok(value) if value == "true" => true,
        Ok(value) if value == "false" => false,
        Ok(_) | Err(env::VarError::NotUnicode(_)) => {
            return Err(io::Error::new(
                io::ErrorKind::InvalidInput,
                "invalid MQTT_WSS_REMOTE_ENABLED",
            ));
        }
        Err(env::VarError::NotPresent) => false,
    };
    let value = match config.var("MQTT_WSS_BIND") {
        Ok(value) => value,
        Err(env::VarError::NotPresent) if remote_setting.is_err() => return Ok(None),
        Err(env::VarError::NotPresent) => {
            return Err(io::Error::new(
                io::ErrorKind::InvalidInput,
                "MQTT_WSS_REMOTE_ENABLED requires MQTT_WSS_BIND",
            ));
        }
        Err(env::VarError::NotUnicode(_)) => {
            return Err(io::Error::new(
                io::ErrorKind::InvalidInput,
                "invalid MQTT_WSS_BIND",
            ));
        }
    };
    let address: SocketAddr = value
        .parse()
        .map_err(|_| io::Error::new(io::ErrorKind::InvalidInput, "invalid MQTT_WSS_BIND"))?;
    let collision = |other: &SocketAddr| {
        address.port() == other.port()
            && (address.ip() == other.ip()
                || address.ip().is_unspecified()
                || other.ip().is_unspecified())
    };
    if mode != BrokerMode::SecureMtls
        || address.ip().is_loopback() == remote_enabled
        || address.ip().is_multicast()
        || address.port() == 0
        || collision(&tcp_bind)
        || additional_binds.iter().any(collision)
    {
        return Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            "MQTT_WSS_BIND requires secure-mtls, a distinct port and explicit remote opt-in",
        ));
    }
    Ok(Some((address, remote_enabled)))
}

fn parse_wss_allowed_origins(config: &Configuration, wss_enabled: bool) -> io::Result<Vec<String>> {
    let value = match config.var("MQTT_WSS_ALLOWED_ORIGINS") {
        Ok(value) if wss_enabled => value,
        Ok(_) => {
            return Err(io::Error::new(
                io::ErrorKind::InvalidInput,
                "MQTT_WSS_ALLOWED_ORIGINS requires MQTT_WSS_BIND",
            ));
        }
        Err(env::VarError::NotPresent) => return Ok(Vec::new()),
        Err(env::VarError::NotUnicode(_)) => {
            return Err(io::Error::new(
                io::ErrorKind::InvalidInput,
                "invalid MQTT_WSS_ALLOWED_ORIGINS",
            ));
        }
    };
    parse_origin_list(&value)
}

fn parse_origin_list(value: &str) -> io::Result<Vec<String>> {
    if value.is_empty() {
        return Ok(Vec::new());
    }
    let origins: Vec<String> = value.split(',').map(str::to_owned).collect();
    if value.len() > 4096
        || origins.len() > 16
        || origins.iter().any(|origin| !valid_https_origin(origin))
        || origins
            .iter()
            .enumerate()
            .any(|(index, origin)| origins[..index].contains(origin))
    {
        return Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            "invalid MQTT_WSS_ALLOWED_ORIGINS",
        ));
    }
    Ok(origins)
}

fn valid_https_origin(origin: &str) -> bool {
    let Some(authority) = origin.strip_prefix("https://") else {
        return false;
    };
    if authority.is_empty()
        || authority.len() > 255
        || authority.bytes().any(|byte| {
            !byte.is_ascii()
                || byte.is_ascii_whitespace()
                || matches!(byte, b'/' | b'?' | b'#' | b'@' | b'*' | b'%' | b'\\')
        })
    {
        return false;
    }
    if let Some(bracketed) = authority.strip_prefix('[') {
        let Some((host, remainder)) = bracketed.split_once(']') else {
            return false;
        };
        return host.parse::<std::net::Ipv6Addr>().is_ok()
            && (remainder.is_empty() || valid_origin_port(remainder));
    }
    let (host, port) = authority
        .split_once(':')
        .map_or((authority, None), |(host, port)| (host, Some(port)));
    let valid_host = host.parse::<std::net::Ipv4Addr>().is_ok()
        || (!host.is_empty()
            && host.split('.').all(|label| {
                !label.is_empty()
                    && !label.starts_with('-')
                    && !label.ends_with('-')
                    && label.bytes().all(|byte| {
                        byte.is_ascii_lowercase() || byte.is_ascii_digit() || byte == b'-'
                    })
            }));
    valid_host && port.is_none_or(|port| valid_origin_port(&format!(":{port}")))
}

fn valid_origin_port(value: &str) -> bool {
    value
        .strip_prefix(':')
        .is_some_and(|port| port.parse::<u16>().is_ok_and(|number| number > 0))
}

fn load_configuration() -> io::Result<Configuration> {
    #[cfg(all(windows, feature = "windows-service-runtime"))]
    if windows_service::active() {
        let launch = windows_launch::Launch::parse(&env::args_os().skip(1).collect::<Vec<_>>())?;
        return Configuration::from_file(&launch.config);
    }
    Configuration::load()
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
    #[cfg(all(windows, feature = "windows-service-runtime"))]
    {
        windows_service::shutdown().await
    }
    #[cfg(not(any(unix, all(windows, feature = "windows-service-runtime"))))]
    tokio::signal::ctrl_c().await
}

async fn run_until_shutdown(
    serving: impl std::future::Future<Output = io::Result<()>>,
    router: Arc<Router>,
    metrics: Arc<Metrics>,
    connections: ConnectionDrain,
) -> Result<(), mqtt_broker::transport::HandlerError> {
    // Drop the accept loop/listener before queuing the actor shutdown barrier.
    let stopped = {
        tokio::pin!(serving);
        #[cfg(all(windows, feature = "windows-service-runtime"))]
        let readiness = windows_service::running();
        #[cfg(not(all(windows, feature = "windows-service-runtime")))]
        let readiness = Ok::<(), io::Error>(());
        match readiness {
            Ok(()) => tokio::select! {
                biased;
                signal = shutdown_signal() => signal,
                result = &mut serving => result,
            },
            // Even an SCM status failure must close listeners and flush the
            // actor before its error is propagated to service_main.
            Err(error) => Err(error),
        }
    };
    metrics.set_listener_ready(false);
    info!("stopping listener and durable session actor");
    finish_shutdown(
        router.shutdown(),
        connections.wait(),
        std::time::Duration::from_secs(15),
    )
    .await?;
    stopped?;
    info!("durable broker shutdown complete");
    Ok(())
}

async fn finish_shutdown(
    actor: impl std::future::Future<Output = Result<(), mqtt_broker::transport::HandlerError>>,
    connections: impl std::future::Future<Output = io::Result<()>>,
    budget: std::time::Duration,
) -> Result<(), mqtt_broker::transport::HandlerError> {
    let deadline = tokio::time::Instant::now() + budget;
    let actor_result = tokio::time::timeout_at(deadline, actor).await;
    // Try the remaining connections even when the actor failed. Both phases
    // share one absolute deadline, and a later drain timeout cannot overwrite
    // an earlier durable-storage error.
    let connection_result = tokio::time::timeout_at(deadline, connections).await;
    let elapsed = |_| io::Error::new(io::ErrorKind::TimedOut, "broker shutdown timed out");
    actor_result.map_err(elapsed)??;
    connection_result.map_err(elapsed)??;
    Ok(())
}

fn validate_security_environment(
    mode: BrokerMode,
    config: &Configuration,
) -> Result<(), io::Error> {
    if config.var_os("MQTT_SECURITY_BUNDLE").is_some() {
        if !matches!(
            mode,
            BrokerMode::SecureMtls | BrokerMode::TlsPassword | BrokerMode::AclLab
        ) {
            return Err(io::Error::new(
                io::ErrorKind::InvalidInput,
                "security bundle requires secure-mtls, tls-password or acl-lab",
            ));
        }
        reject_variables(
            config,
            &["MQTT_USERS_FILE", "MQTT_ACL_FILE"],
            "security bundle rejects legacy users/ACL variables",
        )?;
    }
    Ok(())
}

async fn load_policy(
    config: &Configuration,
    mode: BrokerMode,
) -> Result<Arc<AccessPolicy>, mqtt_broker::transport::HandlerError> {
    let secure = mode == BrokerMode::SecureMtls;
    if let Some(path) = config.var_os("MQTT_SECURITY_BUNDLE") {
        return DynamicPolicy::load(PathBuf::from(path), secure)
            .await
            .map(Arc::new)
            .map_err(Into::into);
    }
    let policy = if secure {
        AccessPolicy::secure(AuthPolicy::load(
            &required_path(config, "MQTT_USERS_FILE")?,
            &required_path(config, "MQTT_ACL_FILE")?,
        )?)
    } else {
        let password_policy = AuthPolicy::load_passwords_with_acl(
            &required_path(config, "MQTT_USERS_FILE")?,
            &required_path(config, "MQTT_ACL_FILE")?,
        )?;
        if mode == BrokerMode::TlsPassword {
            AccessPolicy::tls_password(password_policy)
        } else {
            AccessPolicy::acl_lab(password_policy)
        }
    };
    Ok(Arc::new(policy))
}

async fn start_router(
    directory: &Path,
    auth: &Arc<AccessPolicy>,
    metrics: &Arc<Metrics>,
    limits: mqtt::StateLimits,
    server_keep_alive_seconds: Option<u16>,
) -> Result<Arc<Router>, mqtt_broker::transport::HandlerError> {
    Router::start_observed_with_limits(directory, auth.clone(), metrics.clone(), limits)
        .await
        .map(|router| Arc::new(router.with_server_keep_alive(server_keep_alive_seconds)))
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum BrokerMode {
    SecureMtls,
    TlsPassword,
    OpenLab,
    PasswordLab,
    AclLab,
}

impl BrokerMode {
    fn from_config(config: &Configuration) -> Result<Self, io::Error> {
        match config.var("MQTT_MODE") {
            Ok(value) => Self::parse(Some(&value)),
            Err(env::VarError::NotPresent) => Self::parse(None),
            Err(env::VarError::NotUnicode(_)) => Err(io::Error::new(
                io::ErrorKind::InvalidInput,
                "MQTT_MODE must be secure-mtls, tls-password, open-lab, password-lab or acl-lab",
            )),
        }
    }

    fn parse(value: Option<&str>) -> Result<Self, io::Error> {
        match value {
            Some("open-lab") => Ok(Self::OpenLab),
            Some("password-lab") => Ok(Self::PasswordLab),
            Some("acl-lab") => Ok(Self::AclLab),
            Some("tls-password") => Ok(Self::TlsPassword),
            Some("secure-mtls") | None => Ok(Self::SecureMtls),
            Some(_) => Err(io::Error::new(
                io::ErrorKind::InvalidInput,
                "MQTT_MODE must be secure-mtls, tls-password, open-lab, password-lab or acl-lab",
            )),
        }
    }

    const fn default_bind(self) -> &'static str {
        match self {
            Self::SecureMtls | Self::TlsPassword => "192.168.0.100:8883",
            Self::OpenLab | Self::PasswordLab | Self::AclLab => "127.0.0.1:1883",
        }
    }

    const fn profile_name(self) -> &'static str {
        match self {
            Self::SecureMtls => "secure-mtls",
            Self::TlsPassword => "tls-password",
            Self::OpenLab => "open-lab",
            Self::PasswordLab => "password-lab",
            Self::AclLab => "acl-lab",
        }
    }

    const fn is_plain_lab(self) -> bool {
        matches!(self, Self::OpenLab | Self::PasswordLab | Self::AclLab)
    }

    fn validate_environment(self, config: &Configuration) -> Result<(), io::Error> {
        const TLS_VARIABLES: [&str; 4] = [
            "MQTT_SERVER_CERT",
            "MQTT_SERVER_KEY",
            "MQTT_CLIENT_CA",
            "MQTT_CLIENT_CRL",
        ];
        if self.is_plain_lab() {
            reject_variables(
                config,
                &TLS_VARIABLES,
                "plain laboratory mode rejects TLS variables",
            )?;
        }
        match self {
            Self::TlsPassword => reject_variables(
                config,
                &["MQTT_CLIENT_CA", "MQTT_CLIENT_CRL"],
                "tls-password rejects client CA and CRL",
            ),
            Self::OpenLab => reject_variables(
                config,
                &["MQTT_USERS_FILE", "MQTT_ACL_FILE"],
                "open-lab rejects authentication and ACL variables",
            ),
            Self::PasswordLab => reject_variables(
                config,
                &["MQTT_ACL_FILE"],
                "password-lab rejects MQTT_ACL_FILE",
            ),
            Self::AclLab | Self::SecureMtls => Ok(()),
        }
    }
}

fn reject_variables(
    config: &Configuration,
    names: &[&str],
    message: &'static str,
) -> Result<(), io::Error> {
    if names.iter().any(|name| config.var_os(name).is_some()) {
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

fn required_path(
    config: &Configuration,
    name: &'static str,
) -> Result<PathBuf, Box<dyn std::error::Error + Send + Sync>> {
    config
        .var_os(name)
        .filter(|path| !path.is_empty())
        .map(PathBuf::from)
        .ok_or_else(|| {
            std::io::Error::new(
                std::io::ErrorKind::InvalidInput,
                format!("required environment variable {name} is not set"),
            )
            .into()
        })
}

#[cfg(test)]
mod tests {
    #[test]
    fn wss_browser_origins_are_explicit_https_only() {
        use super::{parse_origin_list, valid_https_origin};

        let good = [
            "https://example.com",
            "https://sub.example.com:8443",
            "https://127.0.0.1:443",
            "https://[::1]:8443",
        ];
        for origin in good {
            assert!(valid_https_origin(origin), "{origin}");
        }
        for origin in [
            "",
            "null",
            "http://example.com",
            "https://example.com/",
            "https://example.com/path",
            "https://example.com?q=1",
            "https://example.com#x",
            "https://user@example.com",
            "https://*.example.com",
            "https://EXAMPLE.com",
            "https://example.com:0",
            "https://example.com:99999",
            "https://example.com ",
            "https://example.com,https://other.com",
            "https://[::1",
            "https://-bad.example",
        ] {
            assert!(!valid_https_origin(origin), "{origin}");
        }
        assert_eq!(
            parse_origin_list("https://example.com,https://other.com")
                .unwrap()
                .len(),
            2
        );
        assert!(parse_origin_list("https://example.com,https://example.com").is_err());
        assert!(parse_origin_list("https://example.com,").is_err());
        assert_eq!(parse_origin_list("").unwrap(), Vec::<String>::new());
    }
    use super::{BrokerMode, ensure_state_profile, validate_open_lab_bind};

    #[tokio::test]
    async fn actor_error_is_not_masked_by_a_later_connection_drain_timeout() {
        let error = super::finish_shutdown(
            async { Err("synthetic actor storage failure".into()) },
            std::future::pending::<std::io::Result<()>>(),
            std::time::Duration::from_millis(5),
        )
        .await
        .unwrap_err();
        assert_eq!(error.to_string(), "synthetic actor storage failure");
    }

    #[tokio::test]
    async fn actor_shutdown_error_is_preserved_after_connections_are_drained() {
        let drained = std::sync::Arc::new(std::sync::atomic::AtomicBool::new(false));
        let flag = drained.clone();
        let error = super::finish_shutdown(
            async { Err("synthetic actor storage failure".into()) },
            async move {
                flag.store(true, std::sync::atomic::Ordering::SeqCst);
                Ok(())
            },
            std::time::Duration::from_secs(1),
        )
        .await
        .unwrap_err();
        assert!(drained.load(std::sync::atomic::Ordering::SeqCst));
        assert_eq!(error.to_string(), "synthetic actor storage failure");
    }

    #[tokio::test]
    async fn actor_and_connection_drain_share_one_deadline() {
        let entered_drain = std::sync::Arc::new(std::sync::atomic::AtomicBool::new(false));
        let flag = entered_drain.clone();
        let error = super::finish_shutdown(
            async {
                tokio::time::sleep(std::time::Duration::from_millis(30)).await;
                Ok(())
            },
            async move {
                flag.store(true, std::sync::atomic::Ordering::SeqCst);
                tokio::time::sleep(std::time::Duration::from_millis(30)).await;
                Ok(())
            },
            std::time::Duration::from_millis(45),
        )
        .await
        .unwrap_err();
        assert!(entered_drain.load(std::sync::atomic::Ordering::SeqCst));
        assert_eq!(
            error.downcast_ref::<std::io::Error>().unwrap().kind(),
            std::io::ErrorKind::TimedOut
        );
    }

    #[test]
    fn secure_mode_is_default_and_unknown_values_fail_closed() {
        assert_eq!(BrokerMode::parse(None).unwrap(), BrokerMode::SecureMtls);
        assert_eq!(
            BrokerMode::parse(Some("tls-password")).unwrap(),
            BrokerMode::TlsPassword
        );
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
    fn tls_password_separates_state() {
        let mode = BrokerMode::TlsPassword;
        assert!(!mode.is_plain_lab());
        assert_eq!(mode.profile_name(), "tls-password");
        let directory = tempfile::tempdir().unwrap();
        ensure_state_profile(directory.path(), mode.profile_name()).unwrap();
        assert!(ensure_state_profile(directory.path(), "secure-mtls").is_err());
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
