// SPDX-License-Identifier: MIT
use std::{env, fs, path::PathBuf};

fn main() {
    println!("cargo:rustc-check-cfg=cfg(e02_campaign)");
    println!("cargo:rerun-if-env-changed=XMQR_E02_CAMPAIGN");
    let e02 = match env::var("XMQR_E02_CAMPAIGN").as_deref() {
        Ok("1") => {
            println!("cargo:rustc-cfg=e02_campaign");
            true
        }
        Ok("0") | Err(_) => false,
        _ => panic!("invalid E02 campaign mode"),
    };
    println!("cargo:rustc-check-cfg=cfg(e01_campaign)");
    println!("cargo:rerun-if-env-changed=XMQR_E01_CAMPAIGN");
    let campaign = match env::var("XMQR_E01_CAMPAIGN").as_deref() {
        Ok("1") => {
            println!("cargo:rustc-cfg=e01_campaign");
            true
        }
        Ok("0") | Err(_) => false,
        _ => panic!("invalid physical campaign mode"),
    };
    assert!(
        !(campaign && e02),
        "E01 and E02 campaigns are mutually exclusive"
    );
    println!("cargo:rustc-check-cfg=cfg(e01_retained)");
    println!("cargo:rerun-if-env-changed=XMQR_E01_RETAINED");
    match env::var("XMQR_E01_RETAINED").as_deref() {
        Ok("1") => println!("cargo:rustc-cfg=e01_retained"),
        Ok("0") | Err(_) => {}
        _ => panic!("invalid retained fixture mode"),
    }
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
    let config_path = root.join("firmware-config.json");
    println!("cargo:rerun-if-changed={}", config_path.display());
    let config: serde_json::Value =
        serde_json::from_slice(&fs::read(config_path).expect("private config unavailable"))
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
        let pem_path = root.join("certs").join(file);
        println!("cargo:rerun-if-changed={}", pem_path.display());
        let mut value = fs::read(pem_path).expect("private PEM unavailable");
        assert!(!value.contains(&0), "invalid PEM");
        value.push(0);
        generated.push_str(&format!("pub const {name}: &[u8] = &{value:?};\n"));
    }
    if campaign {
        let case_config = root.join("p85-case.json");
        println!("cargo:rerun-if-changed={}", case_config.display());
        let case: serde_json::Value =
            serde_json::from_slice(&fs::read(case_config).expect("private case unavailable"))
                .expect("private case invalid");
        let case_root = root
            .join(
                case["case_directory"]
                    .as_str()
                    .expect("private case directory required"),
            )
            .canonicalize()
            .expect("private case directory unavailable");
        assert!(
            case_root.parent() == Some(root.as_path()),
            "private case escaped"
        );
        let ca_path = case_root.join("bad-ca.crt");
        println!("cargo:rerun-if-changed={}", ca_path.display());
        let mut bad_ca = fs::read(ca_path).expect("negative CA unavailable");
        assert!(!bad_ca.contains(&0), "invalid negative CA");
        bad_ca.push(0);
        generated.push_str(&format!(
            "#[cfg(e01_campaign)] pub const BAD_CA: &[u8] = &{bad_ca:?};\n"
        ));
    }
    fs::write(out.join("private_config.rs"), generated).expect("private output unavailable");
    embuild::espidf::sysenv::output();
}
