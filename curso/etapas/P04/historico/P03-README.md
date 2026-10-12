# Projeto inicial — Windows e Rust

Curso: Da lógica ao Broker e Clientes MQTT utilizando Rust.

O P00 define o contexto. O P03 descreve a criação da base Rust e esta é uma
**nova implementação didática do seu primeiro recorte**, não a recuperação
de um snapshot antigo. Os dois programas já compilam e executam. Nesta etapa
imprimem identificação e terminam; a comunicação MQTT será acrescentada depois.

## Abrir e executar no Windows

Extraia o ZIP numa pasta, por exemplo `D:\cursos\mqtt-inicial`. Abra PowerShell.
Entre na pasta extraída que contém `broker`, `client` e este README. Se estiver
usando a fonte versionada, a pasta é:

```powershell
Set-Location 'D:\projects\my-project\rapidez-projects\rapidez-broker-client\xmqr\curso\projeto-inicial'
cargo --version
rustc --version
cargo run --locked --offline --manifest-path .\broker\Cargo.toml
cargo run --locked --offline --manifest-path .\client\Cargo.toml
```

Saída própria do primeiro programa:

```text
Broker MQTT: projeto inicial em Rust.
```

Saída própria do segundo programa:

```text
Client MQTT: projeto inicial em Rust.
```

Cargo também mostra mensagens de compilação/execução. Os programas encerram
com código0: isso é esperado. Não ficam aguardando conexão neste recorte.
Não é necessário abrir porta no firewall ou iniciar systemd/WSL/Docker.

## Digitar desde o início

Para criar suas próprias cópias de prática, use uma pasta nova. Os comandos
abaixo criam os pacotes; não os execute sobre as pastas do ZIP já prontas.

```powershell
New-Item -ItemType Directory -Path 'D:\cursos\minha-base-mqtt'
Set-Location 'D:\cursos\minha-base-mqtt'
cargo new --bin --edition 2024 --vcs none broker-inicial
cargo new --bin --edition 2024 --vcs none client-inicial
```

Abra `broker-inicial\src\main.rs`, escreva o código abaixo, salve e execute
`cargo run --manifest-path .\broker-inicial\Cargo.toml`. Faça o mesmo no client,
trocando apenas Broker por Client na mensagem. Cargo gera seu lockfile.

```rust
// Comandos gerados por P03: base inicial da série didática.
fn main() {
    println!("Broker MQTT: projeto inicial em Rust.");
}
```

## Cada linha e cada símbolo

| Trecho | Explicação |
| --- | --- |
| `// Comandos gerados...` | Comentário de origem da etapa. `//` faz o compilador ignorar o restante dessa linha. Não é uma instrução de rede. |
| `fn` | Palavra reservada que declara uma função, um bloco de instruções executável. |
| espaço entre `fn` e `main` | Separa duas palavras para o compilador reconhecer os tokens. |
| `main` | Nome da função de entrada deste executável. A execução começa aqui. |
| `()` | Lista vazia de parâmetros na assinatura da função. |
| `{` | Abre o corpo da função. |
| quatro espaços na linha seguinte | Indentação que facilita a leitura; não substitui as chaves. |
| `println` | Nome da macro de impressão com uma nova linha ao final. |
| `!` depois de `println` | Identifica a chamada de macro nesta sintaxe. |
| `(` depois de `println!` | Abre a lista de argumentos dessa macro. |
| `"..."` | Aspas delimitam um texto literal; o conteúdo é dado, não código. As aspas não aparecem na saída. |
| `Broker MQTT: projeto inicial em Rust.` | Texto exibido. Sua mensagem pode mudar sem alterar o papel da função. |
| `)` depois do literal | Fecha os argumentos da macro. |
| `;` | Termina a instrução de impressão. |
| `}` | Fecha a função. Quando ela termina, esse programa encerra normalmente. |

## Cada arquivo

| Arquivo | Função |
| --- | --- |
| `prompts/00-contexto.md` | Define o objetivo e o ambiente antes da criação. Não recebe dados do usuário. |
| `prompts/03-criar-base.md` | Pedido executado para gerar esta primeira base didática. |
| `broker/Cargo.toml` | Manifest do pacote broker-inicial: metadados e dependências. |
| `broker/src/main.rs` | Código da entrada do broker inicial. |
| `client/Cargo.toml` | Manifest do pacote client-inicial, independente do broker. |
| `client/src/main.rs` | Código da entrada do client inicial. |
| `Cargo.lock` de cada pacote | Resolução gerada pelo Cargo; como não há dependências externas, o lock é pequeno. |
| `.gitignore` | Evita incluir os arquivos gerados em target como código-fonte. |
| `target/` após compilar | Executáveis/intermediários locais; não vem no ZIP. |

## Entender Cargo.toml

`[package]` inicia a tabela de metadados. `name` identifica o pacote e, nesta
estrutura simples, o binário. `version = "0.1.0"` é a versão didática do programa,
não MQTT0.1. `edition = "2024"` seleciona regras da linguagem Rust.
`publish = false` desativa publicação no crates.io; não impede compilar ou usar
Git. `license = "MIT"` identifica a licença fornecida em LICENSE.
`[dependencies]` está vazio: `println!` vem da biblioteca padrão. Não vamos
introduzir Tokio ou outra crate antes de explicar a necessidade correspondente.

## Entender os comandos novos

| Comando/parte | O que faz |
| --- | --- |
| `Set-Location` | PowerShell muda a pasta atual; os caminhos seguintes são resolvidos a partir dela. |
| aspas simples no caminho | Preservam o texto do caminho, inclusive espaços, sem expansão de variáveis. |
| `New-Item -ItemType Directory -Path ...` | Cria uma pasta nova no caminho informado. |
| `cargo new` | Cria os arquivos iniciais de um pacote Rust. |
| `--bin` | Escolhe programa executável, com src/main.rs. |
| `--edition 2024` | Seleciona a edição de linguagem indicada. |
| `--vcs none` | Não inicializa um Git separado nesse exercício. |
| `cargo run` | Compila, se necessário, e executa o programa. |
| `--manifest-path` | Indica qual Cargo.toml usar, sem precisar entrar na pasta de cada pacote. |
| `.\broker\Cargo.toml` | Caminho relativo do manifest no Windows; `.` é a pasta atual. |
| `--locked` | Recusa mudanças na resolução de um lockfile já fornecido. |
| `--offline` | Trabalha sem acessar a rede. Este projeto usa somente biblioteca padrão e precisa apenas da toolchain instalada. |
| `cargo build --release ...` | Compila o perfil otimizado; não executa automaticamente o programa. |

## Executar o arquivo .exe

```powershell
cargo build --locked --offline --release --manifest-path .\broker\Cargo.toml
cargo build --locked --offline --release --manifest-path .\client\Cargo.toml
.\broker\target\release\broker-inicial.exe
.\client\target\release\client-inicial.exe
```

Esses caminhos valem sem uma variável CARGO_TARGET_DIR ou configuração que
mude a pasta de build. Cargo informa o caminho do executável em `cargo run`.
No PowerShell, `& 'caminho com espaços\programa.exe'` executa um caminho entre
aspas; `&` é o operador de chamada nessa posição.

## Verificação da etapa

```powershell
cargo fmt --manifest-path .\broker\Cargo.toml -- --check
cargo fmt --manifest-path .\client\Cargo.toml -- --check
cargo clippy --locked --offline --all-targets --manifest-path .\broker\Cargo.toml -- -D warnings
cargo clippy --locked --offline --all-targets --manifest-path .\client\Cargo.toml -- -D warnings
```

`--` separa opções do Cargo e da ferramenta que ele chama. `--check` verifica
formatação sem reescrever; `-D warnings` torna avisos erros no gate do Clippy.
São verificações da base inicial, não testes do protocoloMQTT.

Se Cargo não for encontrado, abra um terminal onde sua instalação Rust esteja
no PATH. Se faltar um linker, a mensagem indica problema da toolchain MSVC;
não altere main.rs para esconder esse erro. Ambiente já verificado nesta
entrega: Windows x86_64, Rust/Cargo1.98.1 MSVC.
