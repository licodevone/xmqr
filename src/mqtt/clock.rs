//! Monotonic process progress with a durable UTC floor, without a blocking lock.
#[cfg(test)]
use std::sync::Arc;
#[cfg(test)]
use std::sync::atomic::AtomicBool;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{Instant, SystemTime, UNIX_EPOCH};

use super::router::RouterError;

#[derive(Debug)]
pub(super) struct ExpiryClock {
    start: Instant,
    epoch: AtomicU64,
    logical: AtomicU64,
    #[cfg(test)]
    manual: Option<Arc<ManualTime>>,
}

impl ExpiryClock {
    pub(super) fn new(watermark: u64) -> Result<Self, RouterError> {
        let wall = wall_ms(SystemTime::now())?;
        Ok(Self {
            start: Instant::now(),
            epoch: AtomicU64::new(watermark.max(wall)),
            logical: AtomicU64::new(watermark.max(wall)),
            #[cfg(test)]
            manual: None,
        })
    }

    fn sample(&self) -> Result<(u64, u64), RouterError> {
        #[cfg(test)]
        if let Some(manual) = &self.manual {
            if manual.invalid.load(Ordering::SeqCst) {
                return Err(RouterError::Clock);
            }
            return Ok((
                manual.wall.load(Ordering::SeqCst),
                manual.elapsed.load(Ordering::SeqCst),
            ));
        }
        Ok((
            wall_ms(SystemTime::now())?,
            u64::try_from(self.start.elapsed().as_millis()).map_err(|_| RouterError::Clock)?,
        ))
    }

    pub(super) fn now(&self) -> Result<u64, RouterError> {
        let (wall, elapsed) = self.sample()?;
        let observed_epoch = wall.saturating_sub(elapsed);
        let epoch = self
            .epoch
            .fetch_max(observed_epoch, Ordering::SeqCst)
            .max(observed_epoch);
        let sampled = epoch.checked_add(elapsed).ok_or(RouterError::Clock)?;
        Ok(self
            .logical
            .fetch_max(sampled, Ordering::SeqCst)
            .max(sampled))
    }

    pub(super) fn remaining(
        &self,
        deadline: u64,
        original: Option<u32>,
    ) -> Result<u32, RouterError> {
        remaining_at(deadline, original, self.now()?)
    }

    #[cfg(test)]
    pub(super) fn manual(wall: u64, watermark: u64) -> (Arc<Self>, Arc<ManualTime>) {
        let input = Arc::new(ManualTime {
            wall: AtomicU64::new(wall),
            elapsed: AtomicU64::new(0),
            invalid: AtomicBool::new(false),
        });
        let clock = Arc::new(Self {
            start: Instant::now(),
            epoch: AtomicU64::new(watermark.max(wall)),
            logical: AtomicU64::new(watermark.max(wall)),
            manual: Some(input.clone()),
        });
        (clock, input)
    }
}

pub(super) fn wall_ms(instant: SystemTime) -> Result<u64, RouterError> {
    let duration = instant
        .duration_since(UNIX_EPOCH)
        .map_err(|_| RouterError::Clock)?;
    u64::try_from(duration.as_millis()).map_err(|_| RouterError::Clock)
}

pub(super) fn remaining_at(
    deadline: u64,
    original: Option<u32>,
    now: u64,
) -> Result<u32, RouterError> {
    let remaining = u32::try_from(deadline.saturating_sub(now).div_ceil(1000))
        .map_err(|_| RouterError::Clock)?;
    Ok(original.map_or(remaining, |original| remaining.min(original)))
}

#[derive(Debug, Clone, Copy)]
pub(super) struct ExpiryPermit {
    pub disposition: ExpiryDisposition,
    pub remaining: u32,
    pub deadline: u64,
    pub original: Option<u32>,
}

#[derive(Debug, Clone, Copy, Eq, PartialEq)]
pub(super) enum ExpiryDisposition {
    DiscardUnattempted,
    PreserveUncertain,
}

impl ExpiryPermit {
    pub(super) fn current(self, clock: &ExpiryClock) -> Result<bool, RouterError> {
        Ok(self.remaining == clock.remaining(self.deadline, self.original)?)
    }
}

pub(super) struct ExpiryRefreshBudget {
    pub deadline: tokio::time::Instant,
    attempts: u8,
}

impl ExpiryRefreshBudget {
    pub(super) fn new(now: tokio::time::Instant) -> Self {
        Self {
            deadline: now + std::time::Duration::from_secs(3),
            attempts: 0,
        }
    }

    pub(super) fn allow(&mut self, now: tokio::time::Instant) -> bool {
        if self.attempts >= 4 || now >= self.deadline {
            return false;
        }
        self.attempts += 1;
        true
    }
}

#[cfg(test)]
#[derive(Debug)]
pub(super) struct ManualTime {
    wall: AtomicU64,
    elapsed: AtomicU64,
    invalid: AtomicBool,
}

#[cfg(test)]
impl ManualTime {
    pub(super) fn set(&self, wall: u64, elapsed: u64) {
        if elapsed < self.elapsed.load(Ordering::SeqCst) {
            self.invalid.store(true, Ordering::SeqCst);
            return;
        }
        self.wall.store(wall, Ordering::SeqCst);
        self.elapsed.store(elapsed, Ordering::SeqCst);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn p227e_live_rollback_keeps_elapsed_time_not_only_original_cap() {
        let (clock, input) = ExpiryClock::manual(10_000, 0);
        let deadline = 20_000;
        input.set(13_000, 3_000);
        assert_eq!(clock.remaining(deadline, Some(10)).unwrap(), 7);
        input.set(1_000, 4_000);
        assert_eq!(clock.remaining(deadline, Some(10)).unwrap(), 6);
        input.set(1_000, 10_000);
        assert_eq!(clock.remaining(deadline, Some(10)).unwrap(), 0);
    }

    #[test]
    fn p227e_recovery_floor_prevents_larger_ttl_after_clock_rollback() {
        let (clock, input) = ExpiryClock::manual(1_000, 14_000);
        assert_eq!(clock.remaining(20_000, Some(10)).unwrap(), 6);
        input.set(1_000, 2_000);
        assert_eq!(clock.remaining(20_000, Some(10)).unwrap(), 4);
    }

    #[test]
    fn p227e_forward_step_cannot_resurrect_after_later_rollback() {
        let (clock, input) = ExpiryClock::manual(10_000, 0);
        input.set(30_000, 1_000);
        assert_eq!(clock.remaining(20_000, Some(10)).unwrap(), 0);
        input.set(10_000, 2_000);
        assert_eq!(clock.remaining(20_000, Some(10)).unwrap(), 0);
    }

    #[test]
    fn p227e_permit_requires_same_integer_bucket_after_commit() {
        let (clock, input) = ExpiryClock::manual(10_000, 0);
        let permit = ExpiryPermit {
            disposition: ExpiryDisposition::PreserveUncertain,
            remaining: 7,
            deadline: 20_000,
            original: Some(10),
        };
        input.set(1_000, 3_500);
        assert!(permit.current(&clock).unwrap());
        input.set(1_000, 4_000);
        assert!(!permit.current(&clock).unwrap());
        let refreshed = ExpiryPermit {
            disposition: ExpiryDisposition::PreserveUncertain,
            remaining: 6,
            ..permit
        };
        assert!(refreshed.current(&clock).unwrap());
        let (restored, _) = ExpiryClock::manual(1_000, 14_000);
        assert_eq!(
            restored.remaining(20_000, Some(10)).unwrap(),
            refreshed.remaining
        );
    }

    #[test]
    fn p227e_zero_maximum_overflow_and_pre_epoch_fail_without_wrap() {
        assert!(wall_ms(UNIX_EPOCH - std::time::Duration::from_secs(1)).is_err());
        let (clock, input) = ExpiryClock::manual(u64::MAX, u64::MAX);
        input.set(1, 1);
        assert!(clock.now().is_err());
        assert_eq!(
            remaining_at(u64::from(u32::MAX) * 1000, Some(u32::MAX), 0).unwrap(),
            u32::MAX
        );
        assert_eq!(remaining_at(20_000, Some(0), 10_000).unwrap(), 0);
        assert!(remaining_at(u64::MAX, None, 0).is_err());
    }

    #[test]
    fn p227e_checkpoint_refresh_is_bounded_by_attempts_and_time() {
        let start = tokio::time::Instant::now();
        let mut budget = ExpiryRefreshBudget::new(start);
        let (clock, input) = ExpiryClock::manual(10_000, 0);
        let mut rejected = 0;
        while budget.allow(start) {
            let remaining = clock.remaining(20_000, Some(10)).unwrap();
            let permit = ExpiryPermit {
                disposition: ExpiryDisposition::PreserveUncertain,
                remaining,
                deadline: 20_000,
                original: Some(10),
            };
            rejected += 1;
            input.set(1_000, rejected * 1_000);
            assert!(!permit.current(&clock).unwrap());
        }
        assert_eq!(rejected, 4);
        let mut budget = ExpiryRefreshBudget::new(start);
        assert!(!budget.allow(start + std::time::Duration::from_secs(3)));
    }

    #[test]
    fn p227e_intent_invalid_manual_elapsed_is_refused() {
        let (clock, input) = ExpiryClock::manual(10_000, 0);
        input.set(1_000, 4_000);
        assert_eq!(clock.now().unwrap(), 14_000);
        input.set(1_000, 3_000);
        assert!(clock.now().is_err());
    }
}
