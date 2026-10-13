// SPDX-License-Identifier: MIT
//! Independent MQTT bytes traverse the real TCP/handler/router/writer path.

use super::*;
use crate::persistence::faults::{Action, Fault, Point};
use tokio::{
    io::{AsyncReadExt, AsyncWriteExt},
    net::{TcpListener, TcpStream},
    task::JoinSet,
    time::timeout,
};

fn connect(id: &str, clean: bool) -> Vec<u8> {
    let mut bytes = vec![
        0x10,
        u8::try_from(12 + id.len()).unwrap(),
        0,
        4,
        b'M',
        b'Q',
        b'T',
        b'T',
        4,
        if clean { 2 } else { 0 },
        0,
        30,
    ];
    bytes.extend(u16::try_from(id.len()).unwrap().to_be_bytes());
    bytes.extend(id.as_bytes());
    bytes
}

fn publish(qos: u8, payload: &[u8]) -> Vec<u8> {
    let mut bytes = vec![
        0x31 | (qos << 1),
        u8::try_from(2 + 12 + 2 + payload.len()).unwrap(),
        0,
        12,
    ];
    bytes.extend(b"test/storage");
    bytes.extend([0, 7]);
    bytes.extend(payload);
    bytes
}

async fn expected(stream: &mut TcpStream, bytes: &[u8]) {
    let mut actual = vec![0; bytes.len()];
    timeout(Duration::from_secs(3), stream.read_exact(&mut actual))
        .await
        .unwrap()
        .unwrap();
    assert_eq!(actual, bytes);
}

async fn closed_without_any_ack_or_delivery(stream: &mut TcpStream) {
    let mut bytes = [0; 64];
    match timeout(Duration::from_secs(3), stream.read(&mut bytes))
        .await
        .unwrap()
    {
        Ok(count) => assert_eq!(count, 0, "unexpected MQTT bytes after failed commit"),
        Err(error) => assert_eq!(error.kind(), std::io::ErrorKind::ConnectionReset),
    }
}

#[derive(Clone, Copy, Debug)]
enum Phase {
    Qos1,
    Qos2Publish,
    Qos2Release,
}

#[allow(clippy::too_many_lines)]
async fn failed_commit_case(phase: Phase, fault: Fault) {
    let directory = tempfile::tempdir().unwrap();
    let auth = Arc::new(AccessPolicy::open_lab());
    let router = Arc::new(Router::start(directory.path(), auth.clone()).await.unwrap());
    let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
    let address = listener.local_addr().unwrap();
    let handler_router = router.clone();
    let server = tokio::spawn(async move {
        let mut handlers = JoinSet::new();
        for _ in 0..2 {
            let (stream, _) = listener.accept().await.unwrap();
            let router = handler_router.clone();
            let auth = auth.clone();
            handlers.spawn(async move {
                let connection = BrokerConnection::open_lab_for_test(stream).await.unwrap();
                // Failure is expected; join still verifies no task panic.
                let _ = serve_connection(connection, auth, router).await;
            });
        }
        while let Some(result) = handlers.join_next().await {
            result.unwrap();
        }
    });
    let mut publisher = TcpStream::connect(address).await.unwrap();
    publisher
        .write_all(&connect("publisher", false))
        .await
        .unwrap();
    expected(&mut publisher, &[0x20, 2, 0, 0]).await;
    publisher.write_all(&publish(1, b"base")).await.unwrap();
    expected(&mut publisher, &[0x40, 2, 0, 7]).await;
    let mut observer = TcpStream::connect(address).await.unwrap();
    observer
        .write_all(&connect("observer", true))
        .await
        .unwrap();
    expected(&mut observer, &[0x20, 2, 0, 0]).await;
    let mut subscribe = vec![0x82, 17, 0, 1, 0, 12];
    subscribe.extend(b"test/storage");
    subscribe.push(0); // QoS0 prevents observer ACKs from consuming our fault.
    observer.write_all(&subscribe).await.unwrap();
    expected(&mut observer, &[0x90, 3, 0, 1, 0]).await;
    let mut retained = vec![0x31, 18, 0, 12];
    retained.extend(b"test/storage");
    retained.extend(b"base");
    expected(&mut observer, &retained).await;
    if matches!(phase, Phase::Qos2Release) {
        publisher
            .write_all(&publish(2, b"candidate"))
            .await
            .unwrap();
        expected(&mut publisher, &[0x50, 2, 0, 7]).await;
    }
    let commits = router.metrics().commits.load(Ordering::Relaxed);
    router.inject_for_test(fault).await.unwrap();
    let packet = match phase {
        Phase::Qos1 => publish(1, b"candidate"),
        Phase::Qos2Publish => publish(2, b"candidate"),
        Phase::Qos2Release => vec![0x62, 2, 0, 7],
    };
    publisher.write_all(&packet).await.unwrap();
    closed_without_any_ack_or_delivery(&mut publisher).await;
    closed_without_any_ack_or_delivery(&mut observer).await;
    timeout(Duration::from_secs(3), server)
        .await
        .unwrap()
        .unwrap();
    assert!(!router.probe().await);
    assert_eq!(router.metrics().commits.load(Ordering::Relaxed), commits);
    assert_eq!(
        router.metrics().persistence_errors.load(Ordering::Relaxed),
        1
    );
    // Actor exit closes the writer mailbox; wait boundedly for its lock release.
    let (store, recovered) = timeout(Duration::from_secs(3), async {
        loop {
            match store::MqttStore::open(directory.path()).await {
                Ok(recovered) => break recovered,
                Err(store::StateError::Storage(crate::persistence::StorageError::AlreadyOpen)) => {
                    tokio::time::sleep(Duration::from_millis(5)).await;
                }
                Err(error) => panic!("recovery failed: {error}"),
            }
        }
    })
    .await
    .unwrap();
    let complete = fault.point == Point::WalSync;
    let retained_changed = complete && !matches!(phase, Phase::Qos2Publish);
    assert_eq!(
        recovered.retained["test/storage"].payload,
        if retained_changed {
            b"candidate".as_slice()
        } else {
            b"base".as_slice()
        }
    );
    let pending_qos2 = matches!(phase, Phase::Qos2Publish) && complete
        || matches!(phase, Phase::Qos2Release) && !complete;
    assert_eq!(
        recovered.sessions["publisher"].inbound_qos2.len(),
        usize::from(pending_qos2)
    );
    store.shutdown().await.unwrap();
}

#[tokio::test]
async fn disk_faults_never_emit_puback_pubrec_or_pubcomp_or_uncommitted_fanout() {
    // MQTT-4.3.2-2/4.3.3-2: ACK after ownership. fsync is XMQR's local barrier.
    for phase in [Phase::Qos1, Phase::Qos2Publish, Phase::Qos2Release] {
        for fault in [
            Fault {
                point: Point::WalAppend,
                action: Action::Error(28),
            },
            Fault {
                point: Point::WalAppend,
                action: Action::ErrorAfter(6, 5),
            },
            Fault {
                point: Point::WalSync,
                action: Action::Error(5),
            },
        ] {
            timeout(Duration::from_secs(20), failed_commit_case(phase, fault))
                .await
                .unwrap();
        }
    }
}
