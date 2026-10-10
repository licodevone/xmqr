use std::{error::Error, path::Path};

use mqtt_broker::persistence::backup;

pub fn backup(state_dir: &Path, destination: &Path) -> Result<(), Box<dyn Error>> {
    let sequence = backup::create(state_dir, destination)?;
    println!("Backup criado; sequência {sequence}");
    Ok(())
}

pub fn verify(path: &Path) -> Result<(), Box<dyn Error>> {
    let sequence = backup::verify(path)?;
    println!("Backup íntegro; sequência {sequence}");
    Ok(())
}

pub fn restore(backup_path: &Path, state_dir: &Path) -> Result<(), Box<dyn Error>> {
    let sequence = backup::restore(backup_path, state_dir)?;
    println!("Estado restaurado em diretório novo; sequência {sequence}");
    Ok(())
}
