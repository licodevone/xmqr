// SPDX-License-Identifier: MIT
//! Finite physical TLS rotation probe; the host owns all fixture changes.
use esp_idf_svc::{
    mqtt::client::{EspMqttClient, EventPayload, MqttClientConfiguration, MqttProtocolVersion},
    tls::X509,
    wifi::EspWifi,
};
use std::{
    sync::atomic::{AtomicBool, Ordering},
    thread,
    time::Duration,
};

static CONNECTED: AtomicBool = AtomicBool::new(false);
static ERROR: AtomicBool = AtomicBool::new(false);
static DISCONNECTED: AtomicBool = AtomicBool::new(false);

fn probe(expect_connected: bool) -> Result<(), &'static str> {
    CONNECTED.store(false, Ordering::SeqCst);
    ERROR.store(false, Ordering::SeqCst);
    DISCONNECTED.store(false, Ordering::SeqCst);
    let config = MqttClientConfiguration {
        protocol_version: Some(MqttProtocolVersion::V3_1_1),
        client_id: Some("e02-physical-board"),
        username: Some(super::private::MQTT_USERNAME),
        password: Some(super::private::MQTT_PASSWORD),
        server_certificate: Some(X509::pem_until_nul(super::private::CA)),
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
        ..Default::default()
    };
    let client = EspMqttClient::new_cb(super::private::MQTT_URL, &config, |event| {
        match event.payload() {
            EventPayload::Connected(_) => CONNECTED.store(true, Ordering::SeqCst),
            EventPayload::Disconnected => DISCONNECTED.store(true, Ordering::SeqCst),
            EventPayload::Error(_) => ERROR.store(true, Ordering::SeqCst),
            _ => {}
        }
    })
    .map_err(|_| "E02_MQTT_CREATE")?;
    let observed = super::wait(8, || {
        CONNECTED.load(Ordering::SeqCst)
            || ERROR.load(Ordering::SeqCst)
            || DISCONNECTED.load(Ordering::SeqCst)
    });
    let connected = CONNECTED.load(Ordering::SeqCst);
    let failed = ERROR.load(Ordering::SeqCst) || DISCONNECTED.load(Ordering::SeqCst);
    drop(client);
    if !observed
        || (expect_connected && !connected)
        || (!expect_connected && (connected || !failed))
    {
        return Err("E02_UNEXPECTED_HANDSHAKE");
    }
    Ok(())
}

fn stage(marker: &str, expect_connected: bool) -> Result<(), &'static str> {
    println!("E02_{marker}_READY");
    thread::sleep(Duration::from_secs(10));
    probe(expect_connected)?;
    println!("E02_{marker}_PASS");
    Ok(())
}

pub fn run(wifi: &mut EspWifi<'_>) -> Result<(), &'static str> {
    probe(true)?;
    println!("E02_BASELINE_PASS");
    stage("INVALID_KEY_ROLLBACK", true)?;
    stage("CERT_ROTATION", true)?;
    stage("FOREIGN_CA_REJECTION", false)?;
    stage("CA_ROLLBACK", true)?;
    stage("CRL_REVOCATION", false)?;
    stage("CRL_ROLLBACK", true)?;
    wifi.stop().map_err(|_| "E02_WIFI_STOP")?;
    println!("E02_PHYSICAL_PASS");
    Ok(())
}
