#![cfg_attr(windows, windows_subsystem = "windows")]
mod model;
#[cfg(windows)]
mod platform;
#[cfg(windows)]
mod ui;

fn main() {
    #[cfg(windows)]
    if let Err(error) = platform::entry() {
        eprintln!("XMQR: {error}");
        std::process::exit(1);
    }
    #[cfg(not(windows))]
    {
        eprintln!("O gerenciador XMQR requer Windows.");
        std::process::exit(1);
    }
}
