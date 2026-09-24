//! Exemplo didático MQTT 3.1.1: CONNECT, PINGREQ e DISCONNECT.
//!
//! Não substitui o listener mTLS de `src/transport`. Ele demonstra isolamento,
//! admission control, deadlines e alocação somente após validar o tamanho.

use std::{io, sync::Arc, time::Duration};

use tokio::{
    io::{AsyncReadExt, AsyncWriteExt},
    net::{TcpListener, TcpStream},
    sync::Semaphore,
    time::timeout,
};

const IO_DEADLINE: Duration = Duration::from_secs(3);
const MAX_PACKET_SIZE: usize = 4 * 1024;
const MAX_CONNECTIONS: usize = 1_000;

#[tokio::main]
async fn main() -> io::Result<()> {
    let listener = TcpListener::bind("192.168.0.100:1883").await?;
    let slots = Arc::new(Semaphore::new(MAX_CONNECTIONS));

    loop {
        let (socket, peer) = listener.accept().await?;
        let Ok(permit) = Arc::clone(&slots).try_acquire_owned() else {
            drop(socket);
            continue;
        };

        // A falha/panic desta tarefa fica contida no JoinHandle e não atravessa
        // o loop de aceitação. O código de produção também registra o JoinError.
        drop(tokio::spawn(async move {
            let _permit = permit;
            if let Err(error) = handle_client(socket).await {
                eprintln!("client {peer} disconnected safely: {error}");
            }
        }));
    }
}

async fn handle_client(mut socket: TcpStream) -> io::Result<()> {
    let connect = read_packet(&mut socket).await?;
    validate_minimal_connect(&connect)?;
    socket.write_all(&[0x20, 0x02, 0x00, 0x00]).await?; // CONNACK accepted

    loop {
        let packet = read_packet(&mut socket).await?;
        match packet.as_slice() {
            [0xC0, 0x00] => {
                socket.write_all(&[0xD0, 0x00]).await?; // PINGRESP
            }
            [0xE0, 0x00] => return Ok(()), // DISCONNECT
            _ => {
                return Err(io::Error::new(
                    io::ErrorKind::InvalidData,
                    "unsupported or malformed MQTT packet",
                ));
            }
        }
    }
}

async fn read_packet(socket: &mut TcpStream) -> io::Result<Vec<u8>> {
    timeout(IO_DEADLINE, read_packet_inner(socket))
        .await
        .map_err(|_| io::Error::new(io::ErrorKind::TimedOut, "packet assembly timeout"))?
}

async fn read_packet_inner(socket: &mut TcpStream) -> io::Result<Vec<u8>> {
    let mut first = [0_u8; 1];
    timed_read_exact(socket, &mut first).await?;

    let mut remaining = 0_usize;
    let mut multiplier = 1_usize;
    let mut encoded_length = Vec::with_capacity(4);
    for index in 0..4 {
        let mut byte = [0_u8; 1];
        timed_read_exact(socket, &mut byte).await?;
        encoded_length.push(byte[0]);
        remaining = remaining
            .checked_add(usize::from(byte[0] & 0x7f) * multiplier)
            .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidData, "length overflow"))?;

        if byte[0] & 0x80 == 0 {
            break;
        }
        if index == 3 {
            return Err(io::Error::new(
                io::ErrorKind::InvalidData,
                "Remaining Length exceeds four bytes",
            ));
        }
        multiplier *= 128;
    }

    let header_len = 1 + encoded_length.len();
    if remaining > MAX_PACKET_SIZE.saturating_sub(header_len) {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            "MQTT packet exceeds the configured limit",
        ));
    }

    let mut packet = Vec::with_capacity(header_len + remaining);
    packet.push(first[0]);
    packet.extend_from_slice(&encoded_length);
    packet.resize(header_len + remaining, 0);
    timed_read_exact(socket, &mut packet[header_len..]).await?;
    Ok(packet)
}

async fn timed_read_exact(socket: &mut TcpStream, buffer: &mut [u8]) -> io::Result<()> {
    timeout(IO_DEADLINE, socket.read_exact(buffer))
        .await
        .map_err(|_| io::Error::new(io::ErrorKind::TimedOut, "client read timeout"))??;
    Ok(())
}

fn validate_minimal_connect(packet: &[u8]) -> io::Result<()> {
    // CONNECT flags must be zero. This compact example accepts only the
    // one-byte Remaining Length form and MQTT 3.1.1 protocol level 4.
    let connect_flags = packet.get(9).copied().unwrap_or(1);
    let will_enabled = connect_flags & 0b0000_0100 != 0;
    let will_qos = (connect_flags >> 3) & 0b11;
    let will_retain = connect_flags & 0b0010_0000 != 0;
    let password_without_username =
        connect_flags & 0b0100_0000 != 0 && connect_flags & 0b1000_0000 == 0;
    let flags_valid = connect_flags & 0x01 == 0
        && will_qos != 3
        && (will_enabled || (will_qos == 0 && !will_retain))
        && !password_without_username;

    let valid = packet.len() >= 12
        && packet[0] == 0x10
        && packet[1] < 128
        && packet[2..8] == [0x00, 0x04, b'M', b'Q', b'T', b'T']
        && packet[8] == 0x04
        && flags_valid;
    if !valid {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            "invalid MQTT 3.1.1 CONNECT",
        ));
    }
    Ok(())
}
