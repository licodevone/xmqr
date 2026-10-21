use crate::model::{Action, Component, Entry, Kind, Snapshot, State, valid_id};
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
        [flag] if flag == "--version" => {
            println!("xmqr-manager {}", env!("CARGO_PKG_VERSION"));
            Ok(())
        }
        [flag] if flag == "--help" => {
            println!(
                "XMQR Manager\nSem argumentos: bandeja\n--diagnose: inventário e status JSON\n--version\n--control start|stop|restart COMPONENTE: helper local"
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
                entry.state = match record.state.as_str() {
                    "Running" => State::Running,
                    "Stopped" if record.exit_code == 0 => State::Stopped,
                    "Stopped" => State::Failed,
                    "Start Pending" | "Stop Pending" | "Continue Pending" | "Pause Pending" => {
                        State::Pending
                    }
                    _ => State::Unknown,
                };
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
    Err(io::Error::other(match code {
        3 => "Serviço ausente ou executável diferente da instalação",
        5 => "Acesso negado ao controle do serviço",
        6 => "Existem serviços dependentes em execução; parada recusada",
        7 => "Serviço em transição; aguarde e tente novamente",
        124 => "Prazo excedido; confira o estado antes de repetir",
        1223 => "Elevação cancelada ou indisponível",
        _ => "Operação não concluída; consulte o estado e os logs",
    }))
}

#[derive(Clone, Copy, Debug)]
pub enum Shortcut {
    Config,
    ConfigDir,
    Certificates,
    Logs,
    Panel,
}

pub fn shortcut(id: &str, shortcut: Shortcut) -> io::Result<()> {
    let snapshot = inventory();
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
    let metadata =
        fs::metadata(path).map_err(|_| io::Error::other("Caminho ausente ou acesso negado"))?;
    if matches!(shortcut, Shortcut::Config) {
        if !metadata.is_file() {
            return Err(io::Error::other("Configuração não é um arquivo"));
        }
        Command::new(windows_program(r"System32\notepad.exe")?)
            .arg(path)
            .spawn()?;
    } else {
        if !metadata.is_dir() {
            return Err(io::Error::other("Caminho não é uma pasta"));
        }
        Command::new(windows_program("explorer.exe")?)
            .arg(path)
            .spawn()?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

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
