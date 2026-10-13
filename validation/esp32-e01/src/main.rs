// SPDX-License-Identifier: MIT
//! Initial E01 slice: bounded Wi-Fi/SNTP/mTLS and synthetic 1024-byte loopback.
//! This is test firmware, not the broker or production device application.
use esp_idf_svc::{
    eventloop::EspSystemEventLoop,
    hal::peripherals::Peripherals,
    mqtt::client::{
        Details, EspMqttClient, EventPayload, MqttClientConfiguration, MqttProtocolVersion, QoS,
    },
    sntp::{EspSntp, SyncStatus},
    tls::X509,
    wifi::{ClientConfiguration, Configuration, EspWifi, WifiEvent},
};
use std::{
    sync::atomic::{AtomicBool, AtomicUsize, Ordering},
    thread,
    time::{Duration, Instant},
};

mod private {
    include!(concat!(env!("OUT_DIR"), "/private_config.rs"));
}
#[cfg(e01_retained)]
mod retained;
const TOPIC: &str = "e01/board/bytes";
static CONNECTED: AtomicBool = AtomicBool::new(false);
static SUBSCRIBED: AtomicBool = AtomicBool::new(false);
static RECEIVED: AtomicUsize = AtomicUsize::new(0);
static EXPECTED: AtomicUsize = AtomicUsize::new(0);
static PUBLISHED: AtomicUsize = AtomicUsize::new(usize::MAX);
static INVALID: AtomicBool = AtomicBool::new(false);

fn wait(seconds: u64, predicate: impl Fn() -> bool) -> bool {
    let deadline = Instant::now() + Duration::from_secs(seconds);
    while Instant::now() < deadline {
        if predicate() {
            return true;
        }
        thread::sleep(Duration::from_millis(50));
    }
    predicate()
}

fn run() -> Result<(), &'static str> {
    esp_idf_svc::sys::link_patches();
    println!("E01_BOOT fixture=0.1.0 payload=1024");
    let peripherals = Peripherals::take().map_err(|_| "PERIPHERALS")?;
    let event_loop = EspSystemEventLoop::take().map_err(|_| "EVENT_LOOP")?;
    let _wifi_observer = event_loop
        .subscribe::<WifiEvent, _>(|event| match event {
            WifiEvent::StaConnected(_) => println!("E01_WIFI_ASSOCIATED"),
            WifiEvent::StaDisconnected(info) => {
                println!("E01_WIFI_DISCONNECTED reason={}", info.reason())
            }
            _ => {}
        })
        .map_err(|_| "WIFI_OBSERVER")?;
    let mut wifi = EspWifi::new(peripherals.modem, event_loop, None).map_err(|_| "WIFI_DRIVER")?;
    wifi.set_configuration(&Configuration::Client(ClientConfiguration {
        ssid: private::SSID.try_into().map_err(|_| "SSID_LENGTH")?,
        password: private::WIFI_PASSWORD
            .try_into()
            .map_err(|_| "PASSWORD_LENGTH")?,
        ..Default::default()
    }))
    .map_err(|_| "WIFI_CONFIG")?;
    wifi.start().map_err(|_| "WIFI_START")?;
    if !wait(15, || wifi.is_started().unwrap_or(false)) {
        return Err("WIFI_START_TIMEOUT");
    }
    // ESP-IDF connect scans the configured AP itself. A separate diagnostic
    // scan must not veto an authentication attempt to that same private SSID.
    wifi.connect().map_err(|_| "WIFI_CONNECT")?;
    if !wait(30, || wifi.is_connected().unwrap_or(false)) {
        return Err("WIFI_ASSOCIATION_TIMEOUT");
    }
    if !wait(30, || wifi.is_up().unwrap_or(false)) {
        return Err("WIFI_IP_TIMEOUT");
    }
    println!("E01_WIFI_UP");
    let sntp = EspSntp::new_default().map_err(|_| "SNTP_START")?;
    if !wait(60, || sntp.get_sync_status() == SyncStatus::Completed) {
        return Err("SNTP_TIMEOUT");
    }
    println!("E01_SNTP_SYNC");
    let config = MqttClientConfiguration {
        protocol_version: Some(MqttProtocolVersion::V3_1_1),
        client_id: Some("e01-physical-board"),
        username: Some(private::MQTT_USERNAME),
        password: Some(private::MQTT_PASSWORD),
        server_certificate: Some(X509::pem_until_nul(private::CA)),
        client_certificate: Some(X509::pem_until_nul(private::CERT)),
        private_key: Some(X509::pem_until_nul(private::KEY)),
        skip_cert_common_name_check: false,
        keep_alive_interval: Some(Duration::from_secs(15)),
        reconnect_timeout: None,
        network_timeout: Duration::from_secs(5),
        task_stack: 8192,
        buffer_size: 2048,
        out_buffer_size: 2048,
        outbox_limit: Some(8192),
        ..Default::default()
    };
    let mut client =
        EspMqttClient::new_cb(private::MQTT_URL, &config, |event| match event.payload() {
            EventPayload::Connected(_) => {
                CONNECTED.store(true, Ordering::SeqCst);
            }
            EventPayload::Disconnected => {
                CONNECTED.store(false, Ordering::SeqCst);
            }
            EventPayload::Subscribed(_) => {
                SUBSCRIBED.store(true, Ordering::SeqCst);
            }
            EventPayload::Published(id) => {
                PUBLISHED.store(id as usize, Ordering::SeqCst);
            }
            EventPayload::Received {
                topic,
                data,
                details,
                ..
            } => {
                #[cfg(e01_retained)]
                if retained::observe(topic, data, details) {
                    return;
                }
                let valid = topic == Some(TOPIC)
                    && matches!(details, Details::Complete)
                    && data.len() == 1024
                    && data
                        .iter()
                        .skip(1)
                        .enumerate()
                        .all(|(i, b)| *b == ((i + 1) % 251) as u8)
                    && data[0] <= 2;
                if valid {
                    if usize::from(data[0]) == EXPECTED.load(Ordering::SeqCst) {
                        RECEIVED.fetch_add(1, Ordering::SeqCst);
                    }
                } else {
                    INVALID.store(true, Ordering::SeqCst);
                }
            }
            _ => {}
        })
        .map_err(|_| "MQTT_CREATE")?;
    if !wait(30, || CONNECTED.load(Ordering::SeqCst)) {
        return Err("MQTT_CONNECT_TIMEOUT");
    }
    println!("E01_MTLS_CONNECTED");
    client
        .subscribe(TOPIC, QoS::ExactlyOnce)
        .map_err(|_| "SUBSCRIBE")?;
    if !wait(10, || SUBSCRIBED.load(Ordering::SeqCst)) {
        return Err("SUBSCRIBE_TIMEOUT");
    }
    let mut payload: Vec<u8> = (0..1024).map(|i| (i % 251) as u8).collect();
    for (index, qos) in [QoS::AtMostOnce, QoS::AtLeastOnce, QoS::ExactlyOnce]
        .into_iter()
        .enumerate()
    {
        let before = RECEIVED.load(Ordering::SeqCst);
        EXPECTED.store(index, Ordering::SeqCst);
        payload[0] = index as u8;
        let publication_id = client
            .publish(TOPIC, qos, false, &payload)
            .map_err(|_| "PUBLISH")?;
        if qos != QoS::AtMostOnce
            && !wait(10, || {
                PUBLISHED.load(Ordering::SeqCst) == publication_id as usize
            })
        {
            return Err("PUBLISH_ACK_TIMEOUT");
        }
        if !wait(10, || RECEIVED.load(Ordering::SeqCst) > before) || INVALID.load(Ordering::SeqCst)
        {
            return Err("BYTES_OR_DELIVERY");
        }
        println!("E01_LOOPBACK_PASS qos={index} bytes=1024");
    }
    #[cfg(e01_retained)]
    retained::run(&mut client, &mut payload)?;
    // Dropping the client cancels retries; no infinite application reconnect loop.
    drop(client);
    wifi.stop().map_err(|_| "WIFI_STOP")?;
    println!("E01_INITIAL_SLICE_PASS");
    Ok(())
}

fn main() {
    if let Err(stage) = run() {
        println!("E01_FAIL stage={stage}");
    }
    println!("E01_STOP");
}
