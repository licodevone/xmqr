//! Local-only helper for preparing broker authentication configuration.

mod users;

use std::{
    env,
    error::Error,
    fs::File,
    io::{self, BufReader},
    path::{Path, PathBuf},
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
        [_, group, command, file_flag, file, username_flag, username]
            if group == "user"
                && command == "create"
                && file_flag == "--users-file"
                && username_flag == "--username" =>
        {
            let username = required_utf8(username, "username")?;
            let password_hash = prompt_password_hash()?;
            users::create_user(&PathBuf::from(file), username, &password_hash)?;
            println!("Usuario criado: {username}");
            Ok(())
        }
        [_, group, command, file_flag, file, username_flag, username]
            if group == "user"
                && command == "update-password"
                && file_flag == "--users-file"
                && username_flag == "--username" =>
        {
            let username = required_utf8(username, "username")?;
            let password_hash = prompt_password_hash()?;
            users::update_password(&PathBuf::from(file), username, &password_hash)?;
            println!("Senha atualizada: {username}");
            Ok(())
        }
        [_, group, command, file_flag, file, username_flag, username]
            if group == "user"
                && command == "delete"
                && file_flag == "--users-file"
                && username_flag == "--username" =>
        {
            let username = required_utf8(username, "username")?;
            users::delete_user(&PathBuf::from(file), username)?;
            println!("Usuario excluido: {username}");
            Ok(())
        }
        [_, group, command, file_flag, file]
            if group == "user" && command == "list" && file_flag == "--users-file" =>
        {
            for username in users::list_users(&PathBuf::from(file))? {
                println!("{username}");
            }
            Ok(())
        }
        _ => usage(),
    }
}

fn hash_password() -> Result<(), Box<dyn Error>> {
    let hash = prompt_password_hash()?;
    println!("password_hash = \"{hash}\"");
    Ok(())
}

fn prompt_password_hash() -> Result<String, Box<dyn Error>> {
    let password = Zeroizing::new(rpassword::prompt_password("Password: ")?);
    let confirmation = Zeroizing::new(rpassword::prompt_password("Confirm password: ")?);
    if password.is_empty()
        || password.len() > 1_024
        || password.chars().any(char::is_control)
        || password != confirmation
    {
        return Err("passwords differ, are invalid, or exceed 1024 bytes".into());
    }
    let salt = SaltString::generate(&mut OsRng);
    let hash = argon2_context()
        .hash_password(password.as_bytes(), &salt)
        .map_err(|_| io::Error::other("unable to hash password"))?
        .to_string();
    Ok(hash)
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

fn required_utf8<'a>(value: &'a std::ffi::OsStr, kind: &str) -> Result<&'a str, io::Error> {
    value
        .to_str()
        .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidInput, format!("{kind} must be UTF-8")))
}

fn usage() -> Result<(), Box<dyn Error>> {
    eprintln!(
        "Uso:\n  mqtt-admin user create --users-file ARQUIVO --username USUARIO\n  mqtt-admin user list --users-file ARQUIVO\n  mqtt-admin user update-password --users-file ARQUIVO --username USUARIO\n  mqtt-admin user delete --users-file ARQUIVO --username USUARIO\n  mqtt-admin hash-password\n  mqtt-admin fingerprint <client.crt>"
    );
    std::process::exit(2);
}
