// [P05 - NOVO] io contém erros; Read e Write disponibilizam métodos de I/O.
use std::io::{self, Read, Write};
// [P05 - NOVO] TcpStream representa a conexão ativa com o servidor.
use std::net::TcpStream;

// [P05 - ALTERADO] main retorna sucesso ou erro de rede/entrada/saída.
fn main() -> io::Result<()> {
    // [P03 - MANTIDO] A identificação original do client é preservada.
    println!("Client MQTT: projeto inicial em Rust.");

    // [P05 - NOVO] connect abre TCP; mut permite leitura/escrita; ? propaga falha.
    let mut stream = TcpStream::connect("127.0.0.1:18830")?;
    // [P05 - NOVO] b"ping" é um literal de quatro bytes; write_all envia todos.
    stream.write_all(b"ping")?;
    // [P05 - NOVO] Reserva quatro bytes porque este exercício conhece a resposta.
    let mut response = [0_u8; 4];
    // [P05 - NOVO] read_exact espera quatro bytes ou erro; &mut permite preenchimento.
    stream.read_exact(&mut response)?;
    // [P05 - NOVO] {} formata o texto; from_utf8_lossy converte bytes para exibição.
    println!("Resposta: {}", String::from_utf8_lossy(&response));
    // [P05 - NOVO] Retorna sucesso; o stream é descartado ao sair da função.
    Ok(())
}
