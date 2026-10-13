// SPDX-License-Identifier: MIT
//! Opt-in physical retained campaign, gated by a distinct host MQTT principal.
use esp_idf_svc::mqtt::client::{Details, EspMqttClient, QoS};
use std::sync::atomic::{AtomicUsize, Ordering};

const TOPIC: &str = "e01/board/retained";
const CONTROL: &str = "e01/board/control";
static CONFIRMED: AtomicUsize = AtomicUsize::new(0);

pub fn observe(topic: Option<&str>, data: &[u8], details: Details) -> bool {
    if topic != Some(CONTROL) {
        return false;
    }
    if matches!(details, Details::Complete) && data.len() == 1 && (3..=5).contains(&data[0]) {
        CONFIRMED.store(usize::from(data[0]), Ordering::SeqCst);
    }
    true
}

pub fn run(client: &mut EspMqttClient<'_>, payload: &mut [u8]) -> Result<(), &'static str> {
    super::SUBSCRIBED.store(false, Ordering::SeqCst);
    client
        .subscribe(CONTROL, QoS::AtLeastOnce)
        .map_err(|_| "CONTROL_SUBSCRIBE")?;
    if !super::wait(10, || super::SUBSCRIBED.load(Ordering::SeqCst)) {
        return Err("CONTROL_SUBSCRIBE_TIMEOUT");
    }
    // MQTT-3.3.1-5/6/8: retain latest QoS1 value and replay to a NEW subscription.
    for sequence in [3_u8, 4] {
        payload[0] = sequence;
        let id = client
            .publish(TOPIC, QoS::AtLeastOnce, true, payload)
            .map_err(|_| "RETAINED_PUBLISH")?;
        if !super::wait(10, || {
            super::PUBLISHED.load(Ordering::SeqCst) == id as usize
        }) {
            return Err("RETAINED_ACK_TIMEOUT");
        }
        println!("E01_RETAINED_STORED version={} bytes=1024", sequence - 2);
        if !super::wait(15, || {
            CONFIRMED.load(Ordering::SeqCst) == usize::from(sequence)
        }) {
            return Err("OBSERVER_CONFIRM_TIMEOUT");
        }
        println!(
            "E01_RETAINED_REPLAY_PASS version={} bytes=1024",
            sequence - 2
        );
    }
    // MQTT-3.3.1-10/11: zero-byte retained publication deletes the saved value.
    let id = client
        .publish(TOPIC, QoS::AtLeastOnce, true, &[])
        .map_err(|_| "RETAINED_DELETE")?;
    if !super::wait(10, || {
        super::PUBLISHED.load(Ordering::SeqCst) == id as usize
    }) {
        return Err("RETAINED_ACK_TIMEOUT");
    }
    println!("E01_RETAINED_DELETED");
    if !super::wait(15, || CONFIRMED.load(Ordering::SeqCst) == 5) {
        return Err("OBSERVER_CONFIRM_TIMEOUT");
    }
    println!("E01_RETAINED_DELETE_PASS");
    Ok(())
}
