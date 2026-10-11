//! P55: refusal of incompatible durable state occurs before listener startup.
use mqtt_broker::persistence::Store;
use std::{
    collections::BTreeMap,
    fmt::Write as _,
    fs,
    net::{TcpListener, TcpStream},
    path::Path,
    process::{Command, Stdio},
    sync::{
        Arc,
        atomic::{AtomicBool, Ordering},
    },
    thread,
    time::{Duration, Instant},
};

const KEY: &[u8] = b"mqtt311.state.v1";

fn durable_files(directory: &Path) -> BTreeMap<String, Vec<u8>> {
    fs::read_dir(directory)
        .unwrap()
        .map(|entry| {
            let path = entry.unwrap().path();
            (
                path.file_name().unwrap().to_str().unwrap().to_owned(),
                fs::read(&path).unwrap(),
            )
        })
        .collect()
}

fn session(subscriptions: usize, offline: usize, inbound: usize, outbound: usize) -> String {
    let message = "{topic='test/state',payload='00ff2a',qos=1,retain=false}";
    let incoming = "{packet_id=7,message={topic='test/state',payload='00ff2a',qos=2,retain=false}}";
    let outgoing = "{packet_id=8,stage='await_pub_comp',message={topic='test/state',payload='00ff2a',qos=2,retain=false}}";
    format!(
        "principal='open-lab'\npersistent=true\nnext_packet_id=9\nsubscriptions={{{}}}\noffline=[{}]\ninbound_qos2=[{}]\noutbound=[{}]\n",
        if subscriptions == 2 {
            "'test/state'=2,'test/other'=1"
        } else {
            "'test/state'=2"
        },
        vec![message; offline].join(","),
        (0..inbound)
            .map(|index| incoming.replace("packet_id=7", &format!("packet_id={}", 7 + index)))
            .collect::<Vec<_>>()
            .join(","),
        (0..outbound)
            .map(|index| outgoing.replace("packet_id=8", &format!("packet_id={}", 8 + index)))
            .collect::<Vec<_>>()
            .join(",")
    )
}

fn fixture_document(version: u16, kind: usize) -> String {
    let mut document = format!(
        "version={version}\n[state.sessions.first]\n{}",
        session(
            if kind == 2 { 2 } else { 1 },
            if kind == 3 { 2 } else { 1 },
            if kind == 4 { 2 } else { 1 },
            if kind == 5 { 2 } else { 1 }
        )
    );
    if kind == 0 {
        write!(document, "[state.sessions.second]\n{}", session(1, 1, 1, 1)).unwrap();
    }
    document.push_str(
        "[state.retained.'test/state']\ntopic='test/state'\npayload='00ff2a'\nqos=1\nretain=true\n",
    );
    if kind == 1 {
        document.push_str("[state.retained.'test/other']\ntopic='test/other'\npayload='00ff2a'\nqos=1\nretain=true\n");
    }
    if version == 2 {
        document.push_str("[state.pending_wills.first]\nprincipal='open-lab'\n[state.pending_wills.first.message]\ntopic='test/will'\npayload='0102'\nqos=1\nretain=false\n");
    }
    document
}

#[cfg_attr(not(unix), ignore = "requires Unix directory fsync")]
#[test]
fn reduced_quotas_reject_startup_without_listeners_or_durable_mutation_v1_v2() {
    for version in [1, 2] {
        for (kind, field, reason) in [
            (0, "max_sessions", "sessions"),
            (1, "max_retained", "retained topics"),
            (2, "max_subscriptions", "subscriptions per session"),
            (3, "max_offline", "offline messages per session"),
            (4, "max_inflight", "inflight messages per session"),
            (5, "max_inflight", "inflight messages per session"),
        ] {
            let directory = tempfile::tempdir().unwrap();
            let state = directory.path().join("state");
            fs::create_dir(&state).unwrap();
            fs::write(state.join(".mqtt-broker-profile"), "open-lab\n").unwrap();
            let document = fixture_document(version, kind);
            // Both snapshot and committed WAL are present at the crash boundary.
            {
                let mut store = Store::open(&state).unwrap();
                store.put(KEY, document.as_bytes()).unwrap();
                store.snapshot().unwrap();
                store.put(KEY, document.as_bytes()).unwrap();
            }
            let before = durable_files(&state);
            let reserve = TcpListener::bind("127.0.0.1:0").unwrap();
            let address = reserve.local_addr().unwrap();
            drop(reserve);
            let config = directory.path().join("broker.toml");
            fs::write(&config, format!("version=1\n[broker]\nmode='open-lab'\nbind='{address}'\nstate_dir='state'\n[limits]\n{field}=1\n")).unwrap();
            let mut command = Command::new(env!("CARGO_BIN_EXE_mqtt-broker"));
            for (key, _) in std::env::vars_os() {
                if key.to_string_lossy().starts_with("MQTT_") {
                    command.env_remove(key);
                }
            }
            let log = directory.path().join("startup.log");
            command
                .env("MQTT_CONFIG", &config)
                .env("RUST_LOG", "info")
                .stdout(Stdio::from(fs::File::create(&log).unwrap()))
                .stderr(Stdio::from(
                    fs::OpenOptions::new().append(true).open(&log).unwrap(),
                ));
            let done = Arc::new(AtomicBool::new(false));
            let connected = Arc::new(AtomicBool::new(false));
            let watcher_done = done.clone();
            let watcher_connected = connected.clone();
            let watcher = thread::spawn(move || {
                while !watcher_done.load(Ordering::Acquire) {
                    if TcpStream::connect_timeout(&address, Duration::from_millis(5)).is_ok() {
                        watcher_connected.store(true, Ordering::Release);
                    }
                    thread::sleep(Duration::from_millis(1));
                }
            });
            let mut child = command.spawn().unwrap();
            let deadline = Instant::now() + Duration::from_secs(10);
            let status = loop {
                if let Some(status) = child.try_wait().unwrap() {
                    break status;
                }
                if Instant::now() >= deadline {
                    child.kill().unwrap();
                    break child.wait().unwrap();
                }
                thread::sleep(Duration::from_millis(5));
            };
            done.store(true, Ordering::Release);
            watcher.join().unwrap();
            let output = fs::read_to_string(&log).unwrap();
            assert!(!status.success(), "startup accepted reduced {field}");
            assert!(
                output.contains(&format!("MQTT durable state exceeds limit: {reason}"))
                    || output.contains(&format!("Limit(\"{reason}\")")),
                "{output}"
            );
            assert!(!output.contains("listener started"), "{output}");
            assert!(
                !connected.load(Ordering::Acquire),
                "startup exposed listener"
            );
            assert!(TcpStream::connect_timeout(&address, Duration::from_millis(5)).is_err());
            assert_eq!(
                durable_files(&state),
                before,
                "startup changed durable files"
            );
            // Reopen immediately: no writer lock, and the exact committed image survives.
            let store = Store::open(&state).unwrap();
            assert_eq!(store.get(KEY), Some(document.as_bytes()));
        }
    }
}
