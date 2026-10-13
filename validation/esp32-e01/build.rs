// SPDX-License-Identifier: MIT
use std::{env, fs, path::PathBuf};

fn main() {
    println!("cargo:rerun-if-env-changed=XMQR_E01_PRIVATE_DIR");
    let root =
        PathBuf::from(env::var_os("XMQR_E01_PRIVATE_DIR").expect("private directory required"))
            .canonicalize()
            .expect("private directory unavailable");
    let repo = PathBuf::from(env::var_os("CARGO_MANIFEST_DIR").unwrap())
        .ancestors()
        .nth(2)
        .unwrap()
        .canonicalize()
        .unwrap();
    let out = PathBuf::from(env::var_os("OUT_DIR").unwrap())
        .canonicalize()
        .unwrap();
    assert!(
        !root.starts_with(&repo) && out.starts_with(&root),
        "build must stay private"
    );
    let config: serde_json::Value = serde_json::from_slice(
        &fs::read(root.join("firmware-config.json")).expect("private config unavailable"),
    )
    .expect("private config invalid");
    let mut generated = String::new();
    for name in [
        "ssid",
        "wifi_password",
        "mqtt_url",
        "mqtt_username",
        "mqtt_password",
    ] {
        let value = config[name].as_str().expect("missing private field");
        assert!(!value.contains('\0'), "invalid private field");
        generated.push_str(&format!(
            "pub const {}: &str = {:?};\n",
            name.to_uppercase(),
            value
        ));
    }
    for (name, file) in [
        ("CA", "ca.crt"),
        ("CERT", "board.crt"),
        ("KEY", "board.key"),
    ] {
        let mut value = fs::read(root.join("certs").join(file)).expect("private PEM unavailable");
        assert!(!value.contains(&0), "invalid PEM");
        value.push(0);
        generated.push_str(&format!("pub const {name}: &[u8] = &{value:?};\n"));
    }
    fs::write(out.join("private_config.rs"), generated).expect("private output unavailable");
    embuild::espidf::sysenv::output();
}
