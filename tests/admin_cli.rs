//! Distribution must identify the admin without opening private configuration.
use std::process::Command;

#[test]
fn admin_version_is_side_effect_free_for_both_spellings() {
    for flag in ["--version", "-V"] {
        let output = Command::new(env!("CARGO_BIN_EXE_mqtt-admin"))
            .arg(flag)
            .env("MQTT_STATE_DIR", "/nonexistent/xmqr-p78-state")
            .env("MQTT_USERS_FILE", "/nonexistent/xmqr-p78-users")
            .env("MQTT_SERVER_KEY", "/nonexistent/xmqr-p78-key")
            .output()
            .expect("admin version process");
        assert!(output.status.success());
        assert_eq!(
            output.stdout,
            format!("mqtt-admin {}\n", env!("CARGO_PKG_VERSION")).as_bytes()
        );
        assert_eq!(output.stderr, [] as [u8; 0]);
    }
}

#[test]
fn admin_version_does_not_accept_extra_arguments_or_echo_them() {
    let output = Command::new(env!("CARGO_BIN_EXE_mqtt-admin"))
        .args(["--version", "private-value-that-must-not-be-echoed"])
        .output()
        .expect("admin invalid arguments process");
    assert_eq!(output.status.code(), Some(2));
    assert_eq!(output.stdout, [] as [u8; 0]);
    assert!(
        !String::from_utf8_lossy(&output.stderr).contains("private-value-that-must-not-be-echoed")
    );
}
