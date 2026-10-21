// SPDX-License-Identifier: MIT
//! Validated service invocation. No shell expansion or environment mutation.
use std::{ffi::OsString, io, path::PathBuf};

pub struct Launch {
    pub service_name: String,
    pub logs: PathBuf,
    pub config: PathBuf,
}

impl Launch {
    pub fn parse(arguments: &[OsString]) -> io::Result<Self> {
        if arguments.len() != 5
            || arguments[0] != "--windows-service"
            || arguments[1] != "xmqr-broker"
            || arguments[3] != "--config"
        {
            return Err(invalid());
        }
        let logs = PathBuf::from(&arguments[2]);
        let config = PathBuf::from(&arguments[4]);
        if !logs.is_absolute() || !config.is_absolute() {
            return Err(invalid());
        }
        Ok(Self {
            service_name: "xmqr-broker".into(),
            logs,
            config,
        })
    }
}

fn invalid() -> io::Error {
    io::Error::new(
        io::ErrorKind::InvalidInput,
        "use --windows-service xmqr-broker ABSOLUTE_LOG_DIR --config ABSOLUTE_CONFIG_PATH",
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    fn valid() -> Vec<OsString> {
        vec![
            "--windows-service".into(),
            "xmqr-broker".into(),
            std::env::temp_dir().join("logs with spaces").into(),
            "--config".into(),
            std::env::temp_dir().join("config with spaces.toml").into(),
        ]
    }

    #[test]
    fn absolute_paths_with_spaces_are_preserved_without_shell_parsing() {
        let args = valid();
        let launch = Launch::parse(&args).unwrap();
        assert_eq!(launch.service_name, "xmqr-broker");
        assert_eq!(launch.logs.as_os_str(), args[2]);
        assert_eq!(launch.config.as_os_str(), args[4]);
    }

    #[test]
    fn unrelated_services_and_extra_arguments_are_rejected() {
        for name in [
            "Spooler",
            "xmqr-broker-other",
            "xmqr-broker; stop-process",
            "",
        ] {
            let mut args = valid();
            args[1] = name.into();
            assert!(Launch::parse(&args).is_err());
        }
        let mut args = valid();
        args.push("--ignored".into());
        assert!(Launch::parse(&args).is_err());
        for end in 0..5 {
            assert!(Launch::parse(&valid()[..end]).is_err());
        }
    }

    #[test]
    fn service_paths_must_not_depend_on_system32_working_directory() {
        for index in [2, 4] {
            let mut args = valid();
            args[index] = "relative/path".into();
            assert!(Launch::parse(&args).is_err());
        }
    }
}
