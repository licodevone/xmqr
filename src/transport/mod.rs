//! Bounded network transport for MQTT clients.
//!
//! The default path is TLS-only with mutual authentication. A deliberately
//! named open-lab path exists only for loopback teaching labs.

use crate::monitoring::{Metrics, Rejection};
use std::{
    future::Future,
    io::{self, BufReader},
    net::SocketAddr,
    panic::AssertUnwindSafe,
    path::{Path, PathBuf},
    sync::{
        Arc,
        atomic::{AtomicU64, Ordering},
    },
    time::Duration,
};

use futures_util::FutureExt;
use rustls::{
    RootCertStore, ServerConfig,
    pki_types::{CertificateDer, CertificateRevocationListDer, PrivateKeyDer},
    server::WebPkiClientVerifier,
    version::{TLS12, TLS13},
};
use thiserror::Error;
use tokio::{
    io::{AsyncReadExt, AsyncWrite, AsyncWriteExt},
    net::{TcpListener, TcpStream},
    sync::{Semaphore, watch},
    time::{sleep, timeout},
};
use tokio_rustls::{TlsAcceptor, server::TlsStream};
use tracing::{debug, error, info, warn};
use x509_parser::{parse_x509_certificate, parse_x509_crl, time::ASN1Time};

mod rotation;
pub use rotation::{TlsFiles, TlsWatcher, watch_tls};

/// Maximum number of MQTT bytes accepted by the first application read.
pub const MAX_INITIAL_MQTT_BYTES: usize = 4 * 1024;

const MAX_INITIAL_MQTT_READ_LIMIT: u64 = 4 * 1024;

/// Maximum time allowed for the TLS handshake and for the first MQTT bytes.
pub const INITIAL_IO_TIMEOUT: Duration = Duration::from_secs(3);
const SHUTDOWN_TIMEOUT: Duration = Duration::from_secs(3);

/// Paths needed to build a mutually authenticated TLS server configuration.
#[derive(Debug, Clone)]
pub struct MtlsFiles {
    pub server_certificate_chain: PathBuf,
    pub server_private_key: PathBuf,
    pub client_ca_certificate: PathBuf,
    /// Optional PEM CRL. Without it, certificate-chain and validity checks still
    /// happen, but revocation cannot be determined offline.
    pub client_crl: Option<PathBuf>,
}

/// Resource limits applied before a per-client task is admitted.
#[derive(Debug, Clone, Copy)]
pub struct TransportLimits {
    pub max_concurrent_connections: usize,
}

impl Default for TransportLimits {
    fn default() -> Self {
        Self {
            max_concurrent_connections: 10_000,
        }
    }
}

enum ConnectionStream {
    Mtls(Box<TlsStream<TcpStream>>),
    OpenLab(TcpStream),
}

/// Data handed to the MQTT connection state machine after transport setup.
pub struct BrokerConnection {
    id: u64,
    peer_addr: SocketAddr,
    peer_certificates: Vec<CertificateDer<'static>>,
    initial_mqtt_bytes: Vec<u8>,
    stream: ConnectionStream,
}

impl BrokerConnection {
    #[cfg(all(test, unix))]
    pub(crate) async fn open_lab_for_test(stream: TcpStream) -> Result<Self, HandlerError> {
        let peer = stream.peer_addr()?;
        assert!(peer.ip().is_loopback());
        Ok(establish_open_lab_connection(1, peer, stream).await?)
    }
    #[must_use]
    pub const fn id(&self) -> u64 {
        self.id
    }

    #[must_use]
    pub const fn peer_addr(&self) -> SocketAddr {
        self.peer_addr
    }

    /// Certificate chain verified against the configured local client CA.
    /// Empty for TLS-password and the loopback-only laboratory modes.
    #[must_use]
    pub fn peer_certificates(&self) -> &[CertificateDer<'static>] {
        &self.peer_certificates
    }

    #[must_use]
    pub fn is_tls(&self) -> bool {
        matches!(&self.stream, ConnectionStream::Mtls(_))
    }

    /// Bytes already removed from the TLS stream by the Slowloris guard.
    pub fn take_initial_mqtt_bytes(&mut self) -> Vec<u8> {
        std::mem::take(&mut self.initial_mqtt_bytes)
    }

    /// Continue reading MQTT traffic after consuming the initial bytes.
    ///
    /// The MQTT layer must pass a deadline derived from its CONNECT/keep-alive
    /// state. This prevents a client from extending an incomplete packet forever.
    ///
    /// # Errors
    ///
    /// Returns [`ConnectionIoError::ReadTimeout`] when the deadline expires, or
    /// [`ConnectionIoError::Io`] when the TLS stream fails.
    pub async fn read_with_deadline(
        &mut self,
        buffer: &mut [u8],
        deadline: Duration,
    ) -> Result<usize, ConnectionIoError> {
        let read = async {
            match &mut self.stream {
                ConnectionStream::Mtls(stream) => stream.read(buffer).await,
                ConnectionStream::OpenLab(stream) => stream.read(buffer).await,
            }
        };
        timeout(deadline, read)
            .await
            .map_err(|_| ConnectionIoError::ReadTimeout { deadline })?
            .map_err(ConnectionIoError::Io)
    }

    /// Write with a caller-selected deadline so slow subscribers cannot pin a task.
    ///
    /// # Errors
    ///
    /// Returns [`ConnectionIoError::WriteTimeout`] when the deadline expires, or
    /// [`ConnectionIoError::Io`] when the TLS stream fails.
    pub async fn write_all_with_deadline(
        &mut self,
        bytes: &[u8],
        deadline: Duration,
    ) -> Result<(), ConnectionIoError> {
        let write = async {
            match &mut self.stream {
                ConnectionStream::Mtls(stream) => stream.write_all(bytes).await,
                ConnectionStream::OpenLab(stream) => stream.write_all(bytes).await,
            }
        };
        timeout(deadline, write)
            .await
            .map_err(|_| ConnectionIoError::WriteTimeout { deadline })?
            .map_err(ConnectionIoError::Io)
    }

    /// Close the underlying stream with a bounded TLS close/flush.
    ///
    /// # Errors
    ///
    /// Returns the socket error or `TimedOut` when a nonreading peer pins close.
    pub async fn shutdown(&mut self) -> io::Result<()> {
        match &mut self.stream {
            ConnectionStream::Mtls(stream) => {
                shutdown_with_deadline(stream, SHUTDOWN_TIMEOUT).await
            }
            ConnectionStream::OpenLab(stream) => {
                shutdown_with_deadline(stream, SHUTDOWN_TIMEOUT).await
            }
        }
    }
}

async fn shutdown_with_deadline<S: AsyncWrite + Unpin>(
    stream: &mut S,
    deadline: Duration,
) -> io::Result<()> {
    timeout(deadline, stream.shutdown()).await.map_err(|_| {
        io::Error::new(
            io::ErrorKind::TimedOut,
            "transport shutdown deadline exceeded",
        )
    })?
}

#[derive(Debug, Error)]
pub enum ConnectionIoError {
    #[error("read deadline of {deadline:?} exceeded")]
    ReadTimeout { deadline: Duration },
    #[error("write deadline of {deadline:?} exceeded")]
    WriteTimeout { deadline: Duration },
    #[error("connection I/O failed")]
    Io(#[source] io::Error),
}

#[derive(Debug, Error)]
pub enum TlsConfigError {
    #[error("cannot open {kind} PEM file {path}")]
    OpenPem {
        kind: &'static str,
        path: PathBuf,
        #[source]
        source: io::Error,
    },
    #[error("invalid {kind} PEM file {path}: {message}")]
    InvalidPem {
        kind: &'static str,
        path: PathBuf,
        message: String,
    },
    #[error("{kind} PEM file {path} contains no usable item")]
    EmptyPem { kind: &'static str, path: PathBuf },
    #[error("client CA certificate is not a valid trust anchor: {0}")]
    InvalidClientCa(String),
    #[error("cannot build the mandatory client-certificate verifier: {0}")]
    ClientVerifier(String),
    #[error("cannot build the TLS server configuration: {0}")]
    ServerConfig(String),
    #[error("{0} certificate validity period is invalid or expired")]
    CertificateValidity(&'static str),
    #[error("client CRL validity period is invalid or expired")]
    CrlValidity,
    #[error("client CRL issuer or signature does not match a configured CA")]
    CrlIssuer,
}

#[derive(Debug, Error)]
enum ClientError {
    #[error("TLS handshake timed out")]
    HandshakeTimeout,
    #[error("TLS handshake failed")]
    Handshake(#[source] io::Error),
    #[error("the verified TLS session has no client certificate")]
    MissingPeerCertificate,
    #[error("client sent no MQTT data within the initial deadline")]
    InitialReadTimeout,
    #[error("client closed before sending MQTT data")]
    ClosedBeforeMqtt,
    #[error("initial MQTT read failed")]
    InitialRead(#[source] io::Error),
}

pub type HandlerError = Box<dyn std::error::Error + Send + Sync + 'static>;

/// TCP listener plus a shared TLS generation and connection admission limit.
pub struct SecureTransport {
    listener: TcpListener,
    tls_config: watch::Receiver<Arc<ServerConfig>>,
    tls_sender: watch::Sender<Arc<ServerConfig>>,
    require_client_certificate: bool,
    connection_slots: Arc<Semaphore>,
    connection_capacity: u32,
    next_connection_id: Arc<AtomicU64>,
    metrics: Option<Arc<Metrics>>,
}

/// Publishes a fully validated TLS generation for subsequent handshakes.
#[derive(Clone)]
pub struct TlsReloader(watch::Sender<Arc<ServerConfig>>);

impl TlsReloader {
    pub fn publish(&self, config: Arc<ServerConfig>) {
        self.0.send_replace(config);
    }
}

/// Plain TCP listener for a local teaching lab. Construction rejects every
/// non-loopback address.
pub struct OpenLabTransport {
    listener: TcpListener,
    connection_slots: Arc<Semaphore>,
    connection_capacity: u32,
    next_connection_id: Arc<AtomicU64>,
    metrics: Option<Arc<Metrics>>,
}

/// Completion barrier for all admitted connection work, including handshakes.
/// Obtain this before moving the transport into `serve`, then stop/drop the
/// accept loop before waiting. This does not cancel existing client tasks.
#[derive(Clone)]
pub struct ConnectionDrain {
    slots: Arc<Semaphore>,
    capacity: u32,
}

impl ConnectionDrain {
    /// Wait until every connection's owned admission permit has been released.
    /// The caller must apply its overall shutdown deadline and stop new accepts
    /// first. Cancellation safely returns partially reserved permits.
    /// # Errors
    /// Returns an error if the admission semaphore was unexpectedly closed.
    pub async fn wait(self) -> io::Result<()> {
        let _finished = self
            .slots
            .acquire_many_owned(self.capacity)
            .await
            .map_err(|_| {
                io::Error::new(
                    io::ErrorKind::BrokenPipe,
                    "connection admission tracker closed",
                )
            })?;
        Ok(())
    }
}

fn admission_capacity(limit: usize) -> io::Result<u32> {
    u32::try_from(limit)
        .ok()
        .filter(|_| limit > 0 && limit <= Semaphore::MAX_PERMITS)
        .ok_or_else(|| {
            io::Error::new(
                io::ErrorKind::InvalidInput,
                "connection limit outside supported admission range",
            )
        })
}

impl SecureTransport {
    /// Bind the protected listener and initialize connection admission control.
    ///
    /// # Errors
    ///
    /// Returns [`io::ErrorKind::InvalidInput`] for a zero connection limit, or
    /// the socket error produced while binding `address`.
    pub async fn bind(
        address: SocketAddr,
        tls_config: Arc<ServerConfig>,
        limits: TransportLimits,
    ) -> io::Result<Self> {
        Self::bind_observed(address, tls_config, limits, None).await
    }
    /// Bind with optional bounded monitoring counters.
    /// # Errors
    /// Same validation and socket errors as `bind`.
    pub async fn bind_observed(
        address: SocketAddr,
        tls_config: Arc<ServerConfig>,
        limits: TransportLimits,
        metrics: Option<Arc<Metrics>>,
    ) -> io::Result<Self> {
        let connection_capacity = admission_capacity(limits.max_concurrent_connections)?;
        let listener = TcpListener::bind(address).await?;
        let (tls_sender, tls_config) = watch::channel(tls_config);
        Ok(Self {
            listener,
            tls_config,
            tls_sender,
            require_client_certificate: true,
            connection_slots: Arc::new(Semaphore::new(limits.max_concurrent_connections)),
            connection_capacity,
            next_connection_id: Arc::new(AtomicU64::new(1)),
            metrics,
        })
    }

    /// Bind a TLS endpoint that authenticates MQTT credentials without a client certificate.
    /// This is opt-in and must be paired with a deny-by-default password/ACL policy.
    /// # Errors
    /// Returns the same admission-limit and socket errors as `bind_observed`.
    pub async fn bind_password_observed(
        address: SocketAddr,
        tls_config: Arc<ServerConfig>,
        limits: TransportLimits,
        metrics: Option<Arc<Metrics>>,
    ) -> io::Result<Self> {
        let mut transport = Self::bind_observed(address, tls_config, limits, metrics).await?;
        transport.require_client_certificate = false;
        Ok(transport)
    }

    /// Bind another mTLS endpoint sharing this transport's admission pool and IDs.
    /// # Errors
    /// Returns the socket bind error without starting any accept task.
    pub async fn bind_additional(&self, address: SocketAddr) -> io::Result<Self> {
        Ok(Self {
            listener: TcpListener::bind(address).await?,
            tls_config: self.tls_config.clone(),
            tls_sender: self.tls_sender.clone(),
            require_client_certificate: self.require_client_certificate,
            connection_slots: self.connection_slots.clone(),
            connection_capacity: self.connection_capacity,
            next_connection_id: self.next_connection_id.clone(),
            metrics: self.metrics.clone(),
        })
    }

    #[must_use]
    pub fn tls_reloader(&self) -> TlsReloader {
        TlsReloader(self.tls_sender.clone())
    }

    /// Obtain a drain observer without changing connection admission limits.
    #[must_use]
    pub fn drain_handle(&self) -> ConnectionDrain {
        ConnectionDrain {
            slots: self.connection_slots.clone(),
            capacity: self.connection_capacity,
        }
    }

    /// Accept clients forever and isolate every device in its own Tokio task.
    ///
    /// A panic is caught at the task boundary when the binary uses unwinding
    /// panics (the release profile in this repository does). Panics never cross
    /// into the accept loop or another client task.
    ///
    /// # Errors
    ///
    /// The current implementation retries transient accept errors and normally
    /// runs forever. The result type leaves room for a future graceful-shutdown
    /// controller to return listener-level failures.
    pub async fn serve<H, F>(self, handler: H) -> io::Result<()>
    where
        H: Fn(BrokerConnection) -> F + Clone + Send + Sync + 'static,
        F: Future<Output = Result<(), HandlerError>> + Send + 'static,
    {
        loop {
            let (socket, peer_addr) = match self.listener.accept().await {
                Ok(connection) => connection,
                Err(source) => {
                    warn!(error = %source, "TCP accept failed; applying backoff");
                    sleep(Duration::from_millis(100)).await;
                    continue;
                }
            };

            if let Some(metrics) = &self.metrics {
                metrics.tcp_accepted.fetch_add(1, Ordering::Relaxed);
            }
            let Ok(permit) = Arc::clone(&self.connection_slots).try_acquire_owned() else {
                if let Some(metrics) = &self.metrics {
                    metrics.reject(Rejection::Admission);
                }
                warn!(%peer_addr, "connection rejected because the admission limit is full");
                drop(socket);
                continue;
            };

            if let Err(source) = socket.set_nodelay(true) {
                warn!(%peer_addr, error = %source, "cannot configure accepted socket");
                continue;
            }
            let tls_acceptor = TlsAcceptor::from(self.tls_config.borrow().clone());
            let require_client_certificate = self.require_client_certificate;
            let client_handler = handler.clone();
            let connection_id = self.next_connection_id.fetch_add(1, Ordering::Relaxed);
            let metrics = self.metrics.clone();

            // The drain barrier tracks work through its RAII admission permit;
            // catch_unwind records isolated panics without propagating them.
            drop(tokio::spawn(async move {
                let _permit = permit;
                let client = async {
                    let connection = establish_secure_connection(
                        connection_id,
                        peer_addr,
                        socket,
                        tls_acceptor,
                        require_client_certificate,
                    )
                    .await?;

                    client_handler(connection)
                        .await
                        .map_err(ClientTaskError::Handler)
                };

                match AssertUnwindSafe(client).catch_unwind().await {
                    Ok(Ok(())) => debug!(connection_id, %peer_addr, "client task finished"),
                    Ok(Err(ClientTaskError::Transport(source))) => {
                        if let Some(metrics) = &metrics {
                            metrics.reject(Rejection::Transport);
                        }
                        warn!(connection_id, %peer_addr, error = %source, "secure transport closed client");
                    }
                    Ok(Err(ClientTaskError::Handler(_))) => {
                        // Handler errors may contain application data. Keep the
                        // transport log free of credentials and MQTT payloads.
                        warn!(connection_id, %peer_addr, "MQTT handler closed client; details suppressed");
                    }
                    Err(_) => {
                        error!(connection_id, %peer_addr, "client task panicked and was isolated");
                    }
                }
            }));
        }
    }
}

impl OpenLabTransport {
    /// Bind an unencrypted teaching listener to a loopback address only.
    ///
    /// # Errors
    /// Returns [`io::ErrorKind::InvalidInput`] for a non-loopback address or a
    /// zero connection limit, and otherwise returns the socket bind error.
    pub async fn bind(address: SocketAddr, limits: TransportLimits) -> io::Result<Self> {
        Self::bind_observed(address, limits, None).await
    }
    /// Bind the same loopback-only listener with optional metrics.
    /// # Errors
    /// Same validation and socket errors as `bind`.
    pub async fn bind_observed(
        address: SocketAddr,
        limits: TransportLimits,
        metrics: Option<Arc<Metrics>>,
    ) -> io::Result<Self> {
        if !address.ip().is_loopback() {
            return Err(io::Error::new(
                io::ErrorKind::InvalidInput,
                "open-lab transport requires a loopback bind address",
            ));
        }
        let connection_capacity = admission_capacity(limits.max_concurrent_connections)?;
        let listener = TcpListener::bind(address).await?;
        Ok(Self {
            listener,
            connection_slots: Arc::new(Semaphore::new(limits.max_concurrent_connections)),
            connection_capacity,
            next_connection_id: Arc::new(AtomicU64::new(1)),
            metrics,
        })
    }

    /// Obtain a drain observer without changing loopback or admission policy.
    #[must_use]
    pub fn drain_handle(&self) -> ConnectionDrain {
        ConnectionDrain {
            slots: self.connection_slots.clone(),
            capacity: self.connection_capacity,
        }
    }

    /// Accept loopback clients forever with the same admission and panic
    /// isolation boundaries used by the secure transport.
    ///
    /// # Errors
    /// Returns listener-level socket errors. Transient accept errors are
    /// logged and retried with backoff.
    pub async fn serve<H, F>(self, handler: H) -> io::Result<()>
    where
        H: Fn(BrokerConnection) -> F + Clone + Send + Sync + 'static,
        F: Future<Output = Result<(), HandlerError>> + Send + 'static,
    {
        loop {
            let (socket, peer_addr) = match self.listener.accept().await {
                Ok(connection) => connection,
                Err(source) => {
                    warn!(error = %source, "TCP accept failed; applying backoff");
                    sleep(Duration::from_millis(100)).await;
                    continue;
                }
            };
            if let Some(metrics) = &self.metrics {
                metrics.tcp_accepted.fetch_add(1, Ordering::Relaxed);
            }
            let Ok(permit) = Arc::clone(&self.connection_slots).try_acquire_owned() else {
                if let Some(metrics) = &self.metrics {
                    metrics.reject(Rejection::Admission);
                }
                warn!(%peer_addr, "connection rejected because the admission limit is full");
                drop(socket);
                continue;
            };
            if let Err(source) = socket.set_nodelay(true) {
                warn!(%peer_addr, error = %source, "cannot configure accepted socket");
                continue;
            }
            let client_handler = handler.clone();
            let connection_id = self.next_connection_id.fetch_add(1, Ordering::Relaxed);
            let metrics = self.metrics.clone();
            drop(tokio::spawn(async move {
                let _permit = permit;
                let client = async {
                    let connection =
                        establish_open_lab_connection(connection_id, peer_addr, socket).await?;
                    client_handler(connection)
                        .await
                        .map_err(ClientTaskError::Handler)
                };
                match AssertUnwindSafe(client).catch_unwind().await {
                    Ok(Ok(())) => debug!(connection_id, %peer_addr, "client task finished"),
                    Ok(Err(ClientTaskError::Transport(source))) => {
                        if let Some(metrics) = &metrics {
                            metrics.reject(Rejection::Transport);
                        }
                        warn!(connection_id, %peer_addr, error = %source, "open-lab transport closed client");
                    }
                    Ok(Err(ClientTaskError::Handler(_))) => {
                        warn!(connection_id, %peer_addr, "MQTT handler closed client; details suppressed");
                    }
                    Err(_) => {
                        error!(connection_id, %peer_addr, "client task panicked and was isolated");
                    }
                }
            }));
        }
    }
}

#[derive(Debug, Error)]
enum ClientTaskError {
    #[error(transparent)]
    Transport(#[from] ClientError),
    #[error("MQTT connection handler failed: {0}")]
    Handler(HandlerError),
}

async fn establish_secure_connection(
    id: u64,
    peer_addr: SocketAddr,
    socket: TcpStream,
    tls_acceptor: TlsAcceptor,
    require_client_certificate: bool,
) -> Result<BrokerConnection, ClientError> {
    // Protect the TLS handshake itself from a pre-MQTT Slowloris client.
    let mut stream = timeout(INITIAL_IO_TIMEOUT, tls_acceptor.accept(socket))
        .await
        .map_err(|_| ClientError::HandshakeTimeout)?
        .map_err(ClientError::Handshake)?;

    let prepared = async {
        let peer_certificates = stream
            .get_ref()
            .1
            .peer_certificates()
            .map_or_else(Vec::new, ToOwned::to_owned);
        if require_client_certificate && peer_certificates.is_empty() {
            return Err(ClientError::MissingPeerCertificate);
        }

        // Cap decrypted MQTT bytes, not the potentially larger TLS handshake.
        let mut initial_buffer = [0_u8; MAX_INITIAL_MQTT_BYTES];
        let mut limited_reader = (&mut stream).take(MAX_INITIAL_MQTT_READ_LIMIT);
        let bytes_read = timeout(INITIAL_IO_TIMEOUT, limited_reader.read(&mut initial_buffer))
            .await
            .map_err(|_| ClientError::InitialReadTimeout)?
            .map_err(ClientError::InitialRead)?;
        if bytes_read == 0 {
            return Err(ClientError::ClosedBeforeMqtt);
        }
        Ok((peer_certificates, initial_buffer[..bytes_read].to_vec()))
    }
    .await;
    let (peer_certificates, initial_mqtt_bytes) = match prepared {
        Ok(initial) => initial,
        Err(error) => {
            // TLS is already established even if no MQTT bytes ever arrived.
            // Attempt close_notify within the existing bound; retain setup error.
            let _ = shutdown_with_deadline(&mut stream, SHUTDOWN_TIMEOUT).await;
            return Err(error);
        }
    };

    info!(id, %peer_addr, "TLS MQTT transport established");
    Ok(BrokerConnection {
        id,
        peer_addr,
        peer_certificates,
        initial_mqtt_bytes,
        stream: ConnectionStream::Mtls(Box::new(stream)),
    })
}

async fn establish_open_lab_connection(
    id: u64,
    peer_addr: SocketAddr,
    mut stream: TcpStream,
) -> Result<BrokerConnection, ClientError> {
    let mut initial_buffer = [0_u8; MAX_INITIAL_MQTT_BYTES];
    let mut limited_reader = (&mut stream).take(MAX_INITIAL_MQTT_READ_LIMIT);
    let bytes_read = timeout(INITIAL_IO_TIMEOUT, limited_reader.read(&mut initial_buffer))
        .await
        .map_err(|_| ClientError::InitialReadTimeout)?
        .map_err(ClientError::InitialRead)?;
    if bytes_read == 0 {
        return Err(ClientError::ClosedBeforeMqtt);
    }
    drop(limited_reader);
    info!(id, %peer_addr, "OPEN LAB MQTT transport established without TLS");
    Ok(BrokerConnection {
        id,
        peer_addr,
        peer_certificates: Vec::new(),
        initial_mqtt_bytes: initial_buffer[..bytes_read].to_vec(),
        stream: ConnectionStream::OpenLab(stream),
    })
}

/// Build an mTLS configuration using only TLS 1.2 and TLS 1.3.
///
/// Rustls' AWS-LC provider exposes modern AEAD suites and does not implement
/// legacy SSL/TLS versions, RC4, 3DES, or CBC suites. Protocol negotiation is
/// still restricted explicitly here to make the policy auditable.
///
/// # Errors
///
/// Returns [`TlsConfigError`] when a PEM cannot be read, a trust anchor or CRL
/// is invalid, the private key does not match, or the TLS policy cannot be built.
pub fn load_mtls_server_config(files: &MtlsFiles) -> Result<Arc<ServerConfig>, TlsConfigError> {
    let provider = Arc::new(rustls::crypto::aws_lc_rs::default_provider());
    let server_certificates =
        load_certificates(&files.server_certificate_chain, "server certificate")?;
    validate_certificates(&server_certificates, "server")?;
    let server_key = load_private_key(&files.server_private_key)?;
    let client_ca_certificates = load_certificates(&files.client_ca_certificate, "client CA")?;
    validate_certificates(&client_ca_certificates, "client CA")?;

    let mut roots = RootCertStore::empty();
    for certificate in &client_ca_certificates {
        roots
            .add(certificate.clone())
            .map_err(|source| TlsConfigError::InvalidClientCa(source.to_string()))?;
    }

    let mut verifier_builder =
        WebPkiClientVerifier::builder_with_provider(Arc::new(roots), Arc::clone(&provider));
    if let Some(crl_path) = &files.client_crl {
        let crls = load_crls(crl_path)?;
        validate_crls(&crls, &client_ca_certificates)?;
        verifier_builder = verifier_builder
            .with_crls(crls)
            .enforce_revocation_expiration();
    }
    // Deliberately do not call allow_unauthenticated(): a client certificate is mandatory.
    let client_verifier = verifier_builder
        .build()
        .map_err(|source| TlsConfigError::ClientVerifier(source.to_string()))?;

    let config = ServerConfig::builder_with_provider(provider)
        .with_protocol_versions(&[&TLS13, &TLS12])
        .map_err(|source| TlsConfigError::ServerConfig(source.to_string()))?
        .with_client_cert_verifier(client_verifier)
        .with_single_cert(server_certificates, server_key)
        .map_err(|source| TlsConfigError::ServerConfig(source.to_string()))?;

    Ok(Arc::new(config))
}

/// Build TLS with server identity only. MQTT username/password and ACL remain mandatory.
/// # Errors
/// Rejects missing, malformed or mismatched certificate and private key files.
pub fn load_password_server_config(
    certificate_chain: &Path,
    private_key: &Path,
) -> Result<Arc<ServerConfig>, TlsConfigError> {
    let provider = Arc::new(rustls::crypto::aws_lc_rs::default_provider());
    let certificates = load_certificates(certificate_chain, "server certificate")?;
    validate_certificates(&certificates, "server")?;
    let key = load_private_key(private_key)?;
    let config = ServerConfig::builder_with_provider(provider)
        .with_protocol_versions(&[&TLS13, &TLS12])
        .map_err(|source| TlsConfigError::ServerConfig(source.to_string()))?
        .with_no_client_auth()
        .with_single_cert(certificates, key)
        .map_err(|source| TlsConfigError::ServerConfig(source.to_string()))?;
    Ok(Arc::new(config))
}

fn validate_certificates(
    certificates: &[CertificateDer<'static>],
    kind: &'static str,
) -> Result<(), TlsConfigError> {
    let now = ASN1Time::now();
    for der in certificates {
        let (remainder, certificate) = parse_x509_certificate(der.as_ref())
            .map_err(|_| TlsConfigError::CertificateValidity(kind))?;
        if !remainder.is_empty() || !certificate.validity().is_valid_at(now) {
            return Err(TlsConfigError::CertificateValidity(kind));
        }
    }
    Ok(())
}

fn validate_crls(
    crls: &[CertificateRevocationListDer<'static>],
    client_cas: &[CertificateDer<'static>],
) -> Result<(), TlsConfigError> {
    let now = ASN1Time::now().timestamp();
    for der in crls {
        let (remainder, crl) =
            parse_x509_crl(der.as_ref()).map_err(|_| TlsConfigError::CrlValidity)?;
        let next = crl.next_update().ok_or(TlsConfigError::CrlValidity)?;
        if !remainder.is_empty() || crl.last_update().timestamp() > now || next.timestamp() <= now {
            return Err(TlsConfigError::CrlValidity);
        }
        let signed_by_configured_ca = client_cas.iter().any(|ca_der| {
            parse_x509_certificate(ca_der.as_ref()).is_ok_and(|(_, ca)| {
                crl.issuer() == ca.subject() && crl.verify_signature(ca.public_key()).is_ok()
            })
        });
        if !signed_by_configured_ca {
            return Err(TlsConfigError::CrlIssuer);
        }
    }
    Ok(())
}

fn load_certificates(
    path: &Path,
    kind: &'static str,
) -> Result<Vec<CertificateDer<'static>>, TlsConfigError> {
    let file = std::fs::File::open(path).map_err(|source| TlsConfigError::OpenPem {
        kind,
        path: path.to_path_buf(),
        source,
    })?;
    let certificates = rustls_pemfile::certs(&mut BufReader::new(file))
        .collect::<Result<Vec<_>, _>>()
        .map_err(|source| TlsConfigError::InvalidPem {
            kind,
            path: path.to_path_buf(),
            message: source.to_string(),
        })?;
    if certificates.is_empty() {
        return Err(TlsConfigError::EmptyPem {
            kind,
            path: path.to_path_buf(),
        });
    }
    Ok(certificates)
}

fn load_private_key(path: &Path) -> Result<PrivateKeyDer<'static>, TlsConfigError> {
    let kind = "server private key";
    let file = std::fs::File::open(path).map_err(|source| TlsConfigError::OpenPem {
        kind,
        path: path.to_path_buf(),
        source,
    })?;
    rustls_pemfile::private_key(&mut BufReader::new(file))
        .map_err(|source| TlsConfigError::InvalidPem {
            kind,
            path: path.to_path_buf(),
            message: source.to_string(),
        })?
        .ok_or_else(|| TlsConfigError::EmptyPem {
            kind,
            path: path.to_path_buf(),
        })
}

fn load_crls(path: &Path) -> Result<Vec<CertificateRevocationListDer<'static>>, TlsConfigError> {
    let kind = "client certificate revocation list";
    let file = std::fs::File::open(path).map_err(|source| TlsConfigError::OpenPem {
        kind,
        path: path.to_path_buf(),
        source,
    })?;
    let crls = rustls_pemfile::crls(&mut BufReader::new(file))
        .collect::<Result<Vec<_>, _>>()
        .map_err(|source| TlsConfigError::InvalidPem {
            kind,
            path: path.to_path_buf(),
            message: source.to_string(),
        })?;
    if crls.is_empty() {
        return Err(TlsConfigError::EmptyPem {
            kind,
            path: path.to_path_buf(),
        });
    }
    Ok(crls)
}

#[cfg(test)]
mod tests {
    use super::{OpenLabTransport, TransportLimits};
    use std::{
        io,
        pin::Pin,
        task::{Context, Poll},
        time::Duration,
    };
    use tokio::io::AsyncWrite;

    struct NeverCloses;
    impl AsyncWrite for NeverCloses {
        fn poll_write(
            self: Pin<&mut Self>,
            _: &mut Context<'_>,
            bytes: &[u8],
        ) -> Poll<io::Result<usize>> {
            Poll::Ready(Ok(bytes.len()))
        }
        fn poll_flush(self: Pin<&mut Self>, _: &mut Context<'_>) -> Poll<io::Result<()>> {
            Poll::Ready(Ok(()))
        }
        fn poll_shutdown(self: Pin<&mut Self>, _: &mut Context<'_>) -> Poll<io::Result<()>> {
            Poll::Pending
        }
    }

    #[tokio::test]
    async fn nonreading_peer_cannot_pin_transport_shutdown() {
        let error = super::shutdown_with_deadline(&mut NeverCloses, Duration::from_millis(5))
            .await
            .unwrap_err();
        assert_eq!(error.kind(), io::ErrorKind::TimedOut);
        assert_eq!(super::SHUTDOWN_TIMEOUT, Duration::from_secs(3));
    }

    #[tokio::test]
    async fn writable_transport_shutdown_succeeds() {
        super::shutdown_with_deadline(&mut tokio::io::sink(), Duration::from_millis(5))
            .await
            .unwrap();
    }

    #[tokio::test]
    async fn connection_drain_waits_for_every_owned_permit_and_does_not_change_capacity() {
        let transport = OpenLabTransport::bind(
            "127.0.0.1:0".parse().unwrap(),
            TransportLimits {
                max_concurrent_connections: 2,
            },
        )
        .await
        .unwrap();
        let slots = transport.connection_slots.clone();
        let first = slots.clone().acquire_owned().await.unwrap();
        let second = slots.clone().acquire_owned().await.unwrap();
        let drain = transport.drain_handle();
        drop(transport); // no accepts after drain begins
        let waiting = tokio::spawn(drain.wait());
        tokio::task::yield_now().await;
        assert!(!waiting.is_finished());
        drop(first);
        tokio::task::yield_now().await;
        assert!(!waiting.is_finished());
        drop(second);
        tokio::time::timeout(Duration::from_secs(1), waiting)
            .await
            .unwrap()
            .unwrap()
            .unwrap();
        assert_eq!(slots.available_permits(), 2);
    }

    #[tokio::test]
    async fn connection_drain_releases_after_task_panic_and_drop() {
        let transport = OpenLabTransport::bind(
            "127.0.0.1:0".parse().unwrap(),
            TransportLimits {
                max_concurrent_connections: 1,
            },
        )
        .await
        .unwrap();
        let permit = transport
            .connection_slots
            .clone()
            .acquire_owned()
            .await
            .unwrap();
        let drain = transport.drain_handle();
        drop(transport);
        let task = tokio::spawn(async move {
            let _held = permit;
            panic!("synthetic isolated connection panic");
        });
        assert!(task.await.unwrap_err().is_panic());
        tokio::time::timeout(Duration::from_secs(1), drain.wait())
            .await
            .unwrap()
            .unwrap();
    }

    #[tokio::test]
    async fn cancelled_drain_does_not_leak_permits_or_report_completion() {
        let transport = OpenLabTransport::bind(
            "127.0.0.1:0".parse().unwrap(),
            TransportLimits {
                max_concurrent_connections: 1,
            },
        )
        .await
        .unwrap();
        let slots = transport.connection_slots.clone();
        let held = slots.clone().acquire_owned().await.unwrap();
        let drain = transport.drain_handle();
        drop(transport);
        assert!(
            tokio::time::timeout(Duration::from_millis(5), drain.clone().wait())
                .await
                .is_err()
        );
        assert_eq!(slots.available_permits(), 0);
        drop(held);
        drain.wait().await.unwrap();
        assert_eq!(slots.available_permits(), 1);
    }

    #[tokio::test]
    async fn open_lab_transport_rejects_non_loopback_bind() {
        let error = OpenLabTransport::bind(
            "0.0.0.0:1883".parse().unwrap(),
            TransportLimits {
                max_concurrent_connections: 1,
            },
        )
        .await
        .err()
        .expect("non-loopback open-lab bind must fail");
        assert_eq!(error.kind(), std::io::ErrorKind::InvalidInput);
    }
}
