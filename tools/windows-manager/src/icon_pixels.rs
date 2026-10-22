//! Recolor the supplied symbol without adding pixels outside its alpha mask.
use crate::model::Color;

pub const SIDE: u32 = 32;
pub const BYTE_LEN: usize = 32 * 32 * 4;

pub fn rgba(source: &[u8; BYTE_LEN], color: Color) -> Vec<u8> {
    let mut pixels = source.to_vec();
    let online = color == Color::Green;
    let rgb = if online {
        [35, 190, 105]
    } else {
        [128, 137, 148]
    };
    for pixel in pixels.as_chunks_mut::<4>().0 {
        pixel[..3].copy_from_slice(&rgb);
        if !online {
            pixel[3] = u8::try_from(u16::from(pixel[3]) * 3 / 5)
                .expect("a faded alpha never exceeds the original byte");
        }
    }
    pixels
}

#[cfg(test)]
mod tests {
    use super::*;

    fn symbol() -> [u8; BYTE_LEN] {
        let mut source = [0; BYTE_LEN];
        source[0..4].copy_from_slice(&[240, 20, 10, 255]);
        source[4..8].copy_from_slice(&[20, 30, 240, 80]);
        source
    }

    #[test]
    fn online_preserves_silhouette_and_antialiasing_without_a_badge() {
        let source = symbol();
        let online = rgba(&source, Color::Green);
        assert_eq!(online.len(), source.len());
        assert_eq!(online[3], 255);
        assert_eq!(online[7], 80);
        for (before, after) in source
            .as_chunks::<4>()
            .0
            .iter()
            .zip(online.as_chunks::<4>().0)
        {
            assert_eq!(after[3], before[3]);
            if after[3] != 0 {
                assert!(after[1] > after[0] && after[1] > after[2]);
            }
        }
    }

    #[test]
    fn every_non_running_or_busy_presentation_is_faded_without_green() {
        let source = symbol();
        for state in [Color::Gray, Color::Hidden, Color::Yellow, Color::Red] {
            let faded = rgba(&source, state);
            assert!(faded[3] > 0 && faded[3] < source[3]);
            assert!(faded[7] > 0 && faded[7] < source[7]);
            for (before, after) in source
                .as_chunks::<4>()
                .0
                .iter()
                .zip(faded.as_chunks::<4>().0)
            {
                assert!(after[3] <= before[3]);
                if before[3] == 0 {
                    assert_eq!(after[3], 0);
                }
                assert!(after[0] <= after[1] && after[1] <= after[2]);
            }
        }
    }
}
