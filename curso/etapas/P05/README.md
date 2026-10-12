# P05 — acrescentar client TCP ao projeto P04

Projeto acumulado: P03 +P04 +P05. O brokerP04 continua íntegro. Oclient
mantém a impressãoP03 eagora conecta, envia ping e imprime a resposta doeco.
Comentários [Pxx - NOVO/ALTERADO/MANTIDO] indicam de qual etapa veio otrecho.

## Rodar no Windows: duas janelas PowerShell

Na janela1, entre na pasta extraídaP05 eexecute:

```powershell
cargo run --locked --offline --manifest-path .\broker\Cargo.toml
```

Deixe a janela aberta. Na janela2, na mesma pastaP05:

```powershell
cargo run --locked --offline --manifest-path .\client\Cargo.toml
```

Saída própria do client:

```text
Client MQTT: projeto inicial em Rust.
Resposta: ping
```

O client encerra; o broker continua esperando. Pare somente essa instância
didática com Ctrl+C na janela1 ao terminar. Se oclient falhar ao conectar,
confirme primeiro se a janela1 mostrou TCP de estudo em127.0.0.1:18830.
Não altere firewall ou TLS: este endereço é só sua própria máquina etransporteTCP.

## Arquivos novos ealterados

`client/src/main.rs` acrescenta a conexão e I/O. `client/Cargo.toml` altera a
versão para0.2.0 didática eCargo atualiza seulock. `broker/` é idêntico ao P04.
`prompts/05-client-tcp.md` registra esta fatia. README antigos permanecem em
historico/P03-README.md eP04-README.md; eles descrevem suas etapas anteriores.

## Explicação antes de digitar

| Trecho/API nova | O que é ecomo usar |
| --- | --- |
| `std::net::TcpStream` | Tipo da conexão TCP já aceita/conectada, diferente doTcpListener que espera clientes. Não é biblioteca externa. |
| `TcpStream::connect(...)` | Tenta alcançar IP eporta. Devolve Result comstream ouerro. O ? encerra com falha se não conectar. |
| `mut stream` | Binding mutável necessário para métodos que alteram estado de leitura/escrita. |
| `b"ping"` | O prefixo b escolhe literal de bytes. p,i,n,g são quatro bytesASCII neste exemplo, não um pacote MQTT. |
| `write_all` | Envia toda a fatia de bytes ouerro. Ter enviado não comprova sozinho que opeer processou. |
| `[0_u8; 4]` | Array de4bytes em zero para uma resposta de tamanho conhecido neste exercício. |
| `read_exact` | Continua lendo até preencher o array ou recebererro/EOF. Uma chamada read comum poderia receber menos de4bytes. |
| `&mut response` | Empréstimo exclusivo para permitir preenchera memória do array; não cria outro array. |
| `String::from_utf8_lossy(&response)` | Cria representação detexto para exibição. SequênciasUTF-8 inválidas são substituídas; aqui ping éASCII válido. |
| `"Resposta: {}"` | Texto deformatação com marcador que recebe oargumento depois da vírgula. |
| `Ok(())` | Retorna sucesso e permite que main encerre. O stream sai deescopo efecha aconexão. |

## Digitação da evolução

1. Parta deP04. Não apague broker ouclient para recriar outroprojeto.
2. Abra client/src/main.rs eadicione imports acima de main.
3. Altere somente a assinatura para io::Result<()> e mantenha a impressãoP03.
4. Abaixo dela escreva connect, write_all, array4 e read_exact.
5. Escreva aimpressão daresposta eOk(()), salve, compile eexecute nofluxo acima.
6. Confira o diff incluído para ver todos os arquivos comparados comP04.

Fluxo observado: client envia quatro bytes → broker lê edevolve → client
recebe quatro bytes → mostra ping. Este é um testeTCP, sem MQTT/TLS/credenciais.
Passos futuros ensinarão framing, CONNECT/CONNACK etópicos antes de anunciar
compatibilidadeMQTT. Não altere osnapshotsP03/P04 ao avançar: eles continuam
disponíveis para comparar e reproduzir suas aulas.
