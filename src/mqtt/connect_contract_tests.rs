// SPDX-License-Identifier: MIT
//! Independent CONNECT bytes exercise real TCP admission into the MQTT actor.

use super::*;
use tokio::{
    io::{AsyncReadExt, AsyncWriteExt},
    net::{TcpListener, TcpStream},
    time::timeout,
};

fn connect(id: &[u8], clean: bool, level: u8) -> Vec<u8> {
    let mut body = vec![
        0,
        4,
        b'M',
        b'Q',
        b'T',
        b'T',
        level,
        u8::from(clean) * 2,
        0,
        30,
    ];
    if level == 5 {
        body.push(0); // MQTT 5 CONNECT Properties length.
    }
    body.extend(u16::try_from(id.len()).unwrap().to_be_bytes());
    body.extend(id);
    let mut packet = vec![0x10];
    let mut length = body.len();
    loop {
        let mut digit = u8::try_from(length % 128).unwrap();
        length /= 128;
        if length != 0 {
            digit |= 128;
        }
        packet.push(digit);
        if length == 0 {
            break;
        }
    }
    packet.extend(body);
    packet
}

async fn closed(stream: &mut TcpStream) {
    let mut byte = [0];
    match timeout(Duration::from_secs(3), stream.read(&mut byte))
        .await
        .unwrap()
    {
        Ok(count) => assert_eq!(count, 0, "unexpected packet after CONNECT refusal"),
        Err(error) => assert_eq!(error.kind(), std::io::ErrorKind::ConnectionReset),
    }
}

async fn case(packet: Vec<u8>, code: Option<u8>) {
    let directory = tempfile::tempdir().unwrap();
    let auth = Arc::new(AccessPolicy::open_lab());
    let router = Arc::new(Router::start(directory.path(), auth.clone()).await.unwrap());
    let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
    let address = listener.local_addr().unwrap();
    let handler_router = router.clone();
    let server = tokio::spawn(async move {
        let (stream, _) = listener.accept().await.unwrap();
        let connection = BrokerConnection::open_lab_for_test(stream).await.unwrap();
        let _ = serve_connection(connection, auth, handler_router).await;
    });
    let mut stream = TcpStream::connect(address).await.unwrap();
    stream.write_all(&packet).await.unwrap();
    if let Some(code) = code {
        let expected: &[u8] = if code == 0x83 {
            &[0x20, 3, 0, 0x83, 0]
        } else {
            &[0x20, 2, 0, code]
        };
        let mut actual = vec![0; expected.len()];
        let result = timeout(Duration::from_secs(3), stream.read_exact(&mut actual)).await;
        assert!(
            matches!(result, Ok(Ok(_))),
            "required CONNACK missing: {result:?}"
        );
        assert_eq!(actual, expected);
        if code == 0 {
            stream.write_all(&[0xe0, 0]).await.unwrap();
        }
    }
    closed(&mut stream).await;
    timeout(Duration::from_secs(3), server)
        .await
        .unwrap()
        .unwrap();
    assert!(
        router.probe().await,
        "rejected CONNECT must not poison actor"
    );
    assert_eq!(
        router.metrics().persistence_errors.load(Ordering::Relaxed),
        0
    );
    if code != Some(0) {
        assert_eq!(router.metrics().commits.load(Ordering::Relaxed), 0);
    }
    router.shutdown().await.unwrap();
}

#[tokio::test]
async fn unsupported_level_receives_connack_one() {
    for level in [0, 3, 255] {
        case(connect(b"valid", true, level), Some(1)).await;
    }
}

#[tokio::test]
async fn mqtt5_unsupported_session_options_refused_without_commit() {
    let mut packet = connect(b"valid", false, 5);
    packet.extend([0x31, 4, 0, 1, b'x', b'y']);
    case(packet, Some(0x83)).await;
}

#[tokio::test]
async fn mqtt5_qos0_and_qos1_reach_mqtt311_subscriber() {
    for qos in [0_u8, 1] {
        let directory = tempfile::tempdir().unwrap();
        let auth = Arc::new(AccessPolicy::open_lab());
        let router = Arc::new(Router::start(directory.path(), auth.clone()).await.unwrap());
        let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let address = listener.local_addr().unwrap();
        let worker = tokio::spawn(async move {
            let mut handlers = Vec::new();
            for _ in 0..2 {
                let (stream, _) = listener.accept().await.unwrap();
                let auth = auth.clone();
                let router = router.clone();
                handlers.push(tokio::spawn(async move {
                    let connection = BrokerConnection::open_lab_for_test(stream).await.unwrap();
                    serve_connection(connection, auth, router).await.unwrap();
                }));
            }
            for handler in handlers {
                handler.await.unwrap();
            }
        });
        let mut subscriber = TcpStream::connect(address).await.unwrap();
        subscriber
            .write_all(&connect(b"subscriber", true, 4))
            .await
            .unwrap();
        let mut ack4 = [0; 4];
        timeout(Duration::from_secs(3), subscriber.read_exact(&mut ack4))
            .await
            .unwrap()
            .unwrap();
        assert_eq!(ack4, [0x20, 2, 0, 0]);
        subscriber
            .write_all(&[0x82, 6, 0, 1, 0, 1, b'x', 0])
            .await
            .unwrap();
        let mut suback = [0; 5];
        timeout(Duration::from_secs(3), subscriber.read_exact(&mut suback))
            .await
            .unwrap()
            .unwrap();
        assert_eq!(suback, [0x90, 3, 0, 1, 0]);

        let mut publisher = TcpStream::connect(address).await.unwrap();
        publisher
            .write_all(&connect(b"publisher", true, 5))
            .await
            .unwrap();
        let mut ack5 = [0; 12];
        timeout(Duration::from_secs(3), publisher.read_exact(&mut ack5))
            .await
            .unwrap()
            .unwrap();
        assert_eq!(ack5, [0x20, 10, 0, 0, 7, 0x24, 1, 0x27, 0, 1, 0, 0]);
        if qos == 0 {
            publisher
                .write_all(&[0x30, 5, 0, 1, b'x', 0, b'y'])
                .await
                .unwrap();
        } else {
            publisher
                .write_all(&[0x32, 7, 0, 1, b'x', 0, 1, 0, b'y'])
                .await
                .unwrap();
            let mut puback = [0; 4];
            timeout(Duration::from_secs(3), publisher.read_exact(&mut puback))
                .await
                .unwrap()
                .unwrap();
            assert_eq!(puback, [0x40, 2, 0, 1]);
        }
        let mut delivered = [0; 6];
        timeout(
            Duration::from_secs(3),
            subscriber.read_exact(&mut delivered),
        )
        .await
        .unwrap()
        .unwrap();
        assert_eq!(delivered, [0x30, 4, 0, 1, b'x', b'y']);
        publisher.write_all(&[0xe0, 0]).await.unwrap();
        subscriber.write_all(&[0xe0, 0]).await.unwrap();
        timeout(Duration::from_secs(3), worker)
            .await
            .unwrap()
            .unwrap();
    }
}

#[tokio::test]
async fn mqtt5_subscriber_receives_retained_and_live_qos1_from_v311() {
    let directory = tempfile::tempdir().unwrap();
    let auth = Arc::new(AccessPolicy::open_lab());
    let router = Arc::new(Router::start(directory.path(), auth.clone()).await.unwrap());
    let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
    let address = listener.local_addr().unwrap();
    let worker = tokio::spawn(async move {
        let mut handlers = Vec::new();
        for _ in 0..2 {
            let (stream, _) = listener.accept().await.unwrap();
            let auth = auth.clone();
            let router = router.clone();
            handlers.push(tokio::spawn(async move {
                let connection = BrokerConnection::open_lab_for_test(stream).await.unwrap();
                serve_connection(connection, auth, router).await.unwrap();
            }));
        }
        for handler in handlers {
            handler.await.unwrap();
        }
    });
    let mut publisher = TcpStream::connect(address).await.unwrap();
    publisher
        .write_all(&connect(b"publisher", true, 4))
        .await
        .unwrap();
    let mut ack4 = [0; 4];
    timeout(Duration::from_secs(3), publisher.read_exact(&mut ack4))
        .await
        .unwrap()
        .unwrap();
    assert_eq!(ack4, [0x20, 2, 0, 0]);
    publisher
        .write_all(&[0x33, 6, 0, 1, b'x', 0, 1, b'r'])
        .await
        .unwrap();
    let mut puback = [0; 4];
    timeout(Duration::from_secs(3), publisher.read_exact(&mut puback))
        .await
        .unwrap()
        .unwrap();
    assert_eq!(puback, [0x40, 2, 0, 1]);

    let mut subscriber = TcpStream::connect(address).await.unwrap();
    subscriber
        .write_all(&connect(b"subscriber", true, 5))
        .await
        .unwrap();
    let mut ack5 = [0; 12];
    timeout(Duration::from_secs(3), subscriber.read_exact(&mut ack5))
        .await
        .unwrap()
        .unwrap();
    assert_eq!(ack5[0..4], [0x20, 10, 0, 0]);
    subscriber
        .write_all(&[0x82, 7, 0, 1, 0, 0, 1, b'x', 1])
        .await
        .unwrap();
    let mut suback = [0; 6];
    timeout(Duration::from_secs(3), subscriber.read_exact(&mut suback))
        .await
        .unwrap()
        .unwrap();
    assert_eq!(suback, [0x90, 4, 0, 1, 0, 1]);
    let mut retained = [0; 9];
    timeout(Duration::from_secs(3), subscriber.read_exact(&mut retained))
        .await
        .unwrap()
        .unwrap();
    assert_eq!(retained[0], 0x33);
    assert_eq!(retained[7], 0); // Properties length.
    assert_eq!(retained[8], b'r');
    subscriber
        .write_all(&[0x40, 2, retained[5], retained[6]])
        .await
        .unwrap();

    publisher
        .write_all(&[0x32, 6, 0, 1, b'x', 0, 2, b'l'])
        .await
        .unwrap();
    timeout(Duration::from_secs(3), publisher.read_exact(&mut puback))
        .await
        .unwrap()
        .unwrap();
    let mut live = [0; 9];
    timeout(Duration::from_secs(3), subscriber.read_exact(&mut live))
        .await
        .unwrap()
        .unwrap();
    assert_eq!(live[0], 0x32);
    assert_eq!(live[8], b'l');
    subscriber
        .write_all(&[0x40, 2, live[5], live[6]])
        .await
        .unwrap();
    subscriber.write_all(&[0xe0, 0]).await.unwrap();
    publisher.write_all(&[0xe0, 0]).await.unwrap();
    timeout(Duration::from_secs(3), worker)
        .await
        .unwrap()
        .unwrap();
}

#[tokio::test]
async fn refused_client_ids_receive_connack_two_without_state_change() {
    for clean in [false, true] {
        for id in [
            Vec::new(),
            vec![b'a'; 257],
            "é".repeat(128)
                .into_bytes()
                .into_iter()
                .chain(*b"a")
                .collect(),
        ] {
            let mut packet = connect(&id, clean, 4);
            // Retained QoS0 publish must never be processed after a refusal.
            packet.extend([0x31, 4, 0, 1, b'x', b'y']);
            case(packet, Some(2)).await;
        }
    }
}

#[tokio::test]
async fn supported_alphanumeric_ids_and_local_utf8_boundary_are_accepted() {
    let alphabet = b"0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ";
    for length in 1..=23 {
        case(connect(&alphabet[..length], true, 4), Some(0)).await;
    }
    for id in [vec![b'a'; 256], "é".repeat(128).into_bytes()] {
        case(connect(&id, false, 4), Some(0)).await;
    }
}

#[tokio::test]
async fn malformed_connect_closes_without_connack() {
    let valid = connect(b"valid", true, 4);
    let mut wrong_name = valid.clone();
    wrong_name[4] = b'X';
    let mut reserved_flags = valid.clone();
    reserved_flags[9] |= 1;
    let mut trailing = valid.clone();
    trailing[1] += 1;
    trailing.push(0);
    for packet in [
        wrong_name,
        reserved_flags,
        trailing,
        connect(&[0xff], true, 4),
        connect(&[0], true, 4),
    ] {
        case(packet, None).await;
    }
}
