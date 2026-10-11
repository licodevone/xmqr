#[cfg(unix)]
use std::{
    thread,
    time::{Duration, Instant},
};
// P52: configuration is validated before state is created, using child envs.
use std::{
    fs,
    process::{Command, Stdio},
};

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
