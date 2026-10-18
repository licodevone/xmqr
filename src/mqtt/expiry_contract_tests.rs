// SPDX-License-Identifier: MIT
//! P227E: durable expiry permission must still be current at the first write.
//! The wire oracle below does not use the broker's encoder or decoder.

use super::*;
use crate::persistence::faults::{Action, Fault, Point};
use clock::{ExpiryClock, ManualTime};
use std::sync::atomic::AtomicUsize;
use tokio::{
    io::{AsyncReadExt, AsyncWriteExt},
    net::{TcpListener, TcpStream},
    time::timeout,
};

const PRINCIPAL: &str = "__open_lab__";
const PEER: &str = "expiry-peer";
const TOPIC: &str = "test/state";

type ExpiryHook = Arc<dyn Fn() -> Duration + Send + Sync>;

struct Fixture {
    directory: tempfile::TempDir,
    router: Router,
    auth: Arc<AccessPolicy>,
    metrics: Arc<Metrics>,
    input: Arc<ManualTime>,
    session: router::Session,
    connection: BrokerConnection,
    peer: TcpStream,
    delivery: Delivery,
    packet_id: u16,
    delivery_id: u64,
    baseline_commits: u64,
}

impl Fixture {
    async fn new() -> Self {
        // Native private storage; neither /tmp tmpfs nor any operator state.
        let directory = tempfile::Builder::new()
            .prefix("xmqr-p227e-send-")
            .tempdir_in("/var/tmp")
            .unwrap();
        let auth = Arc::new(AccessPolicy::open_lab());
        let metrics = Arc::new(Metrics::default());
        let (clock, input) = ExpiryClock::manual(10_000, 0);
        let router = Router::start_with_expiry_clock_for_test(
            directory.path(),
            auth.clone(),
            metrics.clone(),
            StateLimits::default(),
            clock,
        )
        .await
        .unwrap();
        let mut session = router
            .register(PEER.into(), PRINCIPAL.into(), false)
            .await
            .unwrap();
        let (reasons, retained) = router
            .subscribe(
                &session,
                vec![(
                    topic::TopicFilter::try_from(TOPIC.to_owned()).unwrap(),
                    Some(1),
                )],
            )
            .await
            .unwrap();
        assert_eq!(reasons, [1]);
        assert!(retained.is_empty());
        let publisher = router
            .register("expiry-source".into(), PRINCIPAL.into(), true)
            .await
            .unwrap();
        router
            .publish(&publisher, message(), Some(9))
            .await
            .unwrap();
        let delivery = timeout(Duration::from_secs(3), session.outbound.recv())
            .await
            .unwrap()
            .expect("real routed copy");
        let Delivery::Publish {
            message,
            packet_id: Some(packet_id),
            dup: false,
        } = &delivery
        else {
            panic!("expected first-attempt QoS1 copy");
        };
        let packet_id = *packet_id;
        let delivery_id = message.expiry_delivery_id.expect("unique prepared copy");
        input.set(1_000, 3_000); // UTC regressed; logical time is still 13_000.
        let (connection, peer) = private_connection().await;
        let baseline_commits = metrics.commits.load(Ordering::Relaxed);
        Self {
            directory,
            router,
            auth,
            metrics,
            input,
            session,
            connection,
            peer,
            delivery,
            packet_id,
            delivery_id,
            baseline_commits,
        }
    }

    fn hook(&mut self, steps: Vec<u64>, delay: Duration) -> Arc<AtomicUsize> {
        let calls = Arc::new(AtomicUsize::new(0));
        let observed = calls.clone();
        let input = self.input.clone();
        let hook: ExpiryHook = Arc::new(move || {
            let index = observed.fetch_add(1, Ordering::SeqCst);
            let elapsed = *steps.get(index).expect("unexpected extra expiry attempt");
            input.set(1_000, elapsed);
            delay
        });
        self.router = self.router.clone().with_expiry_hook_for_test(hook);
        calls
    }

    async fn send(&mut self) -> Result<(), HandlerError> {
        let mut aliases = OutboundAliases {
            maximum: 0,
            topics: HashMap::new(),
        };
        timeout(
            Duration::from_secs(5),
            send_delivery(
                &mut self.connection,
                self.delivery.clone(),
                &self.metrics,
                &self.auth,
                PRINCIPAL,
                self.auth.security_generation(),
                true,
                65_536,
                &mut aliases,
                &self.router,
                &self.session,
            ),
        )
        .await
        .expect("expiry refresh must finish within its finite budget")
    }

    fn assert_commits_and_sent(&self, commits: u64, sent: u64) {
        assert_eq!(
            self.metrics.commits.load(Ordering::Relaxed) - self.baseline_commits,
            commits
        );
        assert_eq!(self.metrics.sent[1].load(Ordering::Relaxed), sent);
    }

    async fn assert_recovered(&self, phase: store::OutboundTransmission, floor: u64) {
        self.router.stop_for_test().await;
        let (store, state) = timeout(Duration::from_secs(3), async {
            loop {
                match store::MqttStore::open(self.directory.path()).await {
                    Ok(recovered) => break recovered,
                    Err(store::StateError::Storage(
                        crate::persistence::StorageError::AlreadyOpen,
                    )) => tokio::time::sleep(Duration::from_millis(5)).await,
                    Err(error) => panic!("private recovery failed: {error}"),
                }
            }
        })
        .await
        .expect("writer must release the private lock");
        let outbound = &state.sessions[PEER].outbound;
        assert_eq!(outbound.len(), 1, "unacknowledged obligation must survive");
        let entry = &outbound[0];
        assert_eq!(entry.packet_id, self.packet_id);
        assert_eq!(entry.transmission, phase);
        assert_eq!(entry.stage, store::OutboundStage::AwaitPubAck);
        assert_eq!(entry.message.expiry_delivery_id, Some(self.delivery_id));
        assert_eq!(entry.message.expiry_at_unix_ms, Some(20_000));
        assert_eq!(entry.message.expiry_interval_seconds, Some(10));
        assert_eq!(entry.message.payload, [42]);
        assert!(state.expiry_clock_unix_ms >= floor);
        store.shutdown().await.unwrap();
    }
}

fn message() -> StoredMessage {
    StoredMessage {
        topic: topic::TopicName::try_from(TOPIC.to_owned()).unwrap(),
        payload: vec![42],
        qos: 1,
        retain: false,
        expiry_at_unix_ms: Some(20_000),
        expiry_interval_seconds: Some(10),
        expiry_delivery_id: None,
        payload_format_indicator: None,
        content_type: None,
        response_topic: None,
        correlation_data: None,
        user_properties: Vec::new(),
        subscription_identifiers: Vec::new(),
        shared_origin: None,
    }
}

async fn private_connection() -> (BrokerConnection, TcpStream) {
    let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
    let mut peer = TcpStream::connect(listener.local_addr().unwrap())
        .await
        .unwrap();
    let (stream, _) = listener.accept().await.unwrap();
    // Satisfy the transport's initial-byte admission, not an MQTT parser oracle.
    peer.write_all(&[0]).await.unwrap();
    let connection = timeout(
        Duration::from_secs(3),
        BrokerConnection::open_lab_for_test(stream),
    )
    .await
    .unwrap()
    .unwrap();
    (connection, peer)
}

async fn no_bytes(peer: &mut TcpStream) {
    let mut bytes = [0; 64];
    match timeout(Duration::from_millis(100), peer.read(&mut bytes)).await {
        Err(_) | Ok(Ok(0)) => {}
        Ok(Err(error)) => assert_eq!(error.kind(), std::io::ErrorKind::ConnectionReset),
        Ok(Ok(count)) => panic!("unexpected {count} bytes without a current expiry permission"),
    }
}

async fn exact_publish(peer: &mut TcpStream, packet_id: u16, expiry: u32) {
    // MQTT5 QoS1, full topic, one Message Expiry property, one payload byte.
    // 2+10(topic) +2(id) +1(properties length) +5(property) +1(payload) =21.
    let mut expected = vec![0x32, 21, 0, 10];
    expected.extend_from_slice(b"test/state");
    expected.extend_from_slice(&packet_id.to_be_bytes());
    expected.extend_from_slice(&[5, 0x02]);
    expected.extend_from_slice(&expiry.to_be_bytes());
    expected.push(42);
    let mut actual = vec![0; expected.len()];
    timeout(Duration::from_secs(1), peer.read_exact(&mut actual))
        .await
        .unwrap()
        .unwrap();
    assert_eq!(actual, expected, "independent exact MQTT5 wire oracle");
    no_bytes(peer).await;
}

#[tokio::test]
async fn p227e_send_same_bucket_commits_once_and_writes_current_ttl() {
    let mut fixture = Fixture::new().await;
    let calls = fixture.hook(vec![3_500], Duration::ZERO);
    fixture.send().await.unwrap();
    assert_eq!(calls.load(Ordering::SeqCst), 1);
    fixture.assert_commits_and_sent(1, 1);
    exact_publish(&mut fixture.peer, fixture.packet_id, 7).await;
    fixture
        .assert_recovered(store::OutboundTransmission::MayHaveSent, 13_000)
        .await;
}

#[tokio::test]
async fn p227e_send_crossed_bucket_commits_again_and_reencodes_lower_ttl() {
    let mut fixture = Fixture::new().await;
    let calls = fixture.hook(vec![4_000, 4_500], Duration::ZERO);
    fixture.send().await.unwrap();
    assert_eq!(calls.load(Ordering::SeqCst), 2);
    fixture.assert_commits_and_sent(2, 1);
    exact_publish(&mut fixture.peer, fixture.packet_id, 6).await;
    fixture
        .assert_recovered(store::OutboundTransmission::MayHaveSent, 14_000)
        .await;
}

#[tokio::test]
async fn p227e_send_four_crossings_fail_bounded_without_any_write() {
    let mut fixture = Fixture::new().await;
    let calls = fixture.hook(vec![4_000, 5_000, 6_000, 7_000], Duration::ZERO);
    let error = fixture.send().await.unwrap_err();
    assert!(
        error
            .to_string()
            .contains("expiry checkpoint refresh limit")
    );
    assert_eq!(calls.load(Ordering::SeqCst), 4);
    fixture.assert_commits_and_sent(4, 0);
    no_bytes(&mut fixture.peer).await;
    fixture
        .assert_recovered(store::OutboundTransmission::MayHaveSent, 16_000)
        .await;
}

#[tokio::test]
async fn p227e_send_encode_delay_past_deadline_never_writes() {
    let mut fixture = Fixture::new().await;
    let calls = fixture.hook(vec![3_500], Duration::from_millis(3_100));
    let error = fixture.send().await.unwrap_err();
    assert!(error.to_string().contains("expiry checkpoint deadline"));
    assert_eq!(calls.load(Ordering::SeqCst), 1);
    fixture.assert_commits_and_sent(1, 0);
    no_bytes(&mut fixture.peer).await;
    fixture
        .assert_recovered(store::OutboundTransmission::MayHaveSent, 13_000)
        .await;
}

#[tokio::test]
async fn p227e_send_wal_error_has_no_permission_and_recovers_prepared() {
    let mut fixture = Fixture::new().await;
    let calls = fixture.hook(vec![3_500], Duration::ZERO);
    // Deterministic failure before append, not uncertain fsync/rollback claims.
    fixture
        .router
        .inject_for_test(Fault {
            point: Point::WalAppend,
            action: Action::Error(28),
        })
        .await
        .unwrap();
    assert!(fixture.send().await.is_err());
    assert_eq!(
        calls.load(Ordering::SeqCst),
        0,
        "encoding was not authorized"
    );
    fixture.assert_commits_and_sent(0, 0);
    assert_eq!(
        fixture.metrics.persistence_errors.load(Ordering::Relaxed),
        1
    );
    no_bytes(&mut fixture.peer).await;
    fixture
        .assert_recovered(store::OutboundTransmission::Prepared, 10_000)
        .await;
}

#[tokio::test]
async fn p227e_send_permission_then_expiry_preserves_uncertain_obligation() {
    let mut fixture = Fixture::new().await;
    let calls = fixture.hook(vec![20_000], Duration::ZERO);
    // Permit R7 was durable before the hook. The later R0 cannot turn this
    // MayHaveSent obligation back into discardable Prepared, even though the
    // queued Delivery still has DUP0 and this transport has written no byte.
    assert!(fixture.send().await.is_err());
    assert_eq!(calls.load(Ordering::SeqCst), 1);
    fixture.assert_commits_and_sent(2, 0);
    no_bytes(&mut fixture.peer).await;
    fixture
        .assert_recovered(store::OutboundTransmission::MayHaveSent, 30_000)
        .await;
}
