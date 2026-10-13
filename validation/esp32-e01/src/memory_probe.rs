// SPDX-License-Identifier: MIT
//! Quantized safe allocation probe, NOT total-free/minimum-free heap statistics.
pub const STEP: usize = 4096;
pub const LIMIT: usize = 196608;

pub fn bounded_probe(mut available: impl FnMut(usize) -> bool) -> usize {
    let mut largest = 0;
    for size in (STEP..=LIMIT).step_by(STEP) {
        if !available(size) {
            break;
        }
        largest = size;
    }
    largest
}

pub fn measure() -> usize {
    bounded_probe(|size| {
        let mut allocation = Vec::<u8>::new();
        allocation.try_reserve_exact(size).is_ok()
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn stops_on_first_failure_and_never_exceeds_limit() {
        let mut attempts = Vec::new();
        assert_eq!(
            bounded_probe(|size| {
                attempts.push(size);
                size <= 3 * STEP
            }),
            3 * STEP
        );
        assert_eq!(attempts, vec![STEP, 2 * STEP, 3 * STEP, 4 * STEP]);
        assert_eq!(bounded_probe(|_| true), LIMIT);
        assert_eq!(bounded_probe(|_| false), 0);
    }
    #[test]
    fn host_measure_is_bounded_and_quantized() {
        let value = measure();
        assert!(value <= LIMIT && value % STEP == 0);
    }
}
