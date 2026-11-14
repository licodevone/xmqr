use crate::{
    model::{Action, Color, Kind, Snapshot, State, control_plan},
    platform::{self, Shortcut},
};
use std::{
    collections::HashMap,
    fs::File,
    sync::mpsc::{self, Receiver, SyncSender},
    thread,
    time::Duration,
};
use tao::{
    event::Event,
    event_loop::{ControlFlow, EventLoopBuilder, EventLoopProxy},
};
use tray_icon::{
    Icon, TrayIcon, TrayIconBuilder,
    menu::{
        Icon as MenuIcon, IconMenuItem, Menu, MenuEvent, MenuId, MenuItem, PredefinedMenuItem,
        Submenu,
    },
};

#[derive(Debug)]
enum UserEvent {
    Menu(MenuEvent),
    Snapshot(Snapshot),
    Done(String),
}
#[derive(Clone, Debug)]
enum Work {
    Control(String, Action),
    ControlAll(Action),
    Open(String, Shortcut),
}
#[derive(Clone)]
enum MenuAction {
    Work(Work),
    Quit,
}

struct App {
    tray: Option<TrayIcon>,
    snapshot: Snapshot,
    actions: HashMap<MenuId, MenuAction>,
    message: Option<String>,
    busy: bool,
    sender: SyncSender<Work>,
}

pub fn run(lock: File) -> Result<(), Box<dyn std::error::Error>> {
    let event_loop = EventLoopBuilder::<UserEvent>::with_user_event().build();
    let proxy = event_loop.create_proxy();
    MenuEvent::set_event_handler(Some(move |event| {
        let _ = proxy.send_event(UserEvent::Menu(event));
    }));
    let (sender, receiver) = mpsc::sync_channel(1);
    let proxy = event_loop.create_proxy();
    thread::spawn(move || worker(receiver, proxy));
    let mut app = App {
        tray: None,
        snapshot: Snapshot::default(),
        actions: HashMap::new(),
        message: None,
        busy: false,
        sender,
    };
    event_loop.run(move |event, _, flow| {
        // The file must live for the entire application, not only until run().
        let _keep_singleton = &lock;
        *flow = ControlFlow::Wait;
        let mut redraw = false;
        match event {
            Event::UserEvent(UserEvent::Snapshot(snapshot)) => {
                if app.snapshot != snapshot {
                    app.snapshot = snapshot;
                    redraw = true;
                }
            }
            Event::UserEvent(UserEvent::Done(message)) => {
                app.busy = false;
                app.message = Some(message);
                redraw = true;
            }
            Event::UserEvent(UserEvent::Menu(event)) => match app.actions.get(&event.id).cloned() {
                Some(MenuAction::Quit) => *flow = ControlFlow::Exit,
                Some(MenuAction::Work(work)) if !app.busy => {
                    match app.sender.try_send(work) {
                        Ok(()) => {
                            app.busy = true;
                            app.message = Some("Operação em andamento…".into());
                        }
                        Err(_) => {
                            app.message = Some("Outra operação está em andamento".into());
                        }
                    }
                    redraw = true;
                }
                _ => {}
            },
            _ => {}
        }
        if redraw && let Err(error) = app.render() {
            eprintln!("Não foi possível atualizar a bandeja: {error}");
            *flow = ControlFlow::Exit;
        }
    });
}

fn worker(receiver: Receiver<Work>, proxy: EventLoopProxy<UserEvent>) {
    loop {
        if proxy
            .send_event(UserEvent::Snapshot(platform::snapshot()))
            .is_err()
        {
            return;
        }
        match receiver.recv_timeout(Duration::from_secs(2)) {
            Ok(work) => {
                let result = match work {
                    Work::Control(id, action) => platform::control(&id, action, true),
                    Work::ControlAll(action) => platform::control_all(action, true),
                    Work::Open(id, shortcut) => platform::shortcut(&id, shortcut),
                };
                let message = match result {
                    Ok(()) => "Operação concluída".into(),
                    Err(error) => {
                        let message = error.to_string();
                        platform::notify_error(&message);
                        message
                    }
                };
                if proxy.send_event(UserEvent::Done(message)).is_err() {
                    return;
                }
            }
            Err(mpsc::RecvTimeoutError::Timeout) => {}
            Err(mpsc::RecvTimeoutError::Disconnected) => return,
        }
    }
}

impl App {
    fn render(&mut self) -> Result<(), Box<dyn std::error::Error>> {
        let color = self.snapshot.color();
        if color == Color::Hidden {
            self.tray = None;
            self.actions.clear();
            return Ok(());
        }
        let menu = Menu::new();
        self.actions.clear();
        menu.append(&MenuItem::new("XMQR — Serviços", false, None))?;
        if self.snapshot.error.is_some() {
            menu.append(&MenuItem::new("Inventário indisponível", false, None))?;
        }
        if let Some(message) = &self.message {
            menu.append(&MenuItem::new(brief(message, 28), false, None))?;
        }
        menu.append(&PredefinedMenuItem::separator())?;
        for (action, label) in [
            (Action::Start, "Iniciar todos"),
            (Action::Stop, "Parar todos"),
            (Action::Restart, "Reiniciar todos"),
            (Action::Recover, "Recuperar serviços"),
        ] {
            let enabled = !self.busy
                && control_plan(&self.snapshot, action).is_ok_and(|plan| !plan.is_empty());
            let item = action_item(label, enabled, action);
            self.actions.insert(
                item.id().clone(),
                MenuAction::Work(Work::ControlAll(action)),
            );
            menu.append(&item)?;
        }
        menu.append(&PredefinedMenuItem::separator())?;
        for entry in &self.snapshot.entries {
            let c = &entry.component;
            let name = c
                .display_name
                .strip_prefix("XMQR ")
                .unwrap_or(&c.display_name);
            let state = match entry.state {
                State::NeverStarted => "Não iniciado",
                State::Unknown => "Indisponível",
                State::CliOnly => "Somente CLI",
                state => state.label(),
            };
            let submenu = Submenu::new(format!("{} — {state}", brief(name, 20)), true);
            let shape = match c.kind {
                Kind::Broker => SERVER,
                Kind::Admin => PANEL,
                Kind::Client => TERMINAL,
            };
            let ink = match entry.state {
                State::Running => [35, 117, 78],
                State::Failed => [175, 49, 53],
                State::Pending => [143, 96, 21],
                _ => NEUTRAL,
            };
            submenu.set_icon(menu_icon(shape, ink));
            if let Some(detail) = &entry.detail {
                submenu.append(&MenuItem::new(brief(detail, 32), false, None))?;
            }
            if c.service_name.is_some() {
                for (action, label) in [
                    (Action::Start, "Iniciar"),
                    (Action::Stop, "Parar"),
                    (Action::Restart, "Reiniciar"),
                ] {
                    let item =
                        action_item(label, !self.busy && action.enabled(entry.state), action);
                    self.actions.insert(
                        item.id().clone(),
                        MenuAction::Work(Work::Control(c.id.clone(), action)),
                    );
                    submenu.append(&item)?;
                }
                submenu.append(&PredefinedMenuItem::separator())?;
            }
            for (configured, shortcut, label) in [
                (c.config_file.is_some(), Shortcut::Config, "Configuração"),
                (
                    c.config_file.is_some(),
                    Shortcut::ConfigDir,
                    "Pasta de configuração",
                ),
                (
                    c.certificates_dir.is_some(),
                    Shortcut::Certificates,
                    "Certificados",
                ),
                (c.logs_dir.is_some(), Shortcut::Logs, "Logs"),
                (c.panel_url.is_some(), Shortcut::Panel, "Painel"),
            ] {
                if configured {
                    let shape = match shortcut {
                        Shortcut::Config => TOOL,
                        Shortcut::ConfigDir => FOLDER,
                        Shortcut::Certificates => KEY,
                        Shortcut::Logs => DOCUMENT,
                        Shortcut::Panel => PANEL,
                    };
                    let item =
                        IconMenuItem::new(label, !self.busy, menu_icon(shape, NEUTRAL), None);
                    self.actions.insert(
                        item.id().clone(),
                        MenuAction::Work(Work::Open(c.id.clone(), shortcut)),
                    );
                    submenu.append(&item)?;
                }
            }
            menu.append(&submenu)?;
        }
        menu.append(&PredefinedMenuItem::separator())?;
        let quit = IconMenuItem::new("Sair da bandeja", true, menu_icon(EXIT, NEUTRAL), None);
        self.actions.insert(quit.id().clone(), MenuAction::Quit);
        menu.append(&quit)?;
        let tooltip = format!(
            "XMQR — {} componente(s) instalado(s){}",
            self.snapshot.entries.len(),
            if self.busy {
                " — operação em andamento"
            } else {
                " — estado dos serviços; MQTT não testado"
            }
        );
        let icon = icon(if self.busy { Color::Yellow } else { color })?;
        if let Some(tray) = &self.tray {
            tray.set_menu(Some(Box::new(menu)));
            tray.set_icon(Some(icon))?;
            tray.set_tooltip(Some(&tooltip))?;
        } else {
            self.tray = Some(
                TrayIconBuilder::new()
                    .with_menu(Box::new(menu))
                    .with_icon(icon)
                    .with_tooltip(tooltip)
                    .build()?,
            );
        }
        Ok(())
    }
}

const NEUTRAL: [u8; 3] = [79, 110, 136];
const PLAY: [u8; 8] = [0, 0x20, 0x30, 0x38, 0x3c, 0x38, 0x30, 0x20];
const STOP: [u8; 8] = [0, 0x7e, 0x42, 0x42, 0x42, 0x42, 0x7e, 0];
const REFRESH: [u8; 8] = [0x04, 0x3e, 0x46, 0x84, 0x81, 0x42, 0x3c, 0];
const TOOL: [u8; 8] = [0x06, 0x09, 0x09, 0x1e, 0x30, 0x60, 0xc0, 0x80];
const SERVER: [u8; 8] = [0x7e, 0x42, 0x52, 0x7e, 0x42, 0x52, 0x7e, 0];
const PANEL: [u8; 8] = [0x7e, 0x42, 0x5a, 0x42, 0x42, 0x7e, 0x18, 0x3c];
const TERMINAL: [u8; 8] = [0x7e, 0x42, 0x62, 0x52, 0x62, 0x4a, 0x7e, 0];
const FOLDER: [u8; 8] = [0, 0x70, 0x4f, 0x81, 0x81, 0x81, 0xff, 0];
const KEY: [u8; 8] = [0x38, 0x44, 0x44, 0x3c, 0x08, 0x0e, 0x08, 0x0e];
const DOCUMENT: [u8; 8] = [0x78, 0x4c, 0x56, 0x42, 0x5a, 0x42, 0x7e, 0];
const EXIT: [u8; 8] = [0x70, 0x50, 0x54, 0x5e, 0x5e, 0x54, 0x50, 0x70];

fn brief(text: &str, limit: usize) -> String {
    let mut chars = text.chars();
    let mut result: String = chars.by_ref().take(limit).collect();
    if chars.next().is_some() {
        result.push('…');
    }
    result.replace('&', "&&")
}

fn action_item(label: &str, enabled: bool, action: Action) -> IconMenuItem {
    let shape = match action {
        Action::Start => PLAY,
        Action::Stop => STOP,
        Action::Restart => REFRESH,
        Action::Recover => TOOL,
    };
    IconMenuItem::new(label, enabled, menu_icon(shape, NEUTRAL), None)
}

fn menu_icon(shape: [u8; 8], ink: [u8; 3]) -> Option<MenuIcon> {
    let mut pixels = Vec::with_capacity(16 * 16 * 4);
    for row in 0..16 {
        for column in 0..16 {
            let alpha = if shape[row / 2] & (0x80 >> (column / 2)) != 0 {
                255
            } else {
                0
            };
            pixels.extend([ink[0], ink[1], ink[2], alpha]);
        }
    }
    MenuIcon::from_rgba(pixels, 16, 16).ok()
}

fn icon(color: Color) -> Result<Icon, tray_icon::BadIcon> {
    Icon::from_rgba(
        crate::icon_pixels::rgba(include_bytes!("../assets/manager.rgba"), color),
        crate::icon_pixels::SIDE,
        crate::icon_pixels::SIDE,
    )
}
