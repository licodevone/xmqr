use crate::model::{Action, Component, Entry, Kind, Snapshot, State, service_state, valid_id};
use fs2::FileExt;
use serde::Deserialize;
use std::{
    env,
    fs::{self, File, OpenOptions},
    io::{self, Read},
    os::windows::process::CommandExt,
    path::{Path, PathBuf},
    process::{Command, Stdio},
    sync::mpsc,
    thread,
    time::{Duration, Instant},
};
use winreg::{
    RegKey,
    enums::{HKEY_LOCAL_MACHINE, KEY_READ, KEY_WOW64_64KEY},
};

const INVENTORY: &str = r"SOFTWARE\XMQR\Components";
const MAX_COMPONENTS: usize = 64;
const MAX_OUTPUT: usize = 65536;
const CREATE_NO_WINDOW: u32 = 0x0800_0000;

pub fn entry() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = env::args().skip(1).collect();
    match args.as_slice() {
        [] => {
            let Some(lock) = singleton()? else {
                return Ok(());
            };
            crate::ui::run(lock)
        }
        [flag] if flag == "--diagnose" => {
            let snapshot = snapshot();
            let items: Vec<_> = snapshot
                .entries
                .iter()
                .map(|entry| {
                    serde_json::json!({
                        "id":entry.component.id, "name":entry.component.display_name,
                        "service":entry.component.service_name, "state":entry.state.label(),
                        "detail":entry.detail
                    })
                })
                .collect();
            println!(
                "{}",
                serde_json::json!({"components":items,"error":snapshot.error})
            );
            Ok(())
        }
        [flag, action, id] if flag == "--control" => {
            let action = Action::parse(action).ok_or("invalid action")?;
            if !valid_id(id) {
                return Err("invalid component".into());
            }
            control(id, action, false).map_err(Into::into)
        }
        [flag, action] if flag == "--control-all" => {
            let action = Action::parse(action).ok_or("invalid action")?;
            control_all(action, false).map_err(Into::into)
        }
        [flag, target, id] if flag == "--open" => {
            let target = Shortcut::parse(target).ok_or("invalid shortcut")?;
            if !valid_id(id) {
                return Err("invalid component".into());
            }
            open_shortcut(id, target, false, true).map_err(Into::into)
        }
        [flag] if flag == "--version" => {
            println!("xmqr-manager {}", env!("CARGO_PKG_VERSION"));
            Ok(())
        }
        [flag] if flag == "--help" => {
            println!(
                "XMQR Manager\nSem argumentos: bandeja\n--diagnose: inventário e status JSON\n--version\n--control start|stop|restart COMPONENTE: helper local\n--control-all start|stop|restart: conjunto de serviços instalados\n--open config|config-dir|certificates|logs COMPONENTE: helper administrativo"
            );
            Ok(())
        }
        _ => Err("invalid arguments; use --help".into()),
    }
}

fn singleton() -> io::Result<Option<File>> {
    let dir = PathBuf::from(
        env::var_os("LOCALAPPDATA").ok_or_else(|| io::Error::other("LOCALAPPDATA unavailable"))?,
    )
    .join("XMQR");
    fs::create_dir_all(&dir)?;
    let file = OpenOptions::new()
        .read(true)
        .write(true)
        .create(true)
        .truncate(false)
        .open(dir.join("manager.lock"))?;
    match file.try_lock_exclusive() {
        Ok(()) => Ok(Some(file)),
        Err(error) if error.kind() == io::ErrorKind::WouldBlock => Ok(None),
        Err(error) => Err(error),
    }
}

fn optional(key: &RegKey, name: &str) -> io::Result<Option<String>> {
    match key.get_value::<String, _>(name) {
        Ok(value) if value.is_empty() => Ok(None),
        Ok(value) => Ok(Some(value)),
        Err(error) if error.kind() == io::ErrorKind::NotFound => Ok(None),
        Err(error) => Err(error),
    }
}

fn read_component(key: &RegKey, id: String) -> io::Result<Component> {
    let kind: String = key.get_value("Kind")?;
    let result = Component {
        id,
        kind: Kind::parse(&kind).ok_or_else(|| io::Error::other("invalid kind"))?,
        display_name: key.get_value("DisplayName")?,
        executable: key.get_value("Executable")?,
        service_name: optional(key, "ServiceName")?,
        config_file: optional(key, "ConfigFile")?,
        certificates_dir: optional(key, "CertificatesDir")?,
        logs_dir: optional(key, "LogsDir")?,
        panel_url: optional(key, "PanelUrl")?,
    };
    if !result.valid() {
        return Err(io::Error::other("invalid component metadata"));
    }
    Ok(result)
}

fn inventory() -> Snapshot {
    let mut snapshot = Snapshot::default();
    let key = match RegKey::predef(HKEY_LOCAL_MACHINE)
        .open_subkey_with_flags(INVENTORY, KEY_READ | KEY_WOW64_64KEY)
    {
        Ok(key) => key,
        Err(error) if error.kind() == io::ErrorKind::NotFound => return snapshot,
        Err(_) => {
            snapshot.error = Some("Não foi possível consultar as instalações XMQR".into());
            return snapshot;
        }
    };
    for (index, result) in key.enum_keys().enumerate() {
        if index >= MAX_COMPONENTS {
            snapshot.error = Some("Limite de 64 componentes excedido".into());
            break;
        }
        let component = result.and_then(|id| {
            key.open_subkey(&id)
                .and_then(|child| read_component(&child, id))
        });
        match component {
            Ok(component) => {
                let state = if component.service_name.is_some() {
                    State::Unknown
                } else {
                    State::CliOnly
                };
                match fs::metadata(&component.executable) {
                    Ok(metadata) if metadata.is_file() => snapshot.entries.push(Entry {
                        component,
                        state,
                        detail: None,
                    }),
                    Ok(_) => {
                        snapshot.error = Some("Instalação XMQR possui executável inválido".into());
                    }
                    Err(error) if error.kind() == io::ErrorKind::NotFound => {}
                    Err(_) => snapshot.entries.push(Entry {
                        component,
                        state: State::Unknown,
                        detail: Some("Acesso ao executável indisponível".into()),
                    }),
                }
            }
            Err(_) => {
                snapshot.error = Some("Registro de instalação XMQR inválido ou sem acesso".into())
            }
        }
    }
    snapshot
        .entries
        .sort_by(|a, b| a.component.id.cmp(&b.component.id));
    snapshot
}

#[derive(Deserialize)]
#[serde(rename_all = "PascalCase")]
struct ServiceRecord {
    name: String,
    state: String,
    exit_code: u32,
    matches: bool,
    error: Option<String>,
}

pub fn snapshot() -> Snapshot {
    let mut snapshot = inventory();
    let names: Vec<_> = snapshot
        .entries
        .iter()
        .filter_map(|e| {
            e.component.service_name.as_ref().map(|name| {
                serde_json::json!({
                    "Name":name,"Executable":e.component.executable
                })
            })
        })
        .collect();
    if names.is_empty() {
        return snapshot;
    }
    let names = serde_json::to_string(&names).expect("service names serialize");
    let records = powershell(
        include_str!("query-services.ps1"),
        &[("XMQR_SERVICE_NAMES", &names)],
        Duration::from_secs(12),
    )
    .and_then(|output| {
        if output.code != 0 {
            return Err(io::Error::other("SCM query failed"));
        }
        serde_json::from_slice::<Vec<ServiceRecord>>(&output.stdout).map_err(io::Error::other)
    });
    for entry in &mut snapshot.entries {
        let Some(name) = &entry.component.service_name else {
            continue;
        };
        if entry.detail.is_some() {
            continue;
        }
        let record = records
            .as_ref()
            .ok()
            .and_then(|records| records.iter().find(|r| &r.name == name));
        match record {
            Some(record) if record.error.is_none() => {
                if !record.matches {
                    entry.state = State::Unknown;
                    entry.detail =
                        Some("Serviço ausente ou executável diferente da instalação".into());
                    continue;
                }
                entry.state = service_state(&record.state, record.exit_code);
                if entry.state == State::NeverStarted {
                    entry.detail = Some(
                        "Nenhuma tentativa de início desde o último boot (1077); configure os arquivos privados antes de iniciar."
                            .into(),
                    );
                }
                if record.state == "Missing" {
                    entry.detail = Some("Serviço registrado no produto não foi encontrado".into());
                }
                if entry.state == State::Failed {
                    entry.detail =
                        Some(format!("Código de saída do serviço: {}", record.exit_code));
                }
            }
            _ => {
                entry.state = State::Unknown;
                entry.detail =
                    Some("Consulta indisponível; não significa que o serviço está parado".into());
            }
        }
    }
    snapshot
}

struct Output {
    code: i32,
    stdout: Vec<u8>,
}

fn windows_program(relative: &str) -> io::Result<PathBuf> {
    // Do not trust inherited SystemRoot in a process launched with UAC.
    let windows = RegKey::predef(HKEY_LOCAL_MACHINE).open_subkey_with_flags(
        r"SOFTWARE\Microsoft\Windows NT\CurrentVersion",
        KEY_READ | KEY_WOW64_64KEY,
    )?;
    let root: String = windows.get_value("SystemRoot")?;
    if !crate::model::local_absolute_path(&root) {
        return Err(io::Error::other("Windows installation path unavailable"));
    }
    let path = PathBuf::from(root).join(relative);
    if !path.is_absolute() || !path.is_file() {
        return Err(io::Error::other("Windows tool unavailable"));
    }
    Ok(path)
}

fn powershell(script: &str, values: &[(&str, &str)], budget: Duration) -> io::Result<Output> {
    let mut command = Command::new(windows_program(
        r"System32\WindowsPowerShell\v1.0\powershell.exe",
    )?);
    let system_modules = windows_program(r"System32\WindowsPowerShell\v1.0\powershell.exe")?
        .parent()
        .expect("system executable has parent")
        .join("Modules");
    command.env("PSModulePath", system_modules);
    command
        .args([
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            script,
        ])
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .creation_flags(CREATE_NO_WINDOW);
    for (name, value) in values {
        command.env(name, value);
    }
    let mut child = command.spawn()?;
    let output = child
        .stdout
        .take()
        .ok_or_else(|| io::Error::other("missing pipe"))?;
    let (sender, receiver) = mpsc::sync_channel(1);
    thread::spawn(move || {
        let mut bytes = Vec::new();
        let result = output.take((MAX_OUTPUT + 1) as u64).read_to_end(&mut bytes);
        let _ = sender.send(result.map(|_| bytes));
    });
    let deadline = Instant::now() + budget;
    let exit = loop {
        if let Some(exit) = child.try_wait()? {
            break exit;
        }
        if Instant::now() >= deadline {
            let _ = child.kill();
            let _ = child.wait();
            return Err(io::Error::new(
                io::ErrorKind::TimedOut,
                "Operação excedeu o prazo; confira o estado antes de repetir",
            ));
        }
        thread::sleep(Duration::from_millis(50));
    };
    let stdout = receiver
        .recv_timeout(Duration::from_secs(1))
        .map_err(|_| io::Error::other("output unavailable"))??;
    if stdout.len() > MAX_OUTPUT {
        return Err(io::Error::other("output exceeds limit"));
    }
    Ok(Output {
        code: exit.code().unwrap_or(1),
        stdout,
    })
}

pub fn control(id: &str, action: Action, allow_elevation: bool) -> io::Result<()> {
    if !valid_id(id) {
        return Err(io::Error::other("Componente inválido"));
    }
    let snapshot = inventory();
    if snapshot.error.is_some() {
        return Err(io::Error::other(
            "Inventário indisponível; nenhuma ação executada",
        ));
    }
    let entry = snapshot
        .entries
        .iter()
        .find(|e| e.component.id == id)
        .ok_or_else(|| io::Error::other("Componente não está mais instalado"))?;
    if entry.detail.is_some() {
        return Err(io::Error::other("Instalação indisponível"));
    }
    let name = entry
        .component
        .service_name
        .as_deref()
        .ok_or_else(|| io::Error::other("Componente sem serviço"))?;
    let output = powershell(
        include_str!("control-service.ps1"),
        &[
            ("XMQR_SERVICE_NAME", name),
            ("XMQR_SERVICE_ACTION", action.name()),
            ("XMQR_SERVICE_EXECUTABLE", &entry.component.executable),
        ],
        Duration::from_secs(35),
    )?;
    if output.code == 5 && allow_elevation {
        let helper = env::current_exe()?;
        let helper = helper
            .to_str()
            .ok_or_else(|| io::Error::other("Caminho do gerenciador inválido"))?;
        let elevated = powershell(
            include_str!("elevate-control.ps1"),
            &[
                ("XMQR_CONTROL_HELPER", helper),
                ("XMQR_CONTROL_ACTION", action.name()),
                ("XMQR_CONTROL_ID", id),
            ],
            Duration::from_secs(55),
        )?;
        return action_result(elevated.code);
    }
    action_result(output.code)
}

fn action_result(code: i32) -> io::Result<()> {
    if code == 0 {
        return Ok(());
    }
    let kind = if code == 5 {
        io::ErrorKind::PermissionDenied
    } else {
        io::ErrorKind::Other
    };
    Err(io::Error::new(
        kind,
        match code {
            3 => "Serviço ausente ou executável diferente da instalação",
            5 => "Acesso negado ao controle do serviço",
            6 => "Existem serviços dependentes em execução; parada recusada",
            7 => "Serviço em transição; aguarde e tente novamente",
            124 => "Prazo excedido; confira o estado antes de repetir",
            1223 => "Elevação cancelada ou indisponível",
            _ => "Operação não concluída; consulte o estado e os logs",
        },
    ))
}

pub fn control_all(action: Action, allow_elevation: bool) -> io::Result<()> {
    let snapshot = snapshot();
    let plan = crate::model::control_plan(&snapshot, action).map_err(io::Error::other)?;
    let result = execute_plan(&plan, |id, step| control(id, step, false));
    if let Err(error) = &result
        && error.kind() == io::ErrorKind::PermissionDenied
        && allow_elevation
    {
        let helper = env::current_exe()?;
        let helper = helper
            .to_str()
            .ok_or_else(|| io::Error::other("Caminho inválido"))?;
        let output = powershell(
            include_str!("elevate-control-all.ps1"),
            &[
                ("XMQR_CONTROL_HELPER", helper),
                ("XMQR_CONTROL_ACTION", action.name()),
            ],
            Duration::from_secs(4550),
        )?;
        return action_result(output.code).map_err(|error| io::Error::new(error.kind(),
                    format!("Operação geral não concluída: {error}. Reconsulte os estados; pode haver ações já concluídas.")));
    }
    result
}

fn execute_plan(
    plan: &[(String, Action)],
    mut execute: impl FnMut(&str, Action) -> io::Result<()>,
) -> io::Result<()> {
    for (index, (id, step)) in plan.iter().enumerate() {
        execute(id, *step).map_err(|error| io::Error::new(error.kind(), format!(
            "Operação geral interrompida em {id}: {error}. {index} etapa(s) concluída(s); confira os estados.")))?;
    }
    Ok(())
}

#[derive(Clone, Copy, Debug)]
pub enum Shortcut {
    Config,
    ConfigDir,
    Certificates,
    Logs,
    Panel,
}

impl Shortcut {
    fn parse(value: &str) -> Option<Self> {
        match value {
            "config" => Some(Self::Config),
            "config-dir" => Some(Self::ConfigDir),
            "certificates" => Some(Self::Certificates),
            "logs" => Some(Self::Logs),
            _ => None,
        }
    }

    fn name(self) -> &'static str {
        match self {
            Self::Config => "config",
            Self::ConfigDir => "config-dir",
            Self::Certificates => "certificates",
            Self::Logs => "logs",
            Self::Panel => "panel",
        }
    }
}

fn target_access(path: &Path, file: bool) -> io::Result<()> {
    let metadata = fs::metadata(path)?;
    if file {
        if !metadata.is_file() {
            return Err(io::Error::other("Configuração não é um arquivo"));
        }
        // Test editing access without reading or writing configuration bytes.
        OpenOptions::new().read(true).write(true).open(path)?;
    } else {
        if !metadata.is_dir() {
            return Err(io::Error::other("Caminho não é uma pasta"));
        }
        if let Some(entry) = fs::read_dir(path)?.next() {
            entry?;
        }
    }
    Ok(())
}

fn shortcut_error(error: io::Error) -> io::Error {
    let message = match error.kind() {
        io::ErrorKind::PermissionDenied => {
            "Acesso negado ao destino; autenticação administrativa necessária".into()
        }
        io::ErrorKind::NotFound => "Arquivo ou pasta não encontrado; confira a instalação".into(),
        _ => format!("Não foi possível abrir o destino: {error}"),
    };
    io::Error::new(error.kind(), message)
}

pub fn shortcut(id: &str, shortcut: Shortcut) -> io::Result<()> {
    open_shortcut(id, shortcut, true, false)
}

fn open_shortcut(
    id: &str,
    shortcut: Shortcut,
    allow_elevation: bool,
    administrative_browser: bool,
) -> io::Result<()> {
    if !valid_id(id) {
        return Err(io::Error::other("Componente inválido"));
    }
    let snapshot = inventory();
    if snapshot.error.is_some() {
        return Err(io::Error::other(
            "Inventário indisponível; nenhuma ação executada",
        ));
    }
    let entry = snapshot
        .entries
        .iter()
        .find(|e| e.component.id == id)
        .ok_or_else(|| io::Error::other("Componente não está mais instalado"))?;
    let c = &entry.component;
    if matches!(shortcut, Shortcut::Panel) {
        let url = c
            .panel_url
            .as_deref()
            .ok_or_else(|| io::Error::other("Painel não configurado"))?;
        let output = powershell(
            "try { Start-Process -FilePath $env:XMQR_OPEN_URL -ErrorAction Stop; exit 0 } catch { exit 1 }",
            &[("XMQR_OPEN_URL", url)],
            Duration::from_secs(10),
        )?;
        return action_result(output.code);
    }
    let path = match shortcut {
        Shortcut::Config => c.config_file.as_deref().map(Path::new),
        Shortcut::ConfigDir => c.config_file.as_deref().and_then(|p| Path::new(p).parent()),
        Shortcut::Certificates => c.certificates_dir.as_deref().map(Path::new),
        Shortcut::Logs => c.logs_dir.as_deref().map(Path::new),
        Shortcut::Panel => unreachable!(),
    }
    .ok_or_else(|| io::Error::other("Caminho não configurado"))?;
    let file = matches!(shortcut, Shortcut::Config);
    if let Err(error) = target_access(path, file) {
        if error.kind() == io::ErrorKind::PermissionDenied && allow_elevation {
            let helper = env::current_exe()?;
            let helper = helper
                .to_str()
                .ok_or_else(|| io::Error::other("Caminho inválido"))?;
            let elevated = powershell(
                include_str!("elevate-open.ps1"),
                &[
                    ("XMQR_OPEN_HELPER", helper),
                    ("XMQR_OPEN_TARGET", shortcut.name()),
                    ("XMQR_OPEN_ID", id),
                ],
                Duration::from_secs(55),
            )?;
            return match elevated.code {
                0 => Ok(()),
                1223 => Err(io::Error::other(
                    "Autenticação administrativa cancelada ou indisponível",
                )),
                124 => Err(io::Error::other(
                    "Autenticação excedeu o prazo; confira as janelas antes de repetir",
                )),
                _ => Err(io::Error::other(
                    "Não foi possível abrir o destino como administrador; confira a instalação",
                )),
            };
        }
        return Err(shortcut_error(error));
    }
    if file {
        Command::new(windows_program(r"System32\notepad.exe")?)
            .arg(path)
            .spawn()?;
    } else if administrative_browser {
        // Explorer normally delegates to the unelevated desktop process. A
        // separate read-only browser retains this helper's administrative token.
        spawn_script(
            include_str!("browse-folder.ps1"),
            &[("XMQR_BROWSE_ROOT", path.as_os_str())],
        )?;
    } else {
        Command::new(windows_program("explorer.exe")?)
            .arg(path)
            .spawn()?;
    }
    Ok(())
}

fn spawn_script(script: &str, values: &[(&str, &std::ffi::OsStr)]) -> io::Result<()> {
    let mut command = Command::new(windows_program(
        r"System32\WindowsPowerShell\v1.0\powershell.exe",
    )?);
    command
        .args([
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-STA",
            "-Command",
            script,
        ])
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .creation_flags(CREATE_NO_WINDOW);
    // Restrict module lookup in GUI helpers as in the synchronous runner.
    let modules = windows_program(r"System32\WindowsPowerShell\v1.0\powershell.exe")?
        .parent()
        .expect("system executable has parent")
        .join("Modules");
    command.env("PSModulePath", modules);
    for (name, value) in values {
        command.env(name, value);
    }
    command.spawn()?;
    Ok(())
}

pub fn notify_error(message: &str) {
    let _ = spawn_script(
        include_str!("notify-error.ps1"),
        &[("XMQR_ERROR_MESSAGE", message.as_ref())],
    );
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn shortcut_helper_rejects_urls_and_shell_fragments() {
        for value in [
            "panel",
            "config;Stop-Service Spooler",
            "../config",
            "",
            "logs\n",
        ] {
            assert!(Shortcut::parse(value).is_none());
        }
        for value in ["config", "config-dir", "certificates", "logs"] {
            assert_eq!(Shortcut::parse(value).unwrap().name(), value);
        }
        for shortcut in [Shortcut::Config, Shortcut::ConfigDir] {
            assert!(open_shortcut("bad;id", shortcut, false, true).is_err());
        }
    }

    #[test]
    fn shortcut_access_distinguishes_missing_wrong_type_and_accessible_destinations() {
        let unique = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let directory =
            env::temp_dir().join(format!("xmqr-shortcut-{}-{unique}", std::process::id()));
        fs::create_dir(&directory).unwrap();
        let file = directory.join("fixture.toml");
        fs::write(&file, b"fixture only").unwrap();
        assert!(target_access(&file, true).is_ok());
        assert!(target_access(&directory, false).is_ok());
        assert!(target_access(&file, false).is_err());
        assert!(target_access(&directory, true).is_err());
        let original_permissions = fs::metadata(&file).unwrap().permissions();
        let mut readonly_permissions = original_permissions.clone();
        readonly_permissions.set_readonly(true);
        fs::set_permissions(&file, readonly_permissions).unwrap();
        let denied = target_access(&file, true).unwrap_err();
        fs::set_permissions(&file, original_permissions).unwrap();
        assert_eq!(denied.kind(), io::ErrorKind::PermissionDenied);
        assert_eq!(
            target_access(&directory.join("missing"), true)
                .unwrap_err()
                .kind(),
            io::ErrorKind::NotFound
        );
        for kind in [io::ErrorKind::NotFound, io::ErrorKind::PermissionDenied] {
            assert_eq!(shortcut_error(io::Error::from(kind)).kind(), kind);
        }
        fs::remove_file(file).unwrap();
        fs::remove_dir(directory).unwrap();
    }

    #[test]
    fn elevation_script_rejects_untrusted_arguments_without_prompting() {
        for (id, target) in [
            ("broker;Start-Process calc", "config"),
            ("broker", "panel"),
            ("broker", "logs;throw"),
        ] {
            let output = powershell(
                include_str!("elevate-open.ps1"),
                &[("XMQR_OPEN_ID", id), ("XMQR_OPEN_TARGET", target)],
                Duration::from_secs(10),
            )
            .unwrap();
            assert_eq!(output.code, 2);
        }
    }

    #[test]
    fn batch_executor_stops_at_first_failure_and_preserves_denial_for_single_uac() {
        let plan = vec![
            ("client".into(), Action::Stop),
            ("admin".into(), Action::Stop),
            ("broker".into(), Action::Stop),
            ("broker".into(), Action::Start),
        ];
        let mut executed = Vec::new();
        let error = execute_plan(&plan, |id, step| {
            executed.push((id.to_owned(), step));
            if id == "broker" {
                Err(io::Error::from(io::ErrorKind::PermissionDenied))
            } else {
                Ok(())
            }
        })
        .unwrap_err();
        assert_eq!(executed, plan[..3]);
        assert_eq!(error.kind(), io::ErrorKind::PermissionDenied);
        assert!(error.to_string().contains("2 etapa(s) concluída(s)"));
    }

    #[test]
    fn bulk_elevation_rejects_other_actions_without_prompting() {
        let output = powershell(
            include_str!("elevate-control-all.ps1"),
            &[("XMQR_CONTROL_ACTION", "stop;shutdown")],
            Duration::from_secs(10),
        )
        .unwrap();
        assert_eq!(output.code, 2);
    }

    #[test]
    fn powershell_data_is_not_executed_and_unicode_survives() {
        let text = "D:\\Configuração com espaços\\a'; throw 'injected'; $()";
        let result = powershell(
            "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new(); ConvertTo-Json -InputObject $env:XMQR_TEST_VALUE -Compress",
            &[("XMQR_TEST_VALUE", text)],
            Duration::from_secs(10),
        ).unwrap();
        assert_eq!(result.code, 0);
        assert_eq!(
            serde_json::from_slice::<String>(&result.stdout).unwrap(),
            text
        );
    }

    #[test]
    fn powershell_execution_has_a_deadline() {
        let start = Instant::now();
        let result = powershell("Start-Sleep -Seconds 20", &[], Duration::from_millis(250));
        assert_eq!(result.err().unwrap().kind(), io::ErrorKind::TimedOut);
        assert!(start.elapsed() < Duration::from_secs(5));
    }

    #[test]
    fn empty_service_query_returns_array_without_mutation() {
        let result = powershell(
            include_str!("query-services.ps1"),
            &[("XMQR_SERVICE_NAMES", "[]")],
            Duration::from_secs(10),
        )
        .unwrap();
        assert_eq!(result.code, 0);
        let records: Vec<ServiceRecord> = serde_json::from_slice(&result.stdout).unwrap();
        assert!(records.is_empty());
    }
}
