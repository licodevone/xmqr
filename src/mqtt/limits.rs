//! Immutable logical quotas shared by recovery, commits and routing.
use std::io;

/// Process-local MQTT state quotas. Defaults preserve the existing ceilings.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[allow(clippy::struct_field_names)] // Explicit maxima mirror configuration and avoid ambiguity.
pub struct StateLimits {
    pub(crate) max_sessions: usize,
    pub(crate) max_retained: usize,
    pub(crate) max_subscriptions: usize,
    pub(crate) max_offline: usize,
    pub(crate) max_inflight: usize,
}

impl Default for StateLimits {
    fn default() -> Self {
        Self {
            max_sessions: 64,
            max_retained: 256,
            max_subscriptions: 256,
            max_offline: 64,
            max_inflight: 32,
        }
    }
}

impl StateLimits {
    /// Validate positive quotas without exceeding the established ceilings.
    /// # Errors
    /// Returns `InvalidInput` for zero or a value above its ceiling.
    pub fn new(
        sessions: usize,
        retained: usize,
        subscriptions: usize,
        offline: usize,
        inflight: usize,
    ) -> io::Result<Self> {
        for (value, ceiling) in [
            (sessions, 64),
            (retained, 256),
            (subscriptions, 256),
            (offline, 64),
            (inflight, 32),
        ] {
            if !(1..=ceiling).contains(&value) {
                return Err(io::Error::new(
                    io::ErrorKind::InvalidInput,
                    "MQTT state quota outside supported range",
                ));
            }
        }
        Ok(Self {
            max_sessions: sessions,
            max_retained: retained,
            max_subscriptions: subscriptions,
            max_offline: offline,
            max_inflight: inflight,
        })
    }
}
