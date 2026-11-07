//! Bounded loading shared by TLS startup, configuration checks and rotation.

use std::{
    fs::OpenOptions,
    io::{self, Cursor, Read},
    path::Path,
};

use rustls::pki_types::{CertificateDer, CertificateRevocationListDer, PrivateKeyDer};
use zeroize::Zeroizing;

use super::TlsConfigError;

const MAX_IDENTITY_PEM_BYTES: u64 = 1024 * 1024;
const MAX_CRL_PEM_BYTES: u64 = 8 * 1024 * 1024;

fn read_pem(
    path: &Path,
    kind: &'static str,
    max_bytes: u64,
) -> Result<Zeroizing<Vec<u8>>, TlsConfigError> {
    let open_error = |source| TlsConfigError::OpenPem {
        kind,
        path: path.to_path_buf(),
        source,
    };
    if !path.metadata().map_err(open_error)?.is_file() {
        return Err(TlsConfigError::NonRegularPem { kind });
    }
    let mut options = OpenOptions::new();
    options.read(true);
    #[cfg(target_os = "linux")]
    {
        use std::os::unix::fs::OpenOptionsExt as _;
        // A path replaced by a FIFO between metadata and open must not block.
        options.custom_flags(libc::O_NONBLOCK);
    }
    let file = options.open(path).map_err(open_error)?;
    let metadata = file.metadata().map_err(open_error)?;
    if !metadata.is_file() {
        return Err(TlsConfigError::NonRegularPem { kind });
    }
    if metadata.len() > max_bytes {
        return Err(TlsConfigError::PemTooLarge { kind, max_bytes });
    }
    let capacity = usize::try_from(metadata.len() + 1).unwrap_or_default();
    let mut bytes = Zeroizing::new(Vec::with_capacity(capacity));
    file.take(max_bytes + 1)
        .read_to_end(&mut bytes)
        .map_err(open_error)?;
    if bytes.len() as u64 > max_bytes {
        return Err(TlsConfigError::PemTooLarge { kind, max_bytes });
    }
    Ok(bytes)
}

fn invalid_pem(path: &Path, kind: &'static str, source: &io::Error) -> TlsConfigError {
    TlsConfigError::InvalidPem {
        kind,
        path: path.to_path_buf(),
        message: source.to_string(),
    }
}

fn empty_pem(path: &Path, kind: &'static str) -> TlsConfigError {
    TlsConfigError::EmptyPem {
        kind,
        path: path.to_path_buf(),
    }
}

pub(super) fn load_certificates(
    path: &Path,
    kind: &'static str,
) -> Result<Vec<CertificateDer<'static>>, TlsConfigError> {
    let bytes = read_pem(path, kind, MAX_IDENTITY_PEM_BYTES)?;
    let certificates = rustls_pemfile::certs(&mut Cursor::new(bytes.as_slice()))
        .collect::<Result<Vec<_>, _>>()
        .map_err(|source| invalid_pem(path, kind, &source))?;
    if certificates.is_empty() {
        return Err(empty_pem(path, kind));
    }
    Ok(certificates)
}

pub(super) fn load_private_key(path: &Path) -> Result<PrivateKeyDer<'static>, TlsConfigError> {
    let kind = "server private key";
    let bytes = read_pem(path, kind, MAX_IDENTITY_PEM_BYTES)?;
    rustls_pemfile::private_key(&mut Cursor::new(bytes.as_slice()))
        .map_err(|source| invalid_pem(path, kind, &source))?
        .ok_or_else(|| empty_pem(path, kind))
}

pub(super) fn load_crls(
    path: &Path,
) -> Result<Vec<CertificateRevocationListDer<'static>>, TlsConfigError> {
    let kind = "client certificate revocation list";
    let bytes = read_pem(path, kind, MAX_CRL_PEM_BYTES)?;
    let crls = rustls_pemfile::crls(&mut Cursor::new(bytes.as_slice()))
        .collect::<Result<Vec<_>, _>>()
        .map_err(|source| invalid_pem(path, kind, &source))?;
    if crls.is_empty() {
        return Err(empty_pem(path, kind));
    }
    Ok(crls)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn pem_limit_is_inclusive_for_identity_and_revocation_material() {
        let root = tempfile::tempdir().unwrap();
        let path = root.path().join("fixture.pem");
        let file = std::fs::File::create(&path).unwrap();
        for limit in [MAX_IDENTITY_PEM_BYTES, MAX_CRL_PEM_BYTES] {
            file.set_len(limit).unwrap();
            assert_eq!(
                read_pem(&path, "fixture", limit).unwrap().len() as u64,
                limit
            );
            file.set_len(limit + 1).unwrap();
            assert!(matches!(
                read_pem(&path, "fixture", limit),
                Err(TlsConfigError::PemTooLarge { max_bytes, .. }) if max_bytes == limit
            ));
        }
    }

    #[test]
    fn all_tls_loaders_reject_non_regular_material() {
        let root = tempfile::tempdir().unwrap();
        let path = root.path();
        assert!(matches!(
            load_certificates(path, "server certificate"),
            Err(TlsConfigError::NonRegularPem { .. })
        ));
        assert!(matches!(
            load_private_key(path),
            Err(TlsConfigError::NonRegularPem { .. })
        ));
        assert!(matches!(
            load_crls(path),
            Err(TlsConfigError::NonRegularPem { .. })
        ));
    }

    #[cfg(unix)]
    #[test]
    fn pem_reader_accepts_renewal_symlinks_to_regular_files() {
        let root = tempfile::tempdir().unwrap();
        let real = root.path().join("certificate.pem");
        let link = root.path().join("active.pem");
        std::fs::write(&real, b"fixture").unwrap();
        std::os::unix::fs::symlink(&real, &link).unwrap();
        assert_eq!(
            read_pem(&link, "fixture", MAX_IDENTITY_PEM_BYTES)
                .unwrap()
                .as_slice(),
            b"fixture"
        );
    }
}
