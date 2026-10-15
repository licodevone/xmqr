//! Local SIGUSR1 TLS rotation. Validation completes before publication.
use super::{
    MtlsFiles, TlsConfigError, TlsReloader, load_mtls_server_config, load_password_server_config,
};
use rustls::ServerConfig;
use std::{io, path::PathBuf, sync::Arc};

#[derive(Clone)]
pub enum TlsFiles {
    Mtls(MtlsFiles),
    Password {
        certificate_chain: PathBuf,
        private_key: PathBuf,
    },
}

impl TlsFiles {
    /// Build a complete candidate from the original configured paths.
    /// # Errors
    /// Rejects invalid PEM, TLS policy, key pairs, trust anchors and revocation lists.
    pub fn load(&self) -> Result<Arc<ServerConfig>, TlsConfigError> {
        match self {
            Self::Mtls(files) => load_mtls_server_config(files),
            Self::Password {
                certificate_chain,
                private_key,
            } => load_password_server_config(certificate_chain, private_key),
        }
    }
}

/// Aborts the signal task at broker shutdown.
pub struct TlsWatcher {
    task: tokio::task::JoinHandle<()>,
}

impl Drop for TlsWatcher {
    fn drop(&mut self) {
        self.task.abort();
    }
}

/// Watch SIGUSR1 on Unix. Failed candidates leave the previous TLS generation active.
/// # Errors
/// Returns a Unix signal registration error; non-Unix has no local signal watcher.
pub fn watch_tls(files: TlsFiles, reloader: TlsReloader) -> io::Result<Option<TlsWatcher>> {
    #[cfg(not(unix))]
    {
        let _ = (files, reloader);
        Ok(None)
    }
    #[cfg(unix)]
    {
        let mut signals =
            tokio::signal::unix::signal(tokio::signal::unix::SignalKind::user_defined1())?;
        let task = tokio::spawn(async move {
            let mut generation = 1_u64;
            while signals.recv().await.is_some() {
                let candidate = files.clone();
                if let Ok(Ok(config)) = tokio::task::spawn_blocking(move || candidate.load()).await
                {
                    if let Some(next) = generation.checked_add(1) {
                        reloader.publish(config);
                        generation = next;
                        tracing::info!(generation, "TLS rotation committed for new handshakes");
                    } else {
                        tracing::warn!("TLS rotation rejected; generation exhausted");
                    }
                } else {
                    tracing::warn!("TLS rotation rejected; prior generation retained");
                }
            }
        });
        Ok(Some(TlsWatcher { task }))
    }
}
