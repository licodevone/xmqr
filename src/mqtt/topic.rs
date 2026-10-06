// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Luis E. S. Pinheiro
//! Validated MQTT 3.1.1 topic names, filters and linear-time matching.

use std::{borrow::Borrow, fmt};

use serde::{Deserialize, Deserializer, Serialize, Serializer, de::Error as _};
use thiserror::Error;

/// Project resource limit, deliberately narrower than MQTT's 65,535-byte
/// encoded-string ceiling so routing work stays bounded per connection.
pub(crate) const MAX_TOPIC_BYTES: usize = 256;

#[derive(Clone, Copy, Debug, Error, Eq, PartialEq)]
pub(crate) enum TopicError {
    #[error("topic is empty")]
    Empty,
    #[error("topic exceeds the project byte limit")]
    TooLong,
    #[error("topic contains U+0000")]
    Null,
    #[error("topic name contains a wildcard")]
    WildcardInName,
    #[error("topic filter contains an invalid wildcard placement")]
    InvalidWildcard,
}

/// A concrete MQTT Topic Name. Wildcards are never valid in a PUBLISH name.
#[derive(Clone, Debug, Eq, Hash, Ord, PartialEq, PartialOrd)]
pub(crate) struct TopicName(String);

impl TopicName {
    pub(crate) fn as_str(&self) -> &str {
        &self.0
    }
}

impl TryFrom<String> for TopicName {
    type Error = TopicError;

    fn try_from(value: String) -> Result<Self, Self::Error> {
        validate_common(&value)?;
        if value.contains(['+', '#']) {
            return Err(TopicError::WildcardInName);
        }
        Ok(Self(value))
    }
}

impl Borrow<str> for TopicName {
    fn borrow(&self) -> &str {
        self.as_str()
    }
}

impl fmt::Display for TopicName {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(self.as_str())
    }
}

impl Serialize for TopicName {
    fn serialize<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        serializer.serialize_str(self.as_str())
    }
}

impl<'de> Deserialize<'de> for TopicName {
    fn deserialize<D: Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        Self::try_from(String::deserialize(deserializer)?).map_err(D::Error::custom)
    }
}

/// A validated MQTT Topic Filter. `+` occupies one complete level and `#`
/// occupies the final complete level.
#[derive(Clone, Debug, Eq, Hash, Ord, PartialEq, PartialOrd)]
pub(crate) struct TopicFilter(String);

impl TopicFilter {
    pub(crate) fn as_str(&self) -> &str {
        &self.0
    }

    /// Match one concrete name without allocations or backtracking.
    #[must_use]
    pub(crate) fn matches(&self, topic: &TopicName) -> bool {
        matches_filter(self.as_str(), topic.as_str())
    }
}

impl TryFrom<String> for TopicFilter {
    type Error = TopicError;

    fn try_from(value: String) -> Result<Self, Self::Error> {
        validate_filter(&value)?;
        Ok(Self(value))
    }
}

impl Borrow<str> for TopicFilter {
    fn borrow(&self) -> &str {
        self.as_str()
    }
}

impl fmt::Display for TopicFilter {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(self.as_str())
    }
}

impl Serialize for TopicFilter {
    fn serialize<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        serializer.serialize_str(self.as_str())
    }
}

impl<'de> Deserialize<'de> for TopicFilter {
    fn deserialize<D: Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        Self::try_from(String::deserialize(deserializer)?).map_err(D::Error::custom)
    }
}

pub(crate) fn valid_topic_name(value: &str) -> bool {
    validate_common(value).is_ok() && !value.contains(['+', '#'])
}

pub(crate) fn valid_topic_filter(value: &str) -> bool {
    validate_filter(value).is_ok()
}

fn validate_filter(value: &str) -> Result<(), TopicError> {
    validate_common(value)?;
    let mut levels = value.split('/').peekable();
    while let Some(level) = levels.next() {
        if level.contains('#') && (level != "#" || levels.peek().is_some()) {
            return Err(TopicError::InvalidWildcard);
        }
        if level.contains('+') && level != "+" {
            return Err(TopicError::InvalidWildcard);
        }
    }
    Ok(())
}

/// Match strings already validated as a Topic Filter and Topic Name.
/// Runtime is linear in the number of filter/topic levels and never
/// backtracks.
#[must_use]
pub(crate) fn matches_filter(filter: &str, topic: &str) -> bool {
    matches_filter_counted(filter, topic).0
}

fn matches_filter_counted(filter: &str, topic: &str) -> (bool, usize) {
    // MQTT-4.7.2-1: a leading wildcard never includes the $ namespace.
    let leading_wildcard = matches!(filter.split('/').next(), Some("+" | "#"));
    if topic.starts_with('$') && leading_wildcard {
        return (false, 1);
    }

    let mut filter_levels = filter.split('/');
    let mut topic_levels = topic.split('/');
    let mut steps = 0;
    loop {
        steps += 1;
        match (filter_levels.next(), topic_levels.next()) {
            (Some("#"), _) | (None, None) => return (true, steps),
            (Some("+"), Some(_)) => {}
            (Some(expected), Some(actual)) if expected == actual => {}
            _ => return (false, steps),
        }
    }
}

fn validate_common(value: &str) -> Result<(), TopicError> {
    if value.is_empty() {
        return Err(TopicError::Empty);
    }
    if value.len() > MAX_TOPIC_BYTES {
        return Err(TopicError::TooLong);
    }
    if value.contains('\0') {
        return Err(TopicError::Null);
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn name(value: &str) -> TopicName {
        TopicName::try_from(value.to_owned()).unwrap()
    }

    fn filter(value: &str) -> TopicFilter {
        TopicFilter::try_from(value.to_owned()).unwrap()
    }

    #[test]
    fn validates_names_and_wildcard_placement() {
        // MQTT-3.3.2-2 and MQTT-4.7.1-1/2/3.
        for value in ["a", "/", "/finance", "$SYS/status", "temperatura/ação"] {
            assert!(TopicName::try_from(value.to_owned()).is_ok(), "{value}");
            assert!(TopicFilter::try_from(value.to_owned()).is_ok(), "{value}");
        }
        for value in ["+", "#", "sport/+", "sport/#", "+/tennis/#"] {
            assert!(TopicFilter::try_from(value.to_owned()).is_ok(), "{value}");
            assert!(TopicName::try_from(value.to_owned()).is_err(), "{value}");
        }
        for value in [
            "",
            "sport+",
            "sport/#/ranking",
            "sport/tennis#",
            "+foo",
            "a\0b",
        ] {
            assert!(TopicFilter::try_from(value.to_owned()).is_err(), "{value}");
        }
        assert!(TopicFilter::try_from("a".repeat(MAX_TOPIC_BYTES + 1)).is_err());
    }

    #[test]
    fn normative_wildcard_and_empty_level_vectors() {
        // MQTT-4.7.1-2/3 and the non-normative examples in section 4.7.1.
        assert!(filter("sport/tennis/player1/#").matches(&name("sport/tennis/player1")));
        assert!(filter("sport/tennis/player1/#").matches(&name("sport/tennis/player1/ranking")));
        assert!(filter("sport/+").matches(&name("sport/")));
        assert!(!filter("sport/+").matches(&name("sport")));
        assert!(filter("+/+").matches(&name("/finance")));
        assert!(filter("/+").matches(&name("/finance")));
        assert!(!filter("+").matches(&name("/finance")));
        assert!(filter("temperatura/+").matches(&name("temperatura/ação")));
    }

    #[test]
    fn leading_wildcard_does_not_match_system_topics() {
        // MQTT-4.7.2-1.
        assert!(!filter("#").matches(&name("$SYS/status")));
        assert!(!filter("+/status").matches(&name("$SYS/status")));
        assert!(filter("$SYS/#").matches(&name("$SYS/status")));
        assert!(filter("$SYS/status").matches(&name("$SYS/status")));
    }

    #[test]
    fn generated_matcher_properties_and_work_bound_hold() {
        // Exhaustive bounded property set: exact filters match only identical
        // names, and matching work never exceeds one pass over filter levels.
        let levels = ["", "a", "β", "$SYS"];
        let mut names = Vec::new();
        for first in levels {
            names.push(first.to_owned());
            for second in levels {
                names.push(format!("{first}/{second}"));
                for third in levels {
                    names.push(format!("{first}/{second}/{third}"));
                }
            }
        }
        names.retain(|value| !value.is_empty());
        for left in &names {
            let exact = TopicFilter::try_from(left.clone()).unwrap();
            for right in &names {
                let topic = TopicName::try_from(right.clone()).unwrap();
                assert_eq!(exact.matches(&topic), left == right, "{left:?} {right:?}");
                let (_, steps) = matches_filter_counted(exact.as_str(), topic.as_str());
                assert!(steps <= exact.as_str().split('/').count() + 1);
            }
        }
    }

    #[test]
    fn generated_wildcards_agree_with_independent_recursive_reference() {
        // MQTT-4.7.1-2/3, MQTT-4.7.2-1. Exhaustive bounded property set;
        // the reference deliberately uses a different, recursive algorithm.
        fn reference(filter: &[&str], topic: &[&str]) -> bool {
            match (filter.split_first(), topic.split_first()) {
                (None, None) | (Some((&"#", _)), _) => true,
                (Some((head, rest)), Some((name, tail))) if *head == "+" || head == name => {
                    reference(rest, tail)
                }
                _ => false,
            }
        }
        fn words(alphabet: &[&str], depth: usize) -> Vec<String> {
            let mut result = alphabet.iter().map(|v| (*v).to_owned()).collect::<Vec<_>>();
            if depth > 1 {
                for prefix in words(alphabet, depth - 1) {
                    for level in alphabet {
                        result.push(format!("{prefix}/{level}"));
                    }
                }
            }
            result
        }
        let names = words(&["", "a", "β", "$SYS"], 3);
        let filters = words(&["", "a", "β", "$SYS", "+", "#"], 3);
        for candidate in filters {
            let Ok(filter) = TopicFilter::try_from(candidate) else {
                continue;
            };
            let filter_levels = filter.as_str().split('/').collect::<Vec<_>>();
            for candidate in &names {
                let Ok(topic) = TopicName::try_from(candidate.clone()) else {
                    continue;
                };
                let hidden = topic.as_str().starts_with('$')
                    && matches!(filter_levels.first(), Some(&"+" | &"#"));
                let expected = !hidden
                    && reference(
                        &filter_levels,
                        &topic.as_str().split('/').collect::<Vec<_>>(),
                    );
                let (actual, steps) = matches_filter_counted(filter.as_str(), topic.as_str());
                assert_eq!(actual, expected, "{filter} vs {topic}");
                assert!(steps <= filter_levels.len() + 1);
            }
        }
    }

    #[test]
    fn maximum_depth_and_utf8_are_bounded_without_normalization() {
        // MQTT-4.7.3-4: no normalization or substitution during matching.
        let deep_name = format!("{}a", "/".repeat(MAX_TOPIC_BYTES - 1));
        let deep_filter = format!("{}+", "/".repeat(MAX_TOPIC_BYTES - 1));
        assert!(filter(&deep_filter).matches(&name(&deep_name)));
        assert!(matches_filter_counted(&deep_filter, &deep_name).1 <= MAX_TOPIC_BYTES + 1);
        assert!(!filter("café").matches(&name("cafe\u{301}")));
        assert!(!filter("a").matches(&name("A")));
        assert!(filter("a/+/b").matches(&name("a//b")));
        assert!(valid_topic_name(&"é".repeat(MAX_TOPIC_BYTES / 2)));
        assert!(!valid_topic_name(&"é".repeat(MAX_TOPIC_BYTES / 2 + 1)));
    }
}
