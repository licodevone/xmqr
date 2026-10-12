// [P04 - NOVO] io representa entrada/saída; Read e Write fornecem seus métodos.
use std::io::{self, Read, Write};
// [P04 - NOVO] TcpListener é o tipo que recebe novas conexões TCP.
use std::net::TcpListener;

// [P04 - ALTERADO] main agora retorna Ok(()) ou um erro de entrada/saída.
fn main() -> io::Result<()> {
    // [P03 - MANTIDO] A identificação inicial continua sendo impressa.
    println!("Broker MQTT: projeto inicial em Rust.");

    // [P04 - NOVO] bind abre a porta só na máquina local; ? propaga erro.
    let listener = TcpListener::bind("127.0.0.1:18830")?;
    // [P04 - NOVO] O endereço só é anunciado depois de bind ter sucesso.
    println!("TCP de estudo em 127.0.0.1:18830");
    // [P04 - NOVO] incoming produz conexões recebidas, atendidas uma por vez.
    for connection in listener.incoming() {
        // [P04 - NOVO] ? obtém o stream; mut permite modificar seu estado.
        let mut stream = connection?;
        // [P04 - NOVO] Array com 512 bytes (u8), inicialmente preenchidos com zero.
        let mut buffer = [0_u8; 512];
        // [P04 - NOVO] Repetir leitura/escrita até o client encerrar o envio.
        loop {
            // [P04 - NOVO] &mut empresta o buffer para receber bytes; count é a quantidade.
            let count = stream.read(&mut buffer)?;
            // [P04 - NOVO] Zero bytes indica fim do fluxo recebido nesta leitura.
            if count == 0 {
                // [P04 - NOVO] Sai deste loop e volta a esperar outro client.
                break;
            }
            // [P04 - NOVO] ..count pega somente os bytes lidos; write_all os devolve.
            stream.write_all(&buffer[..count])?;
        }
    }
    // [P04 - NOVO] Resultado de sucesso sem outro valor, se o laço terminar.
    Ok(())
}
