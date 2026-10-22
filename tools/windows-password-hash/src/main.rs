// SPDX-License-Identifier: MIT
//! Private stdin to a salted hash in the broker's exact bounded profile.
use argon2::{Algorithm, Argon2, Params, PasswordHasher, Version, password_hash::SaltString};
use rand_core::{OsRng, RngCore};
use std::{
    io::{self, Read, Write},
    process::ExitCode,
};
use zeroize::Zeroizing;

const MIN_PASSWORD_BYTES: usize = 32;
const MAX_PASSWORD_BYTES: usize = 1024;

fn context() -> Argon2<'static> {
    let params = Params::new(19_456, 2, 1, Some(32)).expect("valid fixed Argon2id parameters");
    Argon2::new(Algorithm::Argon2id, Version::V0x13, params)
}

fn validate_length(length: usize) -> io::Result<()> {
    if !(MIN_PASSWORD_BYTES..=MAX_PASSWORD_BYTES).contains(&length) {
        return Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            "stdin password must contain 32..1024 bytes",
        ));
    }
    Ok(())
}

fn read_password(reader: impl Read) -> io::Result<Zeroizing<Vec<u8>>> {
    let mut password = Zeroizing::new(Vec::new());
    reader
        .take((MAX_PASSWORD_BYTES + 1) as u64)
        .read_to_end(&mut password)?;
    validate_length(password.len())?;
    Ok(password)
}

fn hash_password(password: &[u8]) -> io::Result<String> {
    validate_length(password.len())?;
    let mut salt_bytes = [0_u8; 16];
    OsRng
        .try_fill_bytes(&mut salt_bytes)
        .map_err(|_| io::Error::other("operating system randomness unavailable"))?;
    let salt = SaltString::encode_b64(&salt_bytes)
        .map_err(|_| io::Error::other("unable to encode password salt"))?;
    context()
        .hash_password(password, &salt)
        .map(|hash| hash.to_string())
        .map_err(|_| io::Error::other("unable to hash password"))
}

fn run() -> io::Result<()> {
    if std::env::args_os().len() != 1 {
        return Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            "command-line arguments are not accepted; use private standard input",
        ));
    }
    let password = read_password(io::stdin().lock())?;
    let hash = Zeroizing::new(hash_password(&password)?);
    writeln!(io::stdout().lock(), "{}", hash.as_str())
}

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("XMQR password hash: {error}");
            ExitCode::from(2)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use argon2::{PasswordHash, PasswordVerifier};
    use std::io::Cursor;

    const TEST_PASSWORD: &[u8] = b"synthetic-unit-test-password-never-provision";

    #[test]
    fn hashes_verify_and_use_distinct_random_salts_in_the_broker_profile() {
        let first = hash_password(TEST_PASSWORD).unwrap();
        let second = hash_password(TEST_PASSWORD).unwrap();
        assert_ne!(first, second);
        let parsed = PasswordHash::new(&first).unwrap();
        let other = PasswordHash::new(&second).unwrap();
        assert_ne!(parsed.salt, other.salt);
        assert_eq!(parsed.algorithm.as_str(), "argon2id");
        assert_eq!(parsed.version, Some(19));
        let params = Params::try_from(&parsed).unwrap();
        assert_eq!(params.m_cost(), 19_456);
        assert_eq!(params.t_cost(), 2);
        assert_eq!(params.p_cost(), 1);
        assert_eq!(parsed.hash.unwrap().as_bytes().len(), 32);
        let mut salt = [0_u8; 32];
        assert_eq!(
            parsed.salt.unwrap().decode_b64(&mut salt).unwrap().len(),
            16
        );
        assert!(context().verify_password(TEST_PASSWORD, &parsed).is_ok());
        assert!(
            context()
                .verify_password(b"wrong-synthetic-unit-test-password", &parsed)
                .is_err()
        );
    }

    #[test]
    fn input_bounds_are_enforced_without_reading_an_unbounded_stream() {
        for length in [0, MIN_PASSWORD_BYTES - 1, MAX_PASSWORD_BYTES + 1] {
            let data = vec![b'x'; length];
            assert!(read_password(data.as_slice()).is_err());
            assert!(hash_password(&data).is_err());
        }
        for length in [MIN_PASSWORD_BYTES, MAX_PASSWORD_BYTES] {
            let data = vec![b'x'; length];
            assert_eq!(read_password(data.as_slice()).unwrap().as_slice(), data);
        }
        let mut source = Cursor::new(vec![b'x'; MAX_PASSWORD_BYTES * 4]);
        assert!(read_password(&mut source).is_err());
        assert_eq!(source.position(), (MAX_PASSWORD_BYTES + 1) as u64);
    }

    #[test]
    fn input_is_raw_bytes_without_silent_newline_or_encoding_changes() {
        let mut data = vec![b'x'; MIN_PASSWORD_BYTES];
        data.extend_from_slice(&[0, 0xff, b'\r', b'\n']);
        assert_eq!(read_password(data.as_slice()).unwrap().as_slice(), data);
    }
}
