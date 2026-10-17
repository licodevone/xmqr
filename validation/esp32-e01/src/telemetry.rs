// SPDX-License-Identifier: MIT
//! Finite physical publication probe; samples are synthetic, not sensor readings.
use esp_idf_svc::{
    mqtt::client::{
        EspMqttClient, EventPayload, MqttClientConfiguration, MqttProtocolVersion, QoS,
    },
    tls::X509,
    wifi::EspWifi,
};
use std::{
    sync::atomic::{AtomicBool, AtomicUsize, Ordering},
    thread,
    time::Duration,
};

const TOPIC: &str = "xmqr/teste/ambiente";
const READINGS: [(u16, u16); 5] = [(231, 452), (233, 455), (234, 451), (232, 458), (235, 454)];
static CONNECTED: AtomicBool = AtomicBool::new(false);
static ERROR: AtomicBool = AtomicBool::new(false);
static PUBLISHED: AtomicUsize = AtomicUsize::new(usize::MAX);

pub fn run(wifi: &mut EspWifi<'_>) -> Result<(), &'static str> {
    let config = MqttClientConfiguration {
        protocol_version: Some(MqttProtocolVersion::V3_1_1),
        client_id: Some("p135-esp32-publisher"),
        username: Some(super::private::MQTT_USERNAME),
        password: Some(super::private::MQTT_PASSWORD),
        server_certificate: Some(X509::pem_until_nul(super::private::CA)),
        client_certificate: Some(X509::pem_until_nul(super::private::CERT)),
        private_key: Some(X509::pem_until_nul(super::private::KEY)),
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
    let mut client = EspMqttClient::new_cb(super::private::MQTT_URL, &config, |event| match event
        .payload()
    {
        EventPayload::Connected(_) => CONNECTED.store(true, Ordering::SeqCst),
        EventPayload::Disconnected | EventPayload::Error(_) => {
            ERROR.store(true, Ordering::SeqCst);
        }
        EventPayload::Published(id) => PUBLISHED.store(id as usize, Ordering::SeqCst),
        _ => {}
    })
    .map_err(|_| "MQTT_CREATE")?;
    if !super::wait(20, || {
        CONNECTED.load(Ordering::SeqCst) || ERROR.load(Ordering::SeqCst)
    }) || !CONNECTED.load(Ordering::SeqCst)
    {
        return Err("MQTT_CONNECT_TIMEOUT");
    }
    println!("P135_MTLS_CONNECTED");
    for (index, (temperature, humidity)) in READINGS.iter().enumerate() {
        if ERROR.load(Ordering::SeqCst) {
            return Err("MQTT_DISCONNECTED");
        }
        let payload = format!(
            "{{\"seq\":{},\"temperature_c\":{}.{},\"humidity_pct\":{}.{},\"source\":\"simulated\"}}",
            index + 1,
            temperature / 10,
            temperature % 10,
            humidity / 10,
            humidity % 10
        );
        let packet_id = client
            .publish(TOPIC, QoS::AtLeastOnce, false, payload.as_bytes())
            .map_err(|_| "PUBLISH")?;
        if !super::wait(10, || {
            PUBLISHED.load(Ordering::SeqCst) == packet_id as usize || ERROR.load(Ordering::SeqCst)
        }) || ERROR.load(Ordering::SeqCst)
        {
            return Err("PUBACK_TIMEOUT");
        }
        println!("P135_PUBACK seq={}", index + 1);
        thread::sleep(Duration::from_millis(500));
    }
    drop(client);
    wifi.stop().map_err(|_| "WIFI_STOP")?;
    println!("P135_PUBLISH_PASS count=5 source=simulated");
    Ok(())
}
