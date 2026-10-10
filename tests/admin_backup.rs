use std::process::Command;

use tempfile::tempdir;

#[cfg(unix)]
#[test]
fn mqtt_admin_backup_verify_restore_round_trip() {
    let parent = tempdir().unwrap();
    let state = parent.path().join("state source");
    let backup = parent.path().join("backup copy");
    let restored = parent.path().join("restored state");
    std::fs::create_dir(&state).unwrap();

    let output = Command::new(env!("CARGO_BIN_EXE_mqtt-admin"))
        .args([
            "state",
            "backup",
            "--state-dir",
            state.to_str().unwrap(),
            "--destination",
            backup.to_str().unwrap(),
        ])
        .output()
        .unwrap();
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );

    let output = Command::new(env!("CARGO_BIN_EXE_mqtt-admin"))
        .args(["state", "verify", "--backup", backup.to_str().unwrap()])
        .output()
        .unwrap();
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );

    let output = Command::new(env!("CARGO_BIN_EXE_mqtt-admin"))
        .args([
            "state",
            "restore",
            "--backup",
            backup.to_str().unwrap(),
            "--state-dir",
            restored.to_str().unwrap(),
        ])
        .output()
        .unwrap();
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(restored.join("state.snapshot").is_file());
    assert!(restored.join("state.wal").is_file());
}
