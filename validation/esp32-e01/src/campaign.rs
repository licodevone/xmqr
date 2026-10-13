// SPDX-License-Identifier: MIT
//! Supervised physical E01 campaign. All reconnect loops are finite.
use esp_idf_svc::{
    mqtt::client::{
        Details, EspMqttClient, EventPayload, LwtConfiguration, MqttClientConfiguration,
        MqttProtocolVersion, QoS,
    },
    tls::X509,
    wifi::EspWifi,
};
use std::{
    sync::atomic::{AtomicBool, AtomicUsize, Ordering},
    thread,
    time::{Duration, Instant},
};

const BYTES: &str = "e01/board/bytes";
const RETAINED: &str = "e01/board/retained";
const CONTROL: &str = "e01/board/control";
const WILL: &str = "e01/board/will";
static CONNECTED: AtomicBool = AtomicBool::new(false);
static ERROR: AtomicBool = AtomicBool::new(false);
static DISCONNECTED: AtomicBool = AtomicBool::new(false);
static SUBACK: AtomicUsize = AtomicUsize::new(0);
static PUBACK: AtomicUsize = AtomicUsize::new(usize::MAX);
static CONFIRM: AtomicUsize = AtomicUsize::new(0);
static EXPECTED: AtomicUsize = AtomicUsize::new(0);
static COPIES: AtomicUsize = AtomicUsize::new(0);
static INVALID: AtomicBool = AtomicBool::new(false);

fn bytes(sequence: u8) -> Vec<u8> {
    let mut value: Vec<u8> = (0..1024).map(|i| (i % 251) as u8).collect();
    value[0] = sequence;
    value
}

fn open(
    ca: &'static [u8],
    password: &'static str,
    will: Option<&[u8]>,
) -> Result<EspMqttClient<'static>, &'static str> {
    CONNECTED.store(false, Ordering::SeqCst);
    ERROR.store(false, Ordering::SeqCst);
    DISCONNECTED.store(false, Ordering::SeqCst);
    let config = MqttClientConfiguration {
        protocol_version: Some(MqttProtocolVersion::V3_1_1),
        client_id: Some("e01-physical-board"),
        username: Some(super::private::MQTT_USERNAME),
        password: Some(password),
        server_certificate: Some(X509::pem_until_nul(ca)),
        client_certificate: Some(X509::pem_until_nul(super::private::CERT)),
        private_key: Some(X509::pem_until_nul(super::private::KEY)),
        skip_cert_common_name_check: false,
        keep_alive_interval: Some(Duration::from_secs(10)),
        reconnect_timeout: None,
        network_timeout: Duration::from_secs(3),
        task_stack: 8192,
        buffer_size: 2048,
        out_buffer_size: 2048,
        outbox_limit: Some(8192),
        lwt: will.map(|data| LwtConfiguration {
            topic: WILL,
            payload: data,
            qos: QoS::AtLeastOnce,
            retain: false,
        }),
        ..Default::default()
    };
    EspMqttClient::new_cb(super::private::MQTT_URL, &config, |event| {
        match event.payload() {
            EventPayload::Connected(_) => {
                CONNECTED.store(true, Ordering::SeqCst);
            }
            EventPayload::Disconnected => {
                CONNECTED.store(false, Ordering::SeqCst);
                DISCONNECTED.store(true, Ordering::SeqCst);
            }
            EventPayload::Error(_) => {
                ERROR.store(true, Ordering::SeqCst);
            }
            EventPayload::Subscribed(id) => {
                SUBACK.store(id as usize, Ordering::SeqCst);
            }
            EventPayload::Published(id) => {
                PUBACK.store(id as usize, Ordering::SeqCst);
            }
            EventPayload::Received {
                topic,
                data,
                details,
                ..
            } => {
                if topic == Some(CONTROL) && matches!(details, Details::Complete) && data.len() == 1
                {
                    CONFIRM.store(usize::from(data[0]), Ordering::SeqCst);
                } else if topic == Some(BYTES) {
                    if matches!(details, Details::Complete)
                        && data.len() == 1024
                        && usize::from(data[0]) == EXPECTED.load(Ordering::SeqCst)
                        && data
                            .iter()
                            .enumerate()
                            .skip(1)
                            .all(|(i, b)| *b == (i % 251) as u8)
                    {
                        COPIES.fetch_add(1, Ordering::SeqCst);
                    } else {
                        INVALID.store(true, Ordering::SeqCst);
                    }
                }
            }
            _ => {}
        }
    })
    .map_err(|_| "P85_MQTT_CREATE")
}

fn connected(will: Option<&[u8]>) -> Result<EspMqttClient<'static>, &'static str> {
    for delay in [1, 2, 4] {
        thread::sleep(Duration::from_secs(delay));
        let client = open(super::private::CA, super::private::MQTT_PASSWORD, will)?;
        if super::wait(10, || {
            CONNECTED.load(Ordering::SeqCst) || ERROR.load(Ordering::SeqCst)
        }) && CONNECTED.load(Ordering::SeqCst)
        {
            return Ok(client);
        }
        drop(client);
    }
    Err("P85_RECONNECT_LIMIT")
}

fn subscribe(client: &mut EspMqttClient<'_>, topic: &str) -> Result<(), &'static str> {
    let id = client
        .subscribe(topic, QoS::ExactlyOnce)
        .map_err(|_| "P85_SUBSCRIBE")?;
    if !super::wait(5, || SUBACK.load(Ordering::SeqCst) == id as usize) {
        return Err("P85_SUBSCRIBE_TIMEOUT");
    }
    Ok(())
}

fn publish(
    client: &mut EspMqttClient<'_>,
    topic: &str,
    data: &[u8],
    retained: bool,
    qos: QoS,
) -> Result<(), &'static str> {
    PUBACK.store(usize::MAX, Ordering::SeqCst);
    let id = client
        .publish(topic, qos, retained, data)
        .map_err(|_| "P85_PUBLISH")?;
    if !super::wait(5, || PUBACK.load(Ordering::SeqCst) == id as usize) {
        return Err("P85_ACK_TIMEOUT");
    }
    Ok(())
}

fn confirmation(sequence: usize) -> Result<(), &'static str> {
    if !super::wait(15, || CONFIRM.load(Ordering::SeqCst) == sequence) {
        return Err("P85_CONFIRM_TIMEOUT");
    }
    Ok(())
}

fn memory(stage: &str) -> Result<usize, &'static str> {
    let largest = super::memory_probe::measure();
    println!("P85_MEMORY stage={stage} largest_probe={largest}");
    if largest < 8192 {
        return Err("P85_MEMORY_LOW");
    }
    Ok(largest)
}

fn negative(ca: &'static [u8], password: &'static str) -> Result<(), &'static str> {
    let rejected = open(ca, password, None)?;
    let observed = super::wait(8, || {
        CONNECTED.load(Ordering::SeqCst)
            || ERROR.load(Ordering::SeqCst)
            || DISCONNECTED.load(Ordering::SeqCst)
    });
    let failed = observed
        && !CONNECTED.load(Ordering::SeqCst)
        && (ERROR.load(Ordering::SeqCst) || DISCONNECTED.load(Ordering::SeqCst));
    drop(rejected);
    if !failed {
        return Err("P85_NEGATIVE_NOT_REJECTED");
    }
    Ok(())
}

pub fn run(wifi: &mut EspWifi<'_>) -> Result<(), &'static str> {
    let will = bytes(6);
    let mut client = connected(Some(&will))?;
    subscribe(&mut client, CONTROL)?;
    publish(&mut client, BYTES, &bytes(6), false, QoS::AtLeastOnce)?;
    let before = memory("idle")?;
    println!("P85_CONNECTED");
    println!("P85_WILL_READY");
    let began = Instant::now();
    wifi.disconnect().map_err(|_| "P85_WIFI_DISCONNECT")?;
    if !super::wait(5, || !wifi.is_connected().unwrap_or(true)) {
        return Err("P85_WIFI_DOWN_TIMEOUT");
    }
    println!("P85_WIFI_DOWN");
    drop(client);
    let mut restored = false;
    for delay in [1, 2, 4] {
        thread::sleep(Duration::from_secs(delay));
        wifi.connect().map_err(|_| "P85_WIFI_RECONNECT")?;
        if super::wait(8, || wifi.is_up().unwrap_or(false)) {
            restored = true;
            break;
        }
        wifi.disconnect().map_err(|_| "P85_WIFI_DISCONNECT")?;
    }
    if !restored {
        return Err("P85_WIFI_RECONNECT_LIMIT");
    }
    client = connected(None)?;
    subscribe(&mut client, CONTROL)?;
    publish(&mut client, BYTES, &bytes(7), false, QoS::AtLeastOnce)?;
    println!(
        "P85_TIME kind=wifi milliseconds={}",
        began.elapsed().as_millis()
    );
    memory("wifi")?;
    println!("P85_WIFI_RECONNECT_PASS");
    publish(&mut client, RETAINED, &bytes(8), true, QoS::AtLeastOnce)?;
    println!("P85_RESTART_READY");
    let began = Instant::now();
    if !super::wait(15, || DISCONNECTED.load(Ordering::SeqCst)) {
        return Err("P85_RESTART_NOT_OBSERVED");
    }
    drop(client);
    client = connected(None)?;
    subscribe(&mut client, CONTROL)?;
    confirmation(8)?;
    publish(&mut client, BYTES, &bytes(10), false, QoS::AtLeastOnce)?;
    println!(
        "P85_TIME kind=broker milliseconds={}",
        began.elapsed().as_millis()
    );
    memory("restart")?;
    println!("P85_BROKER_RECONNECT_PASS");
    confirmation(10)?;
    publish(&mut client, RETAINED, &[], true, QoS::AtLeastOnce)?;
    println!("P85_RESTART_DELETE");
    confirmation(20)?;
    EXPECTED.store(9, Ordering::SeqCst);
    COPIES.store(0, Ordering::SeqCst);
    subscribe(&mut client, BYTES)?;
    println!("P85_DUPLICATE_READY");
    if !super::wait(10, || COPIES.load(Ordering::SeqCst) >= 2) || INVALID.load(Ordering::SeqCst) {
        return Err("P85_DUPLICATE_BYTES");
    }
    println!("P85_DUPLICATE_PASS");
    publish(&mut client, RETAINED, &bytes(11), true, QoS::ExactlyOnce)?;
    println!("P85_EXTERNAL_SUB_READY");
    confirmation(11)?;
    EXPECTED.store(12, Ordering::SeqCst);
    COPIES.store(0, Ordering::SeqCst);
    println!("P85_EXTERNAL_PUB_READY");
    if !super::wait(10, || COPIES.load(Ordering::SeqCst) >= 1) || INVALID.load(Ordering::SeqCst) {
        return Err("P85_EXTERNAL_BYTES");
    }
    println!("P85_EXTERNAL_PASS");
    drop(client);
    negative(super::private::BAD_CA, super::private::MQTT_PASSWORD)?;
    client = connected(None)?;
    drop(client);
    println!("P85_NEGATIVE_CA_PASS");
    negative(super::private::CA, "incorrect-fixture-only")?;
    client = connected(None)?;
    println!("P85_NEGATIVE_PASSWORD_PASS");
    PUBACK.store(usize::MAX, Ordering::SeqCst);
    let denied_id = client
        .publish("e01/forbidden", QoS::AtLeastOnce, false, &bytes(13))
        .map_err(|_| "P85_DENIED_SEND")?;
    if !super::wait(8, || DISCONNECTED.load(Ordering::SeqCst))
        || PUBACK.load(Ordering::SeqCst) == denied_id as usize
    {
        return Err("P85_ACL_NOT_REJECTED");
    }
    drop(client);
    client = connected(None)?;
    subscribe(&mut client, CONTROL)?;
    println!("P85_NEGATIVE_ACL_PASS");
    println!("P85_SAN_READY");
    confirmation(30)?;
    drop(client);
    println!("P85_SAN_ARMED");
    thread::sleep(Duration::from_secs(8));
    negative(super::private::CA, super::private::MQTT_PASSWORD)?;
    println!("P85_NEGATIVE_SAN_PASS");
    client = connected(None)?;
    subscribe(&mut client, CONTROL)?;
    confirmation(31)?;
    publish(&mut client, BYTES, &bytes(14), false, QoS::AtLeastOnce)?;
    println!("P85_SAN_RESTORED");
    let after = memory("final")?;
    if before.saturating_sub(after) > 32768 || client.get_outbox_size() != 0 {
        return Err("P85_MEMORY_DRIFT");
    }
    drop(client);
    wifi.stop().map_err(|_| "WIFI_STOP")?;
    println!("P85_FINAL_PASS");
    Ok(())
}
