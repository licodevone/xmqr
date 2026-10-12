use std::process::Command;

#[test]
fn version_exits_before_configuration_and_state() {
    let directory = tempfile::tempdir().unwrap();
    let state = directory.path().join("must-not-exist");
    for argument in ["--version", "-V"] {
        let output = Command::new(env!("CARGO_BIN_EXE_mqtt-broker"))
            .arg(argument)
            .env("MQTT_CONFIG", directory.path().join("missing.toml"))
            .env("MQTT_STATE_DIR", &state)
            .env("RUST_LOG", "invalid logging filter")
            .output()
            .unwrap();
        assert!(output.status.success());
        assert_eq!(
            output.stdout,
            format!("mqtt-broker {}\n", env!("CARGO_PKG_VERSION")).as_bytes()
        );
        assert_eq!(output.stderr.len(), 0);
        assert!(!state.exists());
    }
}

#[test]
fn unsupported_arguments_are_rejected_without_echo_or_state() {
    let directory = tempfile::tempdir().unwrap();
    let state = directory.path().join("must-not-exist");
    for arguments in [
        vec!["private-fixture"],
        vec!["--version", "private-fixture"],
    ] {
        let output = Command::new(env!("CARGO_BIN_EXE_mqtt-broker"))
            .args(arguments)
            .env("MQTT_CONFIG", directory.path().join("missing.toml"))
            .env("MQTT_STATE_DIR", &state)
            .output()
            .unwrap();
        assert_eq!(output.status.code(), Some(2));
        assert_eq!(output.stdout.len(), 0);
        assert!(!String::from_utf8_lossy(&output.stderr).contains("private-fixture"));
        assert!(!state.exists());
    }
}
