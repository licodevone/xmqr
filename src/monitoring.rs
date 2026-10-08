//! Optional loopback-only HTTP monitoring with bounded requests and fixed labels.
use crate::mqtt::Router;
use std::{
    env,
    fmt::Write as _,
    io,
    net::SocketAddr,
    sync::{
        Arc,
        atomic::{AtomicBool, AtomicU64, Ordering},
    },
    time::Duration,
};
use tokio::{
    io::{AsyncReadExt, AsyncWriteExt},
    net::{TcpListener, TcpStream},
    sync::Semaphore,
    task::{JoinHandle, JoinSet},
    time::timeout,
};

const HEADER_LIMIT: usize = 4096;
const HTTP_CONNECTIONS: usize = 16;
const IO_TIMEOUT: Duration = Duration::from_secs(1);
const PROBE_TIMEOUT: Duration = Duration::from_millis(500);
const REASONS: [&str; 7] = [
    "authentication",
    "authorization",
    "quota",
    "admission",
    "delivery",
    "persistence",
    "transport",
];

#[derive(Clone, Copy)]
pub(crate) enum Rejection {
    Authentication,
    Authorization,
    Quota,
    Admission,
    Delivery,
    Persistence,
    Transport,
}

/// Process-local counters. No topic, principal, payload or client identifiers.
#[derive(Default)]
pub struct Metrics {
    pub(crate) connections_active: AtomicU64,
    pub(crate) connections_total: AtomicU64,
    pub(crate) tcp_accepted: AtomicU64,
    pub(crate) received: [AtomicU64; 3],
    pub(crate) sent: [AtomicU64; 3],
    rejected: [AtomicU64; 7],
    pub(crate) commits: AtomicU64,
    pub(crate) commit_attempts: AtomicU64,
    pub(crate) commit_nanos: AtomicU64,
    pub(crate) persistence_errors: AtomicU64,
    pub(crate) snapshots: AtomicU64,
    pub(crate) wills: AtomicU64,
    pub(crate) offline: AtomicU64,
    pub(crate) inflight: AtomicU64,
    pub(crate) deliveries_queued: AtomicU64,
    pub(crate) commands_queued: AtomicU64,
    pub(crate) sessions: AtomicU64,
    pub(crate) retained: AtomicU64,
    pub(crate) actor_alive: AtomicBool,
    listener_ready: AtomicBool,
    ready: AtomicBool,
    http_rejected: AtomicU64,
}

impl Metrics {
    /// Mark the MQTT listener available or unavailable, independently of HTTP.
    pub fn set_listener_ready(&self, value: bool) {
        self.listener_ready.store(value, Ordering::Relaxed);
        if !value {
            self.ready.store(false, Ordering::Relaxed);
        }
    }
    pub(crate) fn reject(&self, reason: Rejection) {
        self.rejected[reason as usize].fetch_add(1, Ordering::Relaxed);
    }
    pub(crate) fn connection(self: &Arc<Self>) -> ConnectionMetric {
        self.connections_active.fetch_add(1, Ordering::Relaxed);
        self.connections_total.fetch_add(1, Ordering::Relaxed);
        ConnectionMetric(self.clone())
    }
    pub(crate) fn actor(self: &Arc<Self>) -> ActorMetric {
        self.actor_alive.store(true, Ordering::Relaxed);
        ActorMetric(self.clone())
    }
    fn render_scalars(&self, s: &mut String) {
        for (name, kind, value) in [
            (
                "xmqr_connections_active",
                "gauge",
                self.connections_active.load(Ordering::Relaxed),
            ),
            (
                "xmqr_connections_total",
                "counter",
                self.connections_total.load(Ordering::Relaxed),
            ),
            (
                "xmqr_tcp_accepted_total",
                "counter",
                self.tcp_accepted.load(Ordering::Relaxed),
            ),
            (
                "xmqr_persistence_commits_total",
                "counter",
                self.commits.load(Ordering::Relaxed),
            ),
            (
                "xmqr_persistence_commit_attempts_total",
                "counter",
                self.commit_attempts.load(Ordering::Relaxed),
            ),
            (
                "xmqr_persistence_errors_total",
                "counter",
                self.persistence_errors.load(Ordering::Relaxed),
            ),
            (
                "xmqr_persistence_snapshots_total",
                "counter",
                self.snapshots.load(Ordering::Relaxed),
            ),
            (
                "xmqr_wills_published_total",
                "counter",
                self.wills.load(Ordering::Relaxed),
            ),
            (
                "xmqr_offline_messages",
                "gauge",
                self.offline.load(Ordering::Relaxed),
            ),
            (
                "xmqr_inflight_messages",
                "gauge",
                self.inflight.load(Ordering::Relaxed),
            ),
            (
                "xmqr_delivery_messages_queued",
                "gauge",
                self.deliveries_queued.load(Ordering::Relaxed),
            ),
            (
                "xmqr_router_commands_queued",
                "gauge",
                self.commands_queued.load(Ordering::Relaxed),
            ),
            (
                "xmqr_sessions",
                "gauge",
                self.sessions.load(Ordering::Relaxed),
            ),
            (
                "xmqr_retained_messages",
                "gauge",
                self.retained.load(Ordering::Relaxed),
            ),
            (
                "xmqr_ready",
                "gauge",
                u64::from(self.ready.load(Ordering::Relaxed)),
            ),
            (
                "xmqr_monitor_rejected_total",
                "counter",
                self.http_rejected.load(Ordering::Relaxed),
            ),
        ] {
            let _ = writeln!(s, "# TYPE {name} {kind}\n{name} {value}");
        }
    }
    fn render(&self) -> String {
        let mut s = String::with_capacity(4096);
        self.render_scalars(&mut s);
        for (name, counts) in [
            ("xmqr_messages_received_total", &self.received),
            ("xmqr_messages_sent_total", &self.sent),
        ] {
            let _ = writeln!(s, "# TYPE {name} counter");
            for (qos, count) in counts.iter().enumerate() {
                let _ = writeln!(
                    s,
                    "{name}{{qos=\"{qos}\"}} {}",
                    count.load(Ordering::Relaxed)
                );
            }
        }
        let _ = writeln!(s, "# TYPE xmqr_rejections_total counter");
        for (reason, count) in REASONS.iter().zip(&self.rejected) {
            let _ = writeln!(
                s,
                "xmqr_rejections_total{{reason=\"{reason}\"}} {}",
                count.load(Ordering::Relaxed)
            );
        }
        let nanos = self.commit_nanos.load(Ordering::Relaxed);
        let _ = writeln!(
            s,
            "# TYPE xmqr_persistence_commit_duration_seconds summary\nxmqr_persistence_commit_duration_seconds_sum {}.{:09}\nxmqr_persistence_commit_duration_seconds_count {}",
            nanos / 1_000_000_000,
            nanos % 1_000_000_000,
            self.commit_attempts.load(Ordering::Relaxed)
        );
        s
    }
}
pub(crate) struct ConnectionMetric(Arc<Metrics>);
impl Drop for ConnectionMetric {
    fn drop(&mut self) {
        self.0.connections_active.fetch_sub(1, Ordering::Relaxed);
    }
}
pub(crate) struct ActorMetric(Arc<Metrics>);
impl Drop for ActorMetric {
    fn drop(&mut self) {
        self.0.actor_alive.store(false, Ordering::Relaxed);
        self.0.ready.store(false, Ordering::Relaxed);
    }
}

/// Disabled by default; explicitly enabled monitoring remains loopback-only.
#[derive(Clone, Debug)]
pub struct Config {
    pub enabled: bool,
    pub bind: SocketAddr,
}
impl Config {
    /// Load `MQTT_MONITOR_ENABLED` and `MQTT_MONITOR_BIND`.
    /// # Errors
    /// Rejects malformed variables, remote addresses and port zero.
    pub fn from_env() -> io::Result<Self> {
        let enabled = env::var("MQTT_MONITOR_ENABLED").map_err(|e| {
            if matches!(e, env::VarError::NotPresent) {
                io::Error::new(io::ErrorKind::NotFound, "unset")
            } else {
                io::Error::new(io::ErrorKind::InvalidInput, "invalid monitoring variable")
            }
        });
        let bind = env::var("MQTT_MONITOR_BIND");
        if matches!(bind, Err(env::VarError::NotUnicode(_))) {
            return Err(invalid("invalid monitoring address"));
        }
        match enabled {
            Ok(value) => Self::parse(Some(&value), bind.as_deref().ok()),
            Err(e) if e.kind() == io::ErrorKind::NotFound => {
                Self::parse(None, bind.as_deref().ok())
            }
            Err(e) => Err(e),
        }
    }
    fn parse(enabled: Option<&str>, bind: Option<&str>) -> io::Result<Self> {
        let enabled = match enabled {
            None | Some("false") => false,
            Some("true") => true,
            _ => return Err(invalid("MQTT_MONITOR_ENABLED must be true or false")),
        };
        let bind: SocketAddr = bind
            .unwrap_or("127.0.0.1:9090")
            .parse()
            .map_err(|_| invalid("invalid monitoring bind"))?;
        if !bind.ip().is_loopback() || bind.port() == 0 {
            return Err(invalid(
                "monitoring requires a loopback address and nonzero port",
            ));
        }
        Ok(Self { enabled, bind })
    }
}
fn invalid(message: &'static str) -> io::Error {
    io::Error::new(io::ErrorKind::InvalidInput, message)
}

/// Stops the monitoring listener and its requests when dropped; no MQTT shutdown.
pub struct Monitor {
    task: JoinHandle<()>,
    metrics: Arc<Metrics>,
}
impl Monitor {
    /// Start bounded HTTP when explicitly enabled. No authentication/TLS fallback.
    /// # Errors
    /// Returns address validation or bind errors before normal serving starts.
    pub async fn start(
        config: &Config,
        metrics: Arc<Metrics>,
        router: Arc<Router>,
    ) -> io::Result<Option<Self>> {
        if !config.enabled {
            return Ok(None);
        }
        if !config.bind.ip().is_loopback() {
            return Err(invalid("monitoring must bind loopback"));
        }
        let listener = TcpListener::bind(config.bind).await?;
        Ok(Some(Self::from_listener(listener, metrics, router)))
    }
    fn from_listener(listener: TcpListener, metrics: Arc<Metrics>, router: Arc<Router>) -> Self {
        let owned = metrics.clone();
        let task = tokio::spawn(async move {
            let slots = Arc::new(Semaphore::new(HTTP_CONNECTIONS));
            let mut clients = JoinSet::new();
            loop {
                tokio::select! {
                    result=listener.accept()=>{
                        let Ok((stream,_))=result else {tracing::warn!("monitor listener failed; MQTT continues");break;};
                        let Ok(permit)=slots.clone().try_acquire_owned() else {owned.http_rejected.fetch_add(1,Ordering::Relaxed);drop(stream);continue;};
                        let metrics=owned.clone();let router=router.clone();
                        clients.spawn(async move {let _permit=permit;let _=serve_http(stream,metrics,router).await;});
                    }
                    _=clients.join_next(),if !clients.is_empty()=>{}
                }
            }
        });
        Self { task, metrics }
    }
}
impl Drop for Monitor {
    fn drop(&mut self) {
        self.metrics.ready.store(false, Ordering::Relaxed);
        self.task.abort();
    }
}

enum RequestError {
    Invalid,
    TooLarge,
    Timeout,
}
async fn header(stream: &mut TcpStream) -> Result<Vec<u8>, RequestError> {
    let read = async {
        let mut data = Vec::with_capacity(HEADER_LIMIT);
        let mut buffer = [0_u8; 512];
        loop {
            let remaining = HEADER_LIMIT - data.len();
            if remaining == 0 {
                return Err(RequestError::TooLarge);
            }
            let n = stream
                .read(&mut buffer[..remaining.min(512)])
                .await
                .map_err(|_| RequestError::Invalid)?;
            if n == 0 {
                return Err(RequestError::Invalid);
            }
            data.extend_from_slice(&buffer[..n]);
            if data.windows(4).any(|w| w == b"\r\n\r\n") {
                return Ok(data);
            }
        }
    };
    timeout(IO_TIMEOUT, read)
        .await
        .map_err(|_| RequestError::Timeout)?
}
fn route(data: &[u8]) -> Result<&str, u16> {
    let text = std::str::from_utf8(data).map_err(|_| 400_u16)?;
    let first = text.split("\r\n").next().ok_or(400_u16)?;
    let parts: Vec<_> = first.split(' ').collect();
    if parts.len() != 3 || !matches!(parts[2], "HTTP/1.0" | "HTTP/1.1") {
        return Err(400);
    }
    if parts[0] != "GET" {
        return Err(405);
    }
    for line in text.split("\r\n").skip(1).take_while(|l| !l.is_empty()) {
        let Some((name, value)) = line.split_once(':') else {
            return Err(400);
        };
        if name.eq_ignore_ascii_case("transfer-encoding")
            || (name.eq_ignore_ascii_case("content-length") && value.trim() != "0")
        {
            return Err(400);
        }
    }
    Ok(parts[1])
}
async fn serve_http(
    mut stream: TcpStream,
    metrics: Arc<Metrics>,
    router: Arc<Router>,
) -> io::Result<()> {
    let input = header(&mut stream).await;
    let (status, body, prometheus) = match input {
        Err(error) => {
            metrics.http_rejected.fetch_add(1, Ordering::Relaxed);
            (
                match error {
                    RequestError::Invalid => 400,
                    RequestError::TooLarge => 431,
                    RequestError::Timeout => 408,
                },
                "invalid request\n".to_owned(),
                false,
            )
        }
        Ok(data) => match route(&data) {
            Ok("/health") => (200, "ok\n".to_owned(), false),
            Ok(path @ ("/ready" | "/metrics")) => {
                let ready = matches!(timeout(PROBE_TIMEOUT, router.probe()).await, Ok(true))
                    && metrics.listener_ready.load(Ordering::Relaxed);
                metrics.ready.store(ready, Ordering::Relaxed);
                if path == "/metrics" {
                    (200, metrics.render(), true)
                } else {
                    (
                        if ready { 200 } else { 503 },
                        if ready { "ready\n" } else { "not ready\n" }.to_owned(),
                        false,
                    )
                }
            }
            Ok(_) => (404, "not found\n".to_owned(), false),
            Err(code) => {
                metrics.http_rejected.fetch_add(1, Ordering::Relaxed);
                (code, "invalid request\n".to_owned(), false)
            }
        },
    };
    let reason = match status {
        200 => "OK",
        400 => "Bad Request",
        404 => "Not Found",
        405 => "Method Not Allowed",
        408 => "Request Timeout",
        431 => "Request Header Fields Too Large",
        _ => "Service Unavailable",
    };
    let content_type = if prometheus {
        "text/plain; version=0.0.4; charset=utf-8"
    } else {
        "text/plain; charset=utf-8"
    };
    let response = format!(
        "HTTP/1.1 {status} {reason}\r\nContent-Type: {content_type}\r\nContent-Length: {}\r\nConnection: close\r\nCache-Control: no-store\r\n\r\n{body}",
        body.len()
    );
    timeout(IO_TIMEOUT, stream.write_all(response.as_bytes()))
        .await
        .map_err(|_| io::Error::new(io::ErrorKind::TimedOut, "monitor response timeout"))??;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn config_and_http_parser_reject_remote_and_body_requests() {
        let default = Config::parse(None, None).unwrap();
        assert!(!default.enabled);
        assert_eq!(default.bind, "127.0.0.1:9090".parse().unwrap());
        assert!(Config::parse(Some("true"), Some("0.0.0.0:9090")).is_err());
        assert!(Config::parse(Some("yes"), None).is_err());
        assert!(Config::parse(Some("true"), Some("127.0.0.1:0")).is_err());
        assert_eq!(
            route(b"GET /health HTTP/1.1\r\nHost: local\r\n\r\n").unwrap(),
            "/health"
        );
        assert_eq!(route(b"POST /ready HTTP/1.1\r\n\r\n"), Err(405));
        assert_eq!(
            route(b"GET /ready HTTP/1.1\r\nContent-Length: 99\r\n\r\n"),
            Err(400)
        );
        assert_eq!(
            route(b"GET /ready HTTP/1.1\r\nTransfer-Encoding: chunked\r\n\r\n"),
            Err(400)
        );
    }
    #[test]
    fn metrics_are_fixed_cardinality_and_connection_gauge_drains() {
        let metrics = Arc::new(Metrics::default());
        {
            let _guard = metrics.connection();
            assert_eq!(metrics.connections_active.load(Ordering::Relaxed), 1);
        }
        assert_eq!(metrics.connections_active.load(Ordering::Relaxed), 0);
        metrics.reject(Rejection::Authorization);
        let rendered = metrics.render();
        assert!(rendered.contains("reason=\"authorization\"} 1"));
        assert_eq!(
            rendered
                .lines()
                .filter(|l| l.starts_with("xmqr_rejections_total{"))
                .count(),
            7
        );
        assert!(!rendered.contains("username"));
        assert!(!rendered.contains("topic"));
    }
    async fn request(address: SocketAddr, path: &str) -> String {
        let mut stream = TcpStream::connect(address).await.unwrap();
        stream
            .write_all(format!("GET {path} HTTP/1.1\r\nHost: local\r\n\r\n").as_bytes())
            .await
            .unwrap();
        let mut bytes = Vec::new();
        stream.read_to_end(&mut bytes).await.unwrap();
        String::from_utf8(bytes).unwrap()
    }

    #[tokio::test]
    async fn endpoints_detect_actor_stop_and_monitor_teardown() {
        let directory = tempfile::tempdir().unwrap();
        let metrics = Arc::new(Metrics::default());
        let router = Arc::new(
            Router::start_observed(
                directory.path(),
                Arc::new(crate::auth::AccessPolicy::open_lab()),
                metrics.clone(),
            )
            .await
            .unwrap(),
        );
        let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let address = listener.local_addr().unwrap();
        let monitor = Monitor::from_listener(listener, metrics.clone(), router.clone());
        assert!(
            request(address, "/health")
                .await
                .starts_with("HTTP/1.1 200")
        );
        assert!(request(address, "/ready").await.starts_with("HTTP/1.1 503"));
        metrics.set_listener_ready(true);
        assert!(request(address, "/ready").await.starts_with("HTTP/1.1 200"));
        router.stop_for_test().await;
        assert!(request(address, "/ready").await.starts_with("HTTP/1.1 503"));
        assert!(
            request(address, "/health")
                .await
                .starts_with("HTTP/1.1 200")
        );
        drop(monitor);
        tokio::task::yield_now().await;
        assert!(TcpStream::connect(address).await.is_err());
    }
}
