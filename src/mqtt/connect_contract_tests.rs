// SPDX-License-Identifier: MIT
//! Independent CONNECT bytes exercise real TCP admission into the MQTT actor.

use super::*;
use argon2::password_hash::{PasswordHasher, SaltString};
use std::fs;
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

fn connect5_with_properties(properties: &[u8]) -> Vec<u8> {
    let mut packet = connect(b"valid", true, 5);
    packet[12] = u8::try_from(properties.len()).unwrap();
    packet.splice(13..13, properties.iter().copied());
    packet[1] = u8::try_from(packet.len() - 2).unwrap();
    packet
}

fn authenticated_connect(id: &[u8], level: u8) -> Vec<u8> {
    let mut packet = connect(id, true, level);
    packet[9] = 0xc2; // Username, password and Clean Start/Clean Session.
    packet.extend([0, 7]);
    packet.extend(b"student");
    packet.extend([0, 12]);
    packet.extend(b"correct-pass");
    packet[1] = u8::try_from(packet.len() - 2).unwrap();
    packet
}

async fn denied_subscription(stream: &mut TcpStream, level: u8, packet_id: u8) {
    let mut packet = vec![0x82, 0, 0, packet_id];
    if level == 5 {
        packet.push(0); // Empty MQTT 5 properties.
    }
    packet.extend([0, 12]);
    packet.extend(b"denied/topic");
    packet.push(1);
    packet[1] = u8::try_from(packet.len() - 2).unwrap();
    stream.write_all(&packet).await.unwrap();
    let expected = if level == 5 {
        vec![0x90, 4, 0, packet_id, 0, 0x87]
    } else {
        vec![0x90, 3, 0, packet_id, 0x80]
    };
    let mut received = vec![0; expected.len()];
    timeout(Duration::from_secs(3), stream.read_exact(&mut received))
        .await
        .unwrap()
        .unwrap();
    assert_eq!(received, expected);
}

async fn denied_legacy_publish(stream: &mut TcpStream) {
    let mut packet = vec![0x32, 0, 0, 12];
    packet.extend(b"denied/topic");
    packet.extend([0, 3, b'z']);
    packet[1] = u8::try_from(packet.len() - 2).unwrap();
    stream.write_all(&packet).await.unwrap();
    closed(stream).await;
}

async fn denied_mqtt5_qos2_publish(stream: &mut TcpStream) {
    let mut packet = vec![0x34, 0, 0, 12];
    packet.extend(b"denied/topic");
    packet.extend([0, 6, 0, b'n']);
    packet[1] = u8::try_from(packet.len() - 2).unwrap();
    stream.write_all(&packet).await.unwrap();
    let mut pubrec = [0; 6];
    timeout(Duration::from_secs(3), stream.read_exact(&mut pubrec))
        .await
        .unwrap()
        .unwrap();
    assert_eq!(pubrec, [0x50, 4, 0, 6, 0x87, 0]);
}

fn assert_commits(router: &Router, expected: u64) {
    assert_eq!(router.metrics().commits.load(Ordering::Relaxed), expected);
}

async fn allowed_mqtt5_subscription(stream: &mut TcpStream) {
    let mut packet = vec![0x82, 0, 0, 5, 0, 0, 13];
    packet.extend(b"allowed/topic");
    packet.push(1);
    packet[1] = u8::try_from(packet.len() - 2).unwrap();
    stream.write_all(&packet).await.unwrap();
    let mut suback = [0; 6];
    timeout(Duration::from_secs(3), stream.read_exact(&mut suback))
        .await
        .unwrap()
        .unwrap();
    assert_eq!(suback, [0x90, 4, 0, 5, 0, 1]);
}

async fn mqtt5_publish_to_qos0_subscriber(stream: &mut TcpStream, qos: u8) {
    match qos {
        0 => stream
            .write_all(&[0x30, 5, 0, 1, b'x', 0, b'y'])
            .await
            .unwrap(),
        1 => {
            stream
                .write_all(&[0x32, 7, 0, 1, b'x', 0, 1, 0, b'y'])
                .await
                .unwrap();
            let mut ack = [0; 4];
            timeout(Duration::from_secs(3), stream.read_exact(&mut ack))
                .await
                .unwrap()
                .unwrap();
            assert_eq!(ack, [0x40, 2, 0, 1]);
        }
        2 => {
            let publish = [0x34, 7, 0, 1, b'x', 0, 1, 0, b'y'];
            stream.write_all(&publish).await.unwrap();
            let mut ack = [0; 4];
            timeout(Duration::from_secs(3), stream.read_exact(&mut ack))
                .await
                .unwrap()
                .unwrap();
            assert_eq!(ack, [0x50, 2, 0, 1]);
            stream.write_all(&[0x62, 2, 0, 1]).await.unwrap();
            timeout(Duration::from_secs(3), stream.read_exact(&mut ack))
                .await
                .unwrap()
                .unwrap();
            assert_eq!(ack, [0x70, 2, 0, 1]);
        }
        _ => unreachable!(),
    }
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
        let expected: &[u8] = if code == 0 && packet[8] == 5 {
            &[0x20, 8, 0, 0, 5, 0x27, 0, 1, 0, 0]
        } else if code == 0x83 {
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
async fn mqtt5_unsupported_auth_property_refused_without_commit() {
    case(connect5_with_properties(&[0x15, 0, 1, b'x']), Some(0x83)).await;
    case(
        connect5_with_properties(&[0x27, 0, 0, 0, 1, 0x15, 0, 1, b'x']),
        None,
    )
    .await;
}

#[tokio::test]
async fn mqtt5_connect_informational_properties_accept_and_reject_before_commit() {
    case(
        connect5_with_properties(&[
            0x17, 0, 0x19, 1, 0x22, 0, 3, 0x26, 0, 1, b'a', 0, 1, b'b', 0x26, 0, 1, b'a', 0, 1,
            b'c',
        ]),
        Some(0),
    )
    .await;
    for properties in [
        &[0x17, 2][..],
        &[0x19, 0, 0x19, 1][..],
        &[0x22, 0, 0, 0x22, 0, 1][..],
        &[0x26, 0, 1, 0xff, 0, 1, b'b'][..],
        &[0x26, 0, 1, b'a', 0, 2, b'b'][..],
    ] {
        case(connect5_with_properties(properties), None).await;
    }
    case(connect5_with_properties(&[0x27, 0, 0, 1, 0]), Some(0)).await;
    for properties in [
        &[0x27, 0, 0, 0, 0][..],
        &[0x27, 0, 0, 0][..],
        &[0x27, 0, 0, 0, 10, 0x27, 0, 0, 0, 10][..],
        &[0x27, 0, 0, 0, 4][..],
    ] {
        case(connect5_with_properties(properties), None).await;
    }
}

#[tokio::test]
async fn mqtt5_qos0_qos1_qos2_reach_mqtt311_subscriber() {
    for qos in [0_u8, 1, 2] {
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
        let mut ack5 = [0; 10];
        timeout(Duration::from_secs(3), publisher.read_exact(&mut ack5))
            .await
            .unwrap()
            .unwrap();
        assert_eq!(ack5, [0x20, 8, 0, 0, 5, 0x27, 0, 1, 0, 0]);
        mqtt5_publish_to_qos0_subscriber(&mut publisher, qos).await;
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
async fn mqtt5_acl_denial_reports_puback_reason_without_committing() {
    let directory = tempfile::tempdir().unwrap();
    let users = directory.path().join("users.toml");
    let acl = directory.path().join("acl.toml");
    let salt = SaltString::encode_b64(b"sixteen-byte-salt").unwrap();
    let hash = crate::auth::argon2_context()
        .hash_password(b"correct-pass", &salt)
        .unwrap()
        .to_string();
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
    let auth = Arc::new(AccessPolicy::acl_lab(
        crate::auth::AuthPolicy::load_passwords_with_acl(&users, &acl).unwrap(),
    ));
    let router = Arc::new(Router::start(directory.path(), auth.clone()).await.unwrap());
    let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
    let address = listener.local_addr().unwrap();
    let worker_router = router.clone();
    let worker = tokio::spawn(async move {
        for _ in 0..2 {
            let (stream, _) = listener.accept().await.unwrap();
            let connection = BrokerConnection::open_lab_for_test(stream).await.unwrap();
            serve_connection(connection, auth.clone(), worker_router.clone())
                .await
                .unwrap();
        }
    });
    let mut publisher = TcpStream::connect(address).await.unwrap();
    publisher
        .write_all(&authenticated_connect(b"publisher", 5))
        .await
        .unwrap();
    let mut connack = [0; 10];
    timeout(Duration::from_secs(3), publisher.read_exact(&mut connack))
        .await
        .unwrap()
        .unwrap();
    assert_eq!(connack[0..4], [0x20, 8, 0, 0]);

    let commits_before = router.metrics().commits.load(Ordering::Relaxed);
    denied_subscription(&mut publisher, 5, 3).await;
    assert_commits(&router, commits_before);
    let mut denied = vec![0x33, 0, 0, 12];
    denied.extend(b"denied/topic");
    denied.extend([0, 1, 0, b'x']);
    denied[1] = u8::try_from(denied.len() - 2).unwrap();
    publisher.write_all(&denied).await.unwrap();
    let mut refusal = [0; 6];
    timeout(Duration::from_secs(3), publisher.read_exact(&mut refusal))
        .await
        .unwrap()
        .unwrap();
    assert_eq!(refusal, [0x40, 4, 0, 1, 0x87, 0]);
    assert_commits(&router, commits_before);

    denied_mqtt5_qos2_publish(&mut publisher).await;
    assert_commits(&router, commits_before);

    let mut allowed = vec![0x32, 0, 0, 13];
    allowed.extend(b"allowed/topic");
    allowed.extend([0, 2, 0, b'y']);
    allowed[1] = u8::try_from(allowed.len() - 2).unwrap();
    publisher.write_all(&allowed).await.unwrap();
    let mut accepted = [0; 4];
    timeout(Duration::from_secs(3), publisher.read_exact(&mut accepted))
        .await
        .unwrap()
        .unwrap();
    assert_eq!(accepted, [0x40, 2, 0, 2]);
    allowed_mqtt5_subscription(&mut publisher).await;
    publisher.write_all(&[0xe0, 0]).await.unwrap();

    let mut legacy = TcpStream::connect(address).await.unwrap();
    legacy
        .write_all(&authenticated_connect(b"legacy", 4))
        .await
        .unwrap();
    let mut connack4 = [0; 4];
    timeout(Duration::from_secs(3), legacy.read_exact(&mut connack4))
        .await
        .unwrap()
        .unwrap();
    assert_eq!(connack4, [0x20, 2, 0, 0]);
    denied_subscription(&mut legacy, 4, 4).await;
    denied_legacy_publish(&mut legacy).await;

    timeout(Duration::from_secs(3), worker)
        .await
        .unwrap()
        .unwrap();
    router.shutdown().await.unwrap();
}

#[tokio::test]
async fn mqtt5_unsubscribe_reports_each_filter_and_stops_delivery() {
    let directory = tempfile::tempdir().unwrap();
    let auth = Arc::new(AccessPolicy::open_lab());
    let router = Arc::new(Router::start(directory.path(), auth.clone()).await.unwrap());
    let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
    let address = listener.local_addr().unwrap();
    let worker_router = router.clone();
    let worker = tokio::spawn(async move {
        let (stream, _) = listener.accept().await.unwrap();
        let connection = BrokerConnection::open_lab_for_test(stream).await.unwrap();
        serve_connection(connection, auth, worker_router)
            .await
            .unwrap();
    });
    let mut stream = TcpStream::connect(address).await.unwrap();
    stream.write_all(&connect(b"sub", true, 5)).await.unwrap();
    let mut connack = [0; 10];
    timeout(Duration::from_secs(3), stream.read_exact(&mut connack))
        .await
        .unwrap()
        .unwrap();
    assert_eq!(connack[0..4], [0x20, 8, 0, 0]);

    let subscribe = [
        0x82, 12, 0, 1, 0, 0, 6, b't', b'e', b's', b't', b'/', b'#', 1,
    ];
    stream.write_all(&subscribe).await.unwrap();
    let mut suback = [0; 6];
    timeout(Duration::from_secs(3), stream.read_exact(&mut suback))
        .await
        .unwrap()
        .unwrap();
    assert_eq!(suback, [0x90, 4, 0, 1, 0, 1]);
    let unsubscribe = [
        0xa2, 20, 0, 2, 0, 0, 6, b't', b'e', b's', b't', b'/', b'#', 0, 7, b'm', b'i', b's', b's',
        b'i', b'n', b'g',
    ];
    stream.write_all(&unsubscribe).await.unwrap();
    let mut unsuback = [0; 7];
    timeout(Duration::from_secs(3), stream.read_exact(&mut unsuback))
        .await
        .unwrap()
        .unwrap();
    assert_eq!(unsuback, [0xb0, 5, 0, 2, 0, 0, 0x11]);
    let commits = router.metrics().commits.load(Ordering::Relaxed);

    let missing = [0xa2, 11, 0, 3, 0, 0, 6, b't', b'e', b's', b't', b'/', b'#'];
    stream.write_all(&missing).await.unwrap();
    let mut missing_ack = [0; 6];
    timeout(Duration::from_secs(3), stream.read_exact(&mut missing_ack))
        .await
        .unwrap()
        .unwrap();
    assert_eq!(missing_ack, [0xb0, 4, 0, 3, 0, 0x11]);
    assert_eq!(router.metrics().commits.load(Ordering::Relaxed), commits);

    let publish = [
        0x32, 12, 0, 6, b't', b'e', b's', b't', b'/', b'a', 0, 4, 0, b'x',
    ];
    stream.write_all(&publish).await.unwrap();
    let mut puback = [0; 4];
    timeout(Duration::from_secs(3), stream.read_exact(&mut puback))
        .await
        .unwrap()
        .unwrap();
    assert_eq!(puback, [0x40, 2, 0, 4]);
    let mut extra = [0];
    assert!(
        timeout(Duration::from_millis(150), stream.read(&mut extra))
            .await
            .is_err()
    );
    stream.write_all(&[0xe0, 0]).await.unwrap();
    timeout(Duration::from_secs(3), worker)
        .await
        .unwrap()
        .unwrap();
    router.shutdown().await.unwrap();
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
    let mut ack5 = [0; 10];
    timeout(Duration::from_secs(3), subscriber.read_exact(&mut ack5))
        .await
        .unwrap()
        .unwrap();
    assert_eq!(ack5[0..4], [0x20, 8, 0, 0]);
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
