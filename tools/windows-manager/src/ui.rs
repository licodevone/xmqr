use crate::{
    model::{Action, Color, Snapshot, control_plan},
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
    menu::{Menu, MenuEvent, MenuId, MenuItem, PredefinedMenuItem, Submenu},
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
        menu.append(&MenuItem::new("XMQR — sistemas instalados", false, None))?;
        if let Some(error) = &self.snapshot.error {
            menu.append(&MenuItem::new(error, false, None))?;
        }
        if let Some(message) = &self.message {
            menu.append(&MenuItem::new(message, false, None))?;
        }
        menu.append(&PredefinedMenuItem::separator())?;
        for (action, label) in [
            (Action::Start, "Iniciar todos os serviços"),
            (Action::Stop, "Parar todos os serviços"),
            (Action::Restart, "Reiniciar todos os serviços"),
        ] {
            let enabled = !self.busy
                && control_plan(&self.snapshot, action).is_ok_and(|plan| !plan.is_empty());
            let item = MenuItem::new(label, enabled, None);
            self.actions.insert(
                item.id().clone(),
                MenuAction::Work(Work::ControlAll(action)),
            );
            menu.append(&item)?;
        }
        menu.append(&PredefinedMenuItem::separator())?;
        for entry in &self.snapshot.entries {
            let c = &entry.component;
            let submenu = Submenu::new(
                format!("{} — {}", c.display_name, entry.state.label()),
                true,
            );
            if let Some(detail) = &entry.detail {
                submenu.append(&MenuItem::new(detail, false, None))?;
            }
            if c.service_name.is_some() {
                for (action, label) in [
                    (Action::Start, "Iniciar"),
                    (Action::Stop, "Parar"),
                    (Action::Restart, "Reiniciar"),
                ] {
                    let item =
                        MenuItem::new(label, !self.busy && action.enabled(entry.state), None);
                    self.actions.insert(
                        item.id().clone(),
                        MenuAction::Work(Work::Control(c.id.clone(), action)),
                    );
                    submenu.append(&item)?;
                }
                submenu.append(&PredefinedMenuItem::separator())?;
            }
            for (configured, shortcut, label) in [
                (
                    c.config_file.is_some(),
                    Shortcut::Config,
                    "Abrir configuração",
                ),
                (
                    c.config_file.is_some(),
                    Shortcut::ConfigDir,
                    "Abrir pasta de configurações",
                ),
                (
                    c.certificates_dir.is_some(),
                    Shortcut::Certificates,
                    "Abrir pasta de certificados",
                ),
                (c.logs_dir.is_some(), Shortcut::Logs, "Abrir pasta de logs"),
                (c.panel_url.is_some(), Shortcut::Panel, "Abrir painel"),
            ] {
                if configured {
                    let item = MenuItem::new(label, !self.busy, None);
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
        menu.append(&MenuItem::new(
            "Verde: todos os serviços em execução; conexão MQTT não verificada",
            false,
            None,
        ))?;
        let quit = MenuItem::new("Sair da bandeja (mantém os serviços)", true, None);
        self.actions.insert(quit.id().clone(), MenuAction::Quit);
        menu.append(&quit)?;
        let tooltip = format!(
            "XMQR — {} componente(s) instalado(s){}",
            self.snapshot.entries.len(),
            if self.busy {
                " — operação em andamento"
            } else {
                ""
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

fn icon(color: Color) -> Result<Icon, tray_icon::BadIcon> {
    Icon::from_rgba(
        crate::icon_pixels::rgba(include_bytes!("../assets/manager.rgba"), color),
        crate::icon_pixels::SIDE,
        crate::icon_pixels::SIDE,
    )
}
