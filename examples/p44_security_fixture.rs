// SPDX-License-Identifier: MIT
//! Fixed public test password/hash generator, never for production credentials.
use argon2::password_hash::{PasswordHasher, SaltString};
fn main() {
    let salt = SaltString::encode_b64(b"sixteen-byte-salt").expect("fixed test salt");
    let password: &[u8] = if std::env::args().nth(1).as_deref() == Some("rotated") {
        b"fixture-new-pass"
    } else {
        b"fixture-pass"
    };
    let hash = mqtt_broker::auth::argon2_context()
        .hash_password(password, &salt)
        .expect("fixed test hash");
    println!("{hash}");
}
