//! Local-only helper for preparing broker authentication configuration.

use std::{
    env,
    error::Error,
    fs::File,
    io::{self, BufReader},
    path::Path,
};

use argon2::password_hash::{PasswordHasher, SaltString};
use mqtt_broker::auth::argon2_context;
use rand_core::OsRng;
use sha2::{Digest, Sha256};
use zeroize::Zeroizing;

fn main() -> Result<(), Box<dyn Error>> {
    let arguments: Vec<_> = env::args_os().collect();
    match arguments.as_slice() {
        [_, command] if command == "hash-password" => hash_password(),
        [_, command, certificate] if command == "fingerprint" => {
            fingerprint(Path::new(certificate))
        }
        _ => {
            eprintln!("Usage: mqtt-admin hash-password | mqtt-admin fingerprint <client.crt>");
            std::process::exit(2);
        }
    }
}

fn hash_password() -> Result<(), Box<dyn Error>> {
    let password = Zeroizing::new(rpassword::prompt_password("Password: ")?);
    let confirmation = Zeroizing::new(rpassword::prompt_password("Confirm password: ")?);
    if password.is_empty() || password.len() > 1_024 || password != confirmation {
        return Err("passwords differ, are empty, or exceed 1024 bytes".into());
    }
    let salt = SaltString::generate(&mut OsRng);
    let hash = argon2_context()
        .hash_password(password.as_bytes(), &salt)
        .map_err(|_| io::Error::other("unable to hash password"))?;
    println!("password_hash = \"{hash}\"");
    Ok(())
}

fn fingerprint(path: &Path) -> Result<(), Box<dyn Error>> {
    let mut reader = BufReader::new(File::open(path)?);
    let mut certificates = rustls_pemfile::certs(&mut reader);
    let leaf = certificates.next().ok_or("no PEM certificate found")??;
    let digest = Sha256::digest(leaf.as_ref());
    print!("cert_sha256 = \"sha256:");
    for byte in digest {
        print!("{byte:02x}");
    }
    println!("\"");
    Ok(())
}
