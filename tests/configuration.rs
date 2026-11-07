#[cfg(unix)]
use std::process::Stdio;
#[cfg(unix)]
use std::{
    thread,
    time::{Duration, Instant},
};
// P52: configuration is validated before state is created, using child envs.
use std::{fs, process::Command};

fn broker(path: &std::path::Path) -> Command {
    let mut command = Command::new(env!("CARGO_BIN_EXE_mqtt-broker"));
    for (key, _) in std::env::vars_os() {
        if key.to_string_lossy().starts_with("MQTT_") {
            command.env_remove(key);
        }
    }
    command.env("MQTT_CONFIG", path);
    command
}

#[test]
fn check_config_reports_effective_limits_without_touching_state() {
    let directory = tempfile::tempdir().unwrap();
    let path = directory.path().join("broker.toml");
    fs::write(
        &path,
        "version=1\n[broker]\nmode='open-lab'\nstate_dir='private-fixture'\n[limits]\nmax_connections=1",
    )
    .unwrap();
    let output = broker(&path)
        .arg("--check-config")
        .env("MQTT_MAX_CONNECTIONS", "3")
        .output()
        .unwrap();
    assert!(output.status.success(), "{:?}", output.stderr);
    let report: serde_json::Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(report["valid"], true);
    assert_eq!(report["profile"], "open-lab");
    assert_eq!(report["max_connections"], 3);
    assert!(!directory.path().join("private-fixture").exists());
    assert!(!String::from_utf8_lossy(&output.stdout).contains("private-fixture"));
}

#[test]
fn check_config_rejects_invalid_overrides_and_missing_security_files() {
    for (configuration, overrides) in [
        (
            "[broker]\nmode='open-lab'\nstate_dir='state'",
            Some(("MQTT_MAX_CONNECTIONS", "private-fixture")),
        ),
        (
            "[broker]\nmode='open-lab'\nstate_dir='state'\nwss_allowed_origins=['https://private-fixture.example']",
            None,
        ),
        (
            "[broker]\nmode='secure-mtls'\nstate_dir='state'\n[tls]\nserver_cert='private-fixture'\nserver_key='missing.key'\nclient_ca='missing.ca'\n[security]\nbundle='missing.toml'",
            None,
        ),
    ] {
        let directory = tempfile::tempdir().unwrap();
        let path = directory.path().join("broker.toml");
        fs::write(&path, format!("version=1\n{configuration}")).unwrap();
        let mut command = broker(&path);
        if let Some((key, value)) = overrides {
            command.env(key, value);
        }
        let output = command.arg("--check-config").output().unwrap();
        assert_eq!(output.status.code(), Some(2));
        assert!(output.stdout.is_empty());
        assert!(!String::from_utf8_lossy(&output.stderr).contains("private-fixture"));
        assert!(!directory.path().join("state").exists());
    }
}

#[test]
fn check_config_rejects_oversized_tls_material_without_disclosing_paths() {
    let directory = tempfile::tempdir().unwrap();
    let path = directory.path().join("broker.toml");
    let material = directory.path().join("private-pem-fixture");
    fs::File::create(material)
        .unwrap()
        .set_len(1024 * 1024 + 1)
        .unwrap();
    fs::write(
        &path,
        "version=1\n[broker]\nmode='tls-password'\nstate_dir='state'\n[tls]\nserver_cert='private-pem-fixture'\nserver_key='key.pem'\n[security]\nbundle='bundle.toml'",
    )
    .unwrap();
    let output = broker(&path).arg("--check-config").output().unwrap();
    assert_eq!(output.status.code(), Some(2));
    assert_eq!(output.stdout, [] as [u8; 0]);
    let error = String::from_utf8_lossy(&output.stderr);
    assert!(error.contains("materiais TLS"));
    assert!(!error.contains("private-pem-fixture"));
    assert!(!directory.path().join("state").exists());
}

#[test]
fn invalid_configuration_never_creates_state_or_echoes_source() {
    for tail in [
        "unknown='private-fixture'",
        "[broker]\nmode='open-lab'\nbind='0.0.0.0:1883'",
        "[broker]\nmode='open-lab'\n[tls]\nserver_key='private-fixture'",
        "[broker]\nmode='open-lab'\n[monitor]\nbind='0.0.0.0:9090'",
        "[broker]\nmode='secure-mtls'",
        "[broker]\nmode='password-lab'\n[security]\nbundle='private-fixture'",
    ] {
        let directory = tempfile::tempdir().unwrap();
        let path = directory.path().join("broker.toml");
        let state = directory.path().join("state");
        fs::write(&path, format!("version=1\n{tail}\n")).unwrap();
        let output = broker(&path)
            .env("MQTT_STATE_DIR", &state)
            .output()
            .unwrap();
        assert!(!output.status.success());
        assert!(!state.exists(), "invalid configuration created state");
        assert!(!String::from_utf8_lossy(&output.stderr).contains("private-fixture"));
    }
}

#[test]
fn invalid_explicit_override_does_not_fall_back_to_file() {
    let directory = tempfile::tempdir().unwrap();
    let path = directory.path().join("broker.toml");
    fs::write(
        &path,
        "version=1\n[broker]\nmode='open-lab'\nbind='127.0.0.1:0'\nstate_dir='state'",
    )
    .unwrap();
    let result = broker(&path).env("MQTT_BIND", "invalid").output().unwrap();
    assert!(!result.status.success());
    assert!(!directory.path().join("state").exists());
}

#[test]
fn invalid_connection_limit_never_creates_state() {
    let directory = tempfile::tempdir().unwrap();
    let path = directory.path().join("broker.toml");
    let state = directory.path().join("state");
    for value in ["0", "65", "invalid"] {
        fs::write(
            &path,
            "version=1\n[broker]\nmode='open-lab'\n[limits]\nmax_connections=1",
        )
        .unwrap();
        let output = broker(&path)
            .env("MQTT_STATE_DIR", &state)
            .env("MQTT_MAX_CONNECTIONS", value)
            .output()
            .unwrap();
        assert!(!output.status.success());
        assert!(!state.exists());
    }
}

#[cfg(unix)]
#[test]
fn relative_file_configuration_starts_and_stops_durably() {
    let directory = tempfile::tempdir().unwrap();
    let path = directory.path().join("broker.toml");
    let log = directory.path().join("log");
    fs::write(
        &path,
        "version=1\n[broker]\nmode='open-lab'\nbind='127.0.0.1:0'\nstate_dir='state'",
    )
    .unwrap();
    let mut child = broker(&path)
        .env("RUST_LOG", "info")
        .stdout(Stdio::from(fs::File::create(&log).unwrap()))
        .stderr(Stdio::null())
        .spawn()
        .unwrap();
    let deadline = Instant::now() + Duration::from_secs(10);
    let ready = loop {
        if fs::read_to_string(&log)
            .unwrap()
            .contains("OPEN LAB listener started")
        {
            break true;
        }
        if child.try_wait().unwrap().is_some() || Instant::now() >= deadline {
            break false;
        }
        thread::sleep(Duration::from_millis(20));
    };
    if !ready {
        let _ = child.kill();
        let _ = child.wait();
        panic!("TOML listener did not start");
    }
    Command::new("kill")
        .args(["-TERM", &child.id().to_string()])
        .status()
        .unwrap();
    let deadline = Instant::now() + Duration::from_secs(20);
    loop {
        if let Some(status) = child.try_wait().unwrap() {
            assert!(status.success());
            break;
        }
        if Instant::now() >= deadline {
            let _ = child.kill();
            let _ = child.wait();
            panic!("shutdown deadline");
        }
        thread::sleep(Duration::from_millis(20));
    }
    assert!(directory.path().join("state/state.snapshot").is_file());
}

#[test]
fn invalid_state_quotas_never_create_state() {
    for (field, key, ceiling) in [
        ("max_sessions", "MQTT_MAX_SESSIONS", 64),
        ("max_retained", "MQTT_MAX_RETAINED", 256),
        ("max_subscriptions", "MQTT_MAX_SUBSCRIPTIONS", 256),
        ("max_offline", "MQTT_MAX_OFFLINE", 64),
        ("max_inflight", "MQTT_MAX_INFLIGHT", 32),
    ] {
        let directory = tempfile::tempdir().unwrap();
        let path = directory.path().join("broker.toml");
        let state = directory.path().join("state");
        fs::write(
            &path,
            format!("version=1\n[broker]\nmode='open-lab'\n[limits]\n{field}=1"),
        )
        .unwrap();
        for value in ["0".to_owned(), (ceiling + 1).to_string(), "invalid".into()] {
            let output = broker(&path)
                .env("MQTT_STATE_DIR", &state)
                .env(key, value)
                .output()
                .unwrap();
            assert!(!output.status.success());
            assert!(!state.exists());
        }
    }
}
