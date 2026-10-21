// SPDX-License-Identifier: MIT
//! Test fixture only: stdin password to the broker's bounded Argon2id profile.
//! Fixed salt is deliberately reproducible and MUST NOT provision real users.
use argon2::{Algorithm, Argon2, Params, PasswordHasher, Version, password_hash::SaltString};
use std::io::{self, Read};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut password = Vec::new();
    io::stdin().take(1025).read_to_end(&mut password)?;
    if password.is_empty() || password.len() > 1024 {
        return Err("fixture password must contain 1..=1024 bytes".into());
    }
    let salt = SaltString::encode_b64(b"p242-test-salt-16")
        .map_err(|error| io::Error::other(error.to_string()))?;
    let params =
        Params::new(19_456, 2, 1, Some(32)).map_err(|error| io::Error::other(error.to_string()))?;
    let hash = Argon2::new(Algorithm::Argon2id, Version::V0x13, params)
        .hash_password(&password, &salt)
        .map_err(|error| io::Error::other(error.to_string()))?;
    println!("{hash}");
    Ok(())
}
