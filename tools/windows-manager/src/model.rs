//! Platform-independent presentation and input policy.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Kind {
    Broker,
    Client,
    Admin,
}

impl Kind {
    pub fn parse(value: &str) -> Option<Self> {
        match value {
            "broker" => Some(Self::Broker),
            "client" => Some(Self::Client),
            "admin" => Some(Self::Admin),
            _ => None,
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Component {
    pub id: String,
    pub kind: Kind,
    pub display_name: String,
    pub executable: String,
    pub service_name: Option<String>,
    pub config_file: Option<String>,
    pub certificates_dir: Option<String>,
    pub logs_dir: Option<String>,
    pub panel_url: Option<String>,
}

impl Component {
    pub fn valid(&self) -> bool {
        valid_id(&self.id)
            && !self.display_name.is_empty()
            && self.display_name.len() <= 120
            && !self.display_name.chars().any(char::is_control)
            && local_absolute_path(&self.executable)
            && self
                .service_name
                .as_deref()
                .is_none_or(|name| service_matches(self.kind, name))
            && [&self.config_file, &self.certificates_dir, &self.logs_dir]
                .iter()
                .all(|path| path.as_deref().is_none_or(local_absolute_path))
            && self.panel_url.as_deref().is_none_or(loopback_url)
    }
}

pub fn valid_id(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 80
        && value
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b == b'-')
}

pub fn service_matches(kind: Kind, name: &str) -> bool {
    valid_id(name)
        && match kind {
            Kind::Broker => name == "xmqr-broker",
            Kind::Admin => name == "xmqr-admin",
            Kind::Client => name.strip_prefix("xmqr-client-").is_some_and(valid_id),
        }
}

pub fn local_absolute_path(value: &str) -> bool {
    let bytes = value.as_bytes();
    bytes.len() >= 3
        && bytes.len() <= 32760
        && bytes[0].is_ascii_alphabetic()
        && bytes[1] == b':'
        && matches!(bytes[2], b'\\' | b'/')
        && !value.chars().any(|c| c.is_control() || c == '"')
        && !value[2..].contains(':')
}

pub fn loopback_url(value: &str) -> bool {
    let Some(authority) = value.strip_prefix("http://") else {
        return false;
    };
    let authority = authority.strip_suffix('/').unwrap_or(authority);
    let port = ["127.0.0.1:", "[::1]:"]
        .iter()
        .find_map(|prefix| authority.strip_prefix(prefix));
    port.is_some_and(|port| {
        !port.is_empty()
            && port.bytes().all(|b| b.is_ascii_digit())
            && port.parse::<u16>().is_ok_and(|p| p != 0)
    })
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum State {
    Running,
    Stopped,
    Pending,
    Failed,
    Unknown,
    CliOnly,
}

impl State {
    pub fn label(self) -> &'static str {
        match self {
            Self::Running => "Em execução",
            Self::Stopped => "Parado",
            Self::Pending => "Em transição",
            Self::Failed => "Falha",
            Self::Unknown => "Estado indisponível",
            Self::CliOnly => "CLI instalada; sem serviço",
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Entry {
    pub component: Component,
    pub state: State,
    pub detail: Option<String>,
}

#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct Snapshot {
    pub entries: Vec<Entry>,
    pub error: Option<String>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Color {
    Hidden,
    Gray,
    Green,
    Yellow,
    Red,
}

impl Snapshot {
    pub fn color(&self) -> Color {
        if self.error.is_some()
            || self
                .entries
                .iter()
                .any(|e| matches!(e.state, State::Failed | State::Unknown))
        {
            return Color::Red;
        }
        if self.entries.is_empty() {
            return Color::Hidden;
        }
        let states: Vec<_> = self
            .entries
            .iter()
            .map(|e| e.state)
            .filter(|s| *s != State::CliOnly)
            .collect();
        if states.is_empty() || states.iter().all(|s| *s == State::Stopped) {
            return Color::Gray;
        }
        if states.iter().all(|s| *s == State::Running) {
            return Color::Green;
        }
        Color::Yellow
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Action {
    Start,
    Stop,
    Restart,
}

impl Action {
    pub fn parse(value: &str) -> Option<Self> {
        match value {
            "start" => Some(Self::Start),
            "stop" => Some(Self::Stop),
            "restart" => Some(Self::Restart),
            _ => None,
        }
    }
    pub fn name(self) -> &'static str {
        match self {
            Self::Start => "start",
            Self::Stop => "stop",
            Self::Restart => "restart",
        }
    }
    pub fn enabled(self, state: State) -> bool {
        match self {
            Self::Start => matches!(state, State::Stopped | State::Failed),
            Self::Stop | Self::Restart => state == State::Running,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn component(kind: Kind, id: &str) -> Component {
        Component {
            id: id.into(),
            kind,
            display_name: id.into(),
            executable: r"C:\Program Files\XMQR\app.exe".into(),
            service_name: None,
            config_file: None,
            certificates_dir: None,
            logs_dir: None,
            panel_url: None,
        }
    }
    fn snapshot(states: &[State]) -> Snapshot {
        Snapshot {
            entries: states
                .iter()
                .enumerate()
                .map(|(i, s)| Entry {
                    component: component(Kind::Client, &format!("client-{i}")),
                    state: *s,
                    detail: None,
                })
                .collect(),
            error: None,
        }
    }
    #[test]
    fn absent_components_never_get_placeholder_entries() {
        for mask in 0..8 {
            let entries: Vec<_> = [Kind::Broker, Kind::Client, Kind::Admin]
                .into_iter()
                .enumerate()
                .filter(|(i, _)| mask & (1 << i) != 0)
                .map(|(i, kind)| Entry {
                    component: component(kind, &format!("installed-{i}")),
                    state: State::Stopped,
                    detail: None,
                })
                .collect();
            assert_eq!(entries.len(), (mask as u32).count_ones() as usize);
            let s = Snapshot {
                entries,
                error: None,
            };
            assert_eq!(s.color() == Color::Hidden, mask == 0);
        }
    }
    #[test]
    fn aggregate_never_reports_green_for_mixed_failed_or_unknown() {
        assert_eq!(
            snapshot(&[State::Running, State::Running]).color(),
            Color::Green
        );
        assert_eq!(
            snapshot(&[State::Running, State::Stopped]).color(),
            Color::Yellow
        );
        assert_eq!(snapshot(&[State::Pending]).color(), Color::Yellow);
        assert_eq!(
            snapshot(&[State::Running, State::Failed]).color(),
            Color::Red
        );
        assert_eq!(snapshot(&[State::Unknown]).color(), Color::Red);
        assert_eq!(snapshot(&[State::CliOnly]).color(), Color::Gray);
        assert_eq!(
            snapshot(&[State::Running, State::CliOnly]).color(),
            Color::Green
        );
        assert_eq!(
            Snapshot {
                error: Some("access denied".into()),
                ..Default::default()
            }
            .color(),
            Color::Red
        );
    }
    #[test]
    fn service_and_component_ids_cannot_inject_commands_or_target_other_services() {
        for value in [
            "",
            "xmqr-broker;Stop-Service Spooler",
            "xmqr-broker\n",
            "../broker",
            "xmqr broker",
        ] {
            assert!(!valid_id(value));
        }
        assert!(service_matches(Kind::Broker, "xmqr-broker"));
        assert!(!service_matches(Kind::Broker, "Spooler"));
        assert!(!service_matches(Kind::Admin, "xmqr-broker"));
        assert!(!service_matches(Kind::Client, "xmqr-client-"));
        assert!(service_matches(Kind::Client, "xmqr-client-line-01"));
    }
    #[test]
    fn path_and_panel_policy_rejects_relative_unc_remote_and_script_urls() {
        for path in [
            "config.toml",
            r"\server\share\file",
            r"C:relative",
            "C:\\file:stream",
            "C:\\a\"b",
            "",
        ] {
            assert!(!local_absolute_path(path), "{path:?}");
        }
        assert!(local_absolute_path(r"D:\XMQR custom\broker.toml"));
        for url in [
            "https://127.0.0.1:9080",
            "http://localhost:9080",
            "http://127.0.0.1:9080@evil",
            "http://127.0.0.1:0",
            "http://127.0.0.1:9080/?cmd=x",
            "file:///C:/a",
            "http://192.0.2.1:9080",
        ] {
            assert!(!loopback_url(url), "{url}");
        }
        assert!(loopback_url("http://127.0.0.1:9080/"));
        assert!(loopback_url("http://[::1]:9080"));
    }
    #[test]
    fn transitions_and_cli_disable_invalid_actions() {
        for state in [State::Pending, State::Unknown, State::CliOnly] {
            for action in [Action::Start, Action::Stop, Action::Restart] {
                assert!(!action.enabled(state));
            }
        }
        assert!(Action::Start.enabled(State::Failed));
        assert!(!Action::Restart.enabled(State::Stopped));
    }
    #[test]
    fn invalid_optional_fields_invalidate_registration() {
        let mut c = component(Kind::Broker, "broker");
        assert!(c.valid());
        c.config_file = Some("relative.toml".into());
        assert!(!c.valid());
        c.config_file = None;
        c.service_name = Some("xmqr-admin".into());
        assert!(!c.valid());
    }
}
