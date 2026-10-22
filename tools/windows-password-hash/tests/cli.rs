// SPDX-License-Identifier: MIT
use argon2::{Argon2, PasswordHash, PasswordVerifier};
use std::{
    io::Write,
    process::{Command, Stdio},
};

#[test]
fn rejected_arguments_never_echo_their_contents() {
    let marker = "synthetic-rejected-argument-not-a-real-password";
    let output = Command::new(env!("CARGO_BIN_EXE_xmqr-windows-password-hash"))
        .arg(marker)
        .output()
        .unwrap();
    assert_eq!(output.status.code(), Some(2));
    assert!(output.stdout.is_empty());
    assert!(!String::from_utf8(output.stderr).unwrap().contains(marker));
}

#[test]
fn stdin_hash_is_the_only_stdout_and_verifies_without_password_disclosure() {
    let password = b"synthetic-cli-test-password-not-for-provisioning";
    let mut child = Command::new(env!("CARGO_BIN_EXE_xmqr-windows-password-hash"))
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    child.stdin.take().unwrap().write_all(password).unwrap();
    let output = child.wait_with_output().unwrap();
    assert!(output.status.success());
    assert!(output.stderr.is_empty());
    let text = String::from_utf8(output.stdout).unwrap();
    assert_eq!(text.lines().count(), 1);
    assert!(!text.contains(std::str::from_utf8(password).unwrap()));
    let hash = PasswordHash::new(text.trim_end()).unwrap();
    assert!(Argon2::default().verify_password(password, &hash).is_ok());
}
