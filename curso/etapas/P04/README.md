# P04 — acrescentar servidor TCP à base P03

Série didática nova. Projeto acumulado: códigoP03 + alteraçõesP04.
O client continua imprimindo identificação; o broker passa a aceitar TCP.
MQTT é o objetivo futuro; esta etapa usa um eco de bytes para aprender rede.

## Arquivos que mudam

`broker/src/main.rs`: imports, retornoResult, listener e leitura/escrita.
`broker/Cargo.toml`: versão didática0.2.0. Cargo atualiza olock correspondente.
`client/` permanece com os mesmos arquivos do P03, sem alterações de código.
`historico/P03-README.md` preserva a explicação anterior, que não descreve o
comportamento atual de rede. Prompts00 e03 permanecem junto do novo04.

## Executar no Windows

Abra PowerShell na pasta extraídaP04, onde estão broker/client.

```powershell
cargo run --locked --offline --manifest-path .\broker\Cargo.toml
```

Saída:

```text
Broker MQTT: projeto inicial em Rust.
TCP de estudo em 127.0.0.1:18830
```

Agora o processo continua esperando conexão, diferente do P03. Não abra essa
porta no firewall:127.0.0.1 só recebe conexões da própria máquina. Ctrl+C encerra
este processo de primeiro plano. Em outra janela, rodar oclientP04 ainda mostra
a mensagemP03 eencerra; a conexão pelo client entra somente emP05.

## Antes de digitar: biblioteca padrão

`std` é a biblioteca padrão doRust, disponível sem adicionar crate no Cargo.toml.
`std::io` contém tipos/contratos para entrada e saída; `std::net` contém rede.
`Read` e`Write` são traits: descrevem comportamentos de tipos que podem ler ou
escrever bytes. Importá-los permite chamar os métodos correspondentes doStream.
`TcpListener` é o tipo do socket que espera novas conexões, não a conexão de
um client específico. Não confunda biblioteca, trait eobjeto de conexão.

## Cada trecho novo

| Código | Explicação detalhada |
| --- | --- |
| `use std::io::{self, Read, Write};` | `use` traz nomes ao módulo; `::` percorre o caminho; chaves agrupam imports; `self` importa o próprio io; Read/Write disponibilizam seus métodos. |
| `use std::net::TcpListener;` | Importa o tipo que abre a escutaTCP. Não abre a porta ao importar. |
| `fn main() -> io::Result<()>` | `->` indica tipo retornado. Result pode ser Ok ouErr; `()` é valor unitário de sucesso, sem outro dado de retorno. |
| `let listener = ...` | Associa o objeto devolvido ao nome listener. |
| `TcpListener::bind("127.0.0.1:18830")` | Chama função associada bind: IPloopback eporta18830 estão na string. Devolve resultado com listener ouerro. |
| `?` | Extrai sucesso ou encerra a função propagando o erro. Nesta função de entrada, erro encerra o processo com falha. |
| `listener.incoming()` | Produz um iterador de tentativas de conexão. Pode esperar pela próxima conexão. |
| `for connection in ...` | Repete para cada item do iterador. Item é Result, não stream automaticamente. |
| `let mut stream = connection?;` | Obtém a conexão oupropaga erro. `mut` permite operações que alteram o estado de leitura/escrita. |
| `[0_u8; 512]` | Array de512 bytes em zero. u8 é inteiro sem sinal de 8 bits. `;` interno separa valor equantidade. |
| `loop` | Repete leitura da mesma conexão atéencontrar condição de saída. |
| `stream.read(&mut buffer)?` | Empresta buffer para alteração eobtém quantos bytes chegaram. Pode receber menos que512; não é necessariamente uma mensagem inteira. |
| `if count == 0` | DetectaEOF, fim do fluxo de envio nesta leitura. |
| `break;` | Sai somente do loop interno; oservidor volta a aceitar o próximo client. |
| `&buffer[..count]` | Empresta uma fatia desde início atécount exclusivo. Só devolve bytes recebidos, sem incluir zeros do restante do array. |
| `stream.write_all(...)` | Tenta escrever todos os bytes da fatia ouretorna erro. Não comprova processamento de negócio pelo destinatário. |
| `Ok(())` | Resultado de sucesso da função, semdado. Esse ponto costuma não ser alcançado enquanto incoming segue esperando conexões. |

## Como acrescentar o código

1. Abra broker/src/main.rs. Mantenha a impressãoP03 dentro de main.
2. Escreva os dois imports acima dafunção eajuste sua assinatura para Result.
3. Depois da impressão, acrescente bind, anúncio efor.
4. Dentro dofor, crie stream ebuffer; depois escreva loop/read/if/write_all.
5. Depois dofor, escrevaOk(()). Salve eexecute ocomando acima.

Se a porta estiver ocupada, bind retornaerro antes deanunciar aescuta. Feche
somente sua instância didática anterior; não pare serviços reais da máquina.
TCP é fluxo: várias escritas podem chegar numa leitura euma escrita pode chegar
fragmentada. O parserMQTT futuro precisará tratar essas duas situações.

Limites desta etapa: um client por vez, operações blo queantes, buffer512,
sem timeout, autenticação ouTLS. Esses acréscimos terão novos prompts eexplicações.
