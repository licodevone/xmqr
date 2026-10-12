# Da lógica ao Broker e Clientes MQTT utilizando Rust

## Reconstruir o primeiro commit do XMQR

O destino é o conteúdo do commit `f7efe357cdcd4a05e922a5fb205bd8757cdc5625`:
XMQR 0.3.0, 35 arquivos e 6.083 linhas Rust. Ele já inclui `mqtt-broker`,
`mqtt-client` e `mqtt-admin` no mesmo pacote. O client independente surgiu depois.
O histórico começa com esse conjunto pronto e não registra a sua construção
desde uma pasta vazia. A sequência R01 a R10 abaixo foi preparada agora por P77
para ensinar a reconstrução; ela não afirma recuperar prompts antigos.

Ao finalizar R10, a pasta `codigo/` do pacote tem exatamente os arquivos desse
primeiro commit. Os guias, prompts de aula e relatórios ficam fora de `codigo/`.
Um commit criado por você terá outro identificador, mesmo com arquivos iguais:
nome do autor, data, mensagem e outros metadados participam do identificador Git.

## Como estudar e digitar

1. Abra o guia HTML e a aula correspondente à etapa.
2. Leia objetivo, conceitos novos e bibliotecas antes de digitar.
3. Crie os diretórios indicados e abra cada arquivo no editor. A ordem de
   digitação aparece na aula, com o conteúdo integral e números de linha.
4. Digite apenas o texto da coluna código. Números e explicações não fazem
   parte do programa. Comentários que aparecem no código original podem ser digitados.
5. Quando a aula indicar uma substituição, substitua o arquivo inteiro pelo
   conteúdo novo mostrado. Preserve os demais arquivos: a evolução é cumulativa.
6. Salve todos os arquivos e rode o comando do checkpoint dentro do projeto.
   Leia a primeira mensagem de erro antes das mensagens que são consequência dela.
7. Compare com a pasta `codigo/` do ZIP da etapa. `ALTERACOES.diff` mostra o que
   mudou desde a anterior; `MANIFESTO.json` identifica arquivos novos/mantidos/alterados.

As explicações ao lado das linhas ajudam a ler a sintaxe. O texto específico de
cada módulo explica seu papel no funcionamento. Uma nota de continuação de uma
expressão não constitui, sozinha, análise de todo o efeito daquela função.

## Seção 1 — Preparar o ambiente e começar o pacote

### Aula 1 — Ferramentas e primeiro programa, R01

Abra PowerShell e confira as ferramentas que você já instalou:

```powershell
rustc --version
cargo --version
git --version
```

`rustc` é o compilador que transforma Rust em código executável. `cargo` organiza
o projeto, resolve bibliotecas e chama o compilador. `rustup` administra versões
dessas ferramentas. `git` registra versões dos arquivos. `--version` pede a
versão da ferramenta, sem executar o seu programa MQTT.

O manifesto histórico pede Rust 1.88 ou superior e edição 2024. A verificação
recente usou Windows/Rust 1.98.1 e Ubuntu 26/WSL/Rust 1.99.0; não foi teste do
MSRV exato 1.88. Edição da linguagem e versão do compilador são informações diferentes.

Se a ferramenta faltar, instale seguindo [o manual oficial de Rust](https://doc.rust-lang.org/book/ch01-01-installation.html).
No Windows, o instalador de Rust para MSVC orienta a instalação das ferramentas
C++ do Visual Studio, que fornecem linker e bibliotecas nativas. Neste projeto,
o provedor criptográfico também compila código nativo: leia qualquer diagnóstico
de ferramenta ausente. Não reinstale nem atualize ferramentas que já funcionam.
Para Git ausente, use o instalador indicado em [Git Downloads](https://git-scm.com/downloads).

Passos para uma máquina Windows que ainda não tenha Rust:

1. Abra a página de instalação vinculada acima e baixe `rustup-init.exe` para
   Windows, escolhendo a arquitetura da máquina.
2. Execute o instalador. Se ele oferecer preparar o Visual Studio, siga essa
   opção. Na instalação manual, selecione o conjunto **Desenvolvimento para
   desktop com C++**, que inclui compilador/linker MSVC e Windows SDK.
3. Volte ao instalador Rust e conclua a instalação padrão de Rust estável para MSVC.
4. Feche e abra novamente o PowerShell para carregar os caminhos das ferramentas.
5. Repita `rustc --version` e `cargo --version`; depois confira `cargo fmt --version`
   e `cargo clippy --version`. Se esses componentes faltarem, instale-os com
   `rustup component add rustfmt clippy` e repita a conferência.

A arquitetura x86_64 usa programas de 64 bits. MSVC identifica a família de
ferramentas/linkagem Microsoft, não a versão do seu programa. O detalhe dos
pré-requisitos está no [manual rustup/MSVC](https://rust-lang.github.io/rustup/installation/windows-msvc.html).

No Ubuntu, se estiver preparando uma instalação nova, os pré-requisitos de
compilação nativa podem ser instalados assim, antes do instalador Rust oficial:

```bash
sudo apt update
sudo apt install build-essential cmake pkg-config git
```

`sudo` executa a operação administrativa, `apt update` atualiza a lista de
pacotes disponíveis, `apt install` instala os pacotes nomeados. `build-essential`
fornece compilação/linkagem nativa; CMake organiza builds de dependências nativas;
`pkg-config` consulta informações de bibliotecas de sistema. Esses comandos são
preparação de uma máquina nova, não parte do programa Rust que será digitado.

Se Rust ainda não estiver instalado no Ubuntu, o comando do instalador oficial é:

```bash
curl --proto '=https' --tlsv1.2 https://sh.rustup.rs -sSf | sh
```

`curl` obtém o script por HTTPS; as opções restringem protocolo/TLS e apresentam
falhas; `| sh` envia o script ao interpretador. Isso instala ferramentas, não
compila o XMQR. Conclua a opção padrão do instalador, abra novamente o terminal
e confira rustc/cargo. Se faltar curl numa instalação nova, instale o pacote
`curl` antes. Não execute o instalador quando as ferramentas já funcionam.

Como você já tem Rust, comece em uma pasta nova de estudo, fora do XMQR existente:

```powershell
Set-Location 'D:\projects\my-project\rapidez-projects'
cargo new --bin --name mqtt-broker --edition 2024 --vcs none xmqr-curso-03
Set-Location '.\xmqr-curso-03'
```

`Set-Location` escolhe a pasta do terminal. `cargo new` cria o projeto;
`--bin` cria um programa executável; `--name mqtt-broker` escolhe o nome do
pacote; `--edition 2024` escolhe as regras da linguagem; `--vcs none` deixa a
inicialização Git para a última aula. `xmqr-curso-03` é a pasta nova. Se ela já
existe, escolha outro nome; não substitua uma pasta que contém seu trabalho.

Estrutura inicial:

```text
xmqr-curso-03/
  Cargo.toml
  src/
    main.rs
```

No editor, digite o `main.rs` mostrado em R01. Ele contém uma função `main` e
uma impressão. `fn` declara função; `main` é a entrada do executável; `()` contém
os parâmetros, vazios aqui; `{}` delimita o corpo; `println!` é uma macro que
imprime texto e nova linha; aspas delimitam texto; `;` encerra a instrução.
Quatro espaços organizam a leitura dentro do bloco.

Crie também o arquivo `.gitignore` na raiz e digite o conteúdo mostrado em R01.
Ele será importante para não preparar os arquivos gerados e segredos no commit.
Confira Cargo.toml com o conteúdo de R01; o comando Cargo já gerou sua base.

```powershell
cargo generate-lockfile
cargo build --locked --bins
cargo run --locked --bin mqtt-broker
```

O primeiro comando gera o lock da base simples. `build` gera executáveis;
`--locked` impede mudar as dependências registradas; `--bins` seleciona os
binários. `run --bin mqtt-broker` executa o programa escolhido. Nesta etapa ele
imprime a apresentação e termina: ainda não inicia o broker.

### Aula 2 — Manifesto, bibliotecas e símbolos, R02

Abra `Cargo.toml` e digite o manifesto integral histórico exibido em R02.
Ele muda a versão do pacote para 0.3.0 e declara as bibliotecas. A pasta da aula
ainda não possui todas as funcionalidades dessa versão: o número é o destino
do manifesto, enquanto a etapa R02 identifica o progresso didático.

`[package]` abre a seção de identificação; `name` nomeia o pacote; `version`
é a versão escolhida pelo autor; `edition` escolhe a edição Rust; `rust-version`
declara a versão mínima; `publish = false` impede publicar esse pacote no crates.io;
`default-run` seleciona o executável padrão quando há vários. `[dependencies]`
declara bibliotecas necessárias ao programa; `[dev-dependencies]` contém apoio
a testes/exemplos. Uma biblioteca externa é um conjunto de código reutilizável,
chamado crate, que Cargo obtém e compila junto com o programa.

`tokio = { version = "1.53.1", features = [...] }` usa uma tabela TOML: `version`
indica a faixa de versões compatíveis e `features` seleciona capacidades opcionais.
`default-features = false` desativa o conjunto padrão daquela dependência.
`"0.23.45"` normalmente permite atualizações compatíveis dentro de 0.23;
`"=0.25.1"` exige exatamente essa versão. O `Cargo.lock` fornecido determina
quais versões efetivas foram usadas no snapshot histórico.

**Não digite os milhares de caracteres gerados de `Cargo.lock`.** Copie o arquivo
fornecido em R02 para a raiz do projeto, substituindo o lock simples de R01.
Ele é gerado pelo Cargo e contém versões, relações entre crates e checksums.
Gerar hoje outro lock pode escolher versões diferentes mesmo com o mesmo manifesto.
Não use `cargo update` para reconstruir exatamente este histórico.

Leia a explicação de cada biblioteca no guia antes dos arquivos que a utilizam.
Depois salve e execute:

```powershell
cargo build --locked --bins
```

A primeira compilação com bibliotecas pode demorar. Cargo pode baixar crates
caso o cache não as contenha. `--offline` só deve ser acrescentado se as
dependências do lock já estiverem disponíveis. A biblioteca padrão `std` vem
com Rust e não precisa ser incluída como dependência.

Símbolos que aparecerão nos próximos módulos:

| Símbolo/palavra | Leitura e efeito |
| --- | --- |
| `use a::b` | Traz o nome b do caminho a para este módulo. Não executa a função importada. |
| `pub mod auth;` | Declara o módulo e permite acesso externo; procura auth.rs ou auth/mod.rs. |
| `let`, `mut` | Criam variável; mut permite modificar sua vinculação/valor quando o tipo permite. |
| `&T`, `&mut T` | Emprestam referência compartilhada ou exclusiva a um valor, sem transferir ownership. |
| `String`, `&str` | Texto possuído em memória e fatia de texto emprestada, respectivamente. |
| `Vec<T>`, `&[u8]` | Sequência possuída de elementos e fatia emprestada de bytes. |
| `Option<T>` | Some(valor) ou None: expressa presença/ausência. |
| `Result<T, E>` | Ok(resultado) ou Err(erro): retorno que deve ser tratado. |
| `?` | Propaga o erro ao chamador, se houver; caso contrário extrai o sucesso. |
| `->` | Separa parâmetros do tipo de retorno da função. |
| `match`, `=>` | Selecionam uma alternativa e indicam a expressão executada para o padrão. |
| `async`, `.await` | Definem operação assíncrona e aguardam sua conclusão sem ocupar o worker com espera ativa. |
| `move` | Move valores capturados para a função anônima/tarefa, respeitando seus tipos. |
| `Arc<T>` | Ownership compartilhado com contagem atômica; não torna sozinho todo T seguro para mutação. |
| `#[derive(...)]` | Pede ao compilador/macros implementações de traits como Debug ou Serialize. |
| `#[cfg(...)]` | Compila o item seguinte apenas quando a configuração indicada se aplica. |
| `#[test]`, `assert_eq!` | Identificam teste e verificam igualdade; não são executados por cargo build. |
| `'a`, `'static` | Descrevem validade de referências; não são cronômetros nem tempo de conexão. |
| `0x30`, `0b0010` | Escrevem números em hexadecimal/binário para representar bits de protocolos. |
| `..`, `..=` | Delimitam fatias/faixas com limite superior exclusivo ou inclusivo. |

## Seção 2 — Construir os componentes de infraestrutura

### Aula 3 — Persistência e ator, R03

Crie `src/persistence/mod.rs`, `src/persistence/actor.rs` e `src/lib.rs` na
ordem mostrada no guia. Digite o conteúdo integral. `lib.rs` passa a declarar
`pub mod persistence;`; o nome de crate usado por código Rust é `mqtt_broker`,
com sublinhado, enquanto o nome Cargo/executável mantém `mqtt-broker`.

O módulo de persistência mantém um mapa chave/valor durável. WAL é o registro
sequencial de alterações: recuperação lê registros válidos para reconstituir o
estado. Snapshot guarda uma imagem do mapa e permite reduzir o WAL. Checksum
detecta corrupção; lock de arquivo evita escritores concorrentes sobre o mesmo
estado. A sincronização de arquivo/diretório depende do sistema operacional.

O ator recebe comandos por canal limitado, executa operações de disco numa
thread dedicada e responde pelo canal oneshot. Assim, o chamador assíncrono não
faz uma operação de disco bloqueante dentro de um worker Tokio. `Put`, `Delete`,
`Get`, `Snapshot` e `Shutdown` são alternativas de comando com seus dados/respostas.

Confira especialmente `Store::open`, a gravação/sincronização de registros,
`replay_wal`, `read_snapshot` e o loop da thread do ator. Os testes de crash
usam estado temporário e falhas simuladas; não execute isso sobre dados reais.
Compile com `cargo build --locked --bins` e confira os alvos com
`cargo check --locked --all-targets`. Ainda mantenha o main de apresentação.

### Aula 4 — Autenticação e ACL, R04

Crie `src/auth/mod.rs` e acrescente `pub mod auth;` ao `lib.rs` indicado na
aula. Autenticação responde quem é o cliente; ACL decide se essa identidade
pode publicar ou receber num tópico. Serde/TOML leem os arquivos de configuração;
Argon2 verifica senha; SHA-256 produz fingerprint dos bytes do certificado;
as comparações e limites evitam aceitar entradas fora do contrato.

`AuthPolicy` contém a configuração carregada e `AccessPolicy` escolhe a política
do perfil. `open-lab` é explicitamente anônimo; o modo seguro exige identidade e
permissão. Não copie uma senha pessoal para o código. Os exemplos de configuração
da última etapa são modelos, não credenciais prontas. Repita build e check.

### Aula 5 — Transporte e concorrência, R05

Crie `src/transport/mod.rs` e acrescente `pub mod transport;` ao `lib.rs`.
O transporte aceita conexões TCP, limita vagas, impõe deadlines e oferece
leitura/escrita ao módulo MQTT. `SecureTransport` usa TLS/mTLS e valida o
certificado do cliente; `OpenLabTransport` restringe o laboratório ao loopback.

`Semaphore` representa vagas disponíveis. O permit permanece com a conexão e
sua liberação devolve a vaga. `tokio::spawn` inicia tarefa; `timeout` limita uma
operação. A contenção de panic evita que uma conexão interrompa o laço principal.
`BrokerConnection` oferece uma interface comum ao TCP simples e ao TLS.
Compilar este módulo não exige criar certificados nem abrir uma porta: isso
ocorre somente quando um executável chama as rotinas correspondentes.

## Seção 3 — Construir o núcleo MQTT, R06

### Aula 6 — Ler e produzir pacotes: codec.rs

Crie `src/mqtt/codec.rs`. Um pacote MQTT é uma sequência de bytes com cabeçalho,
tamanho restante e campos específicos. A leitura da rede pode entregar só parte
do pacote ou vários pacotes juntos; `FrameReader` acumula bytes dentro do limite,
valida o cabeçalho e extrai um pacote completo. `decode` interpreta o corpo;
os `encode_*` montam respostas. `Qos` representa as três modalidades de entrega.
Não amplie os limites enquanto reproduz o snapshot.

### Aula 7 — Estado MQTT: store.rs

Crie `src/mqtt/store.rs`. Esse arquivo transforma sessões, retained, mensagens
offline e pacotes em trânsito numa representação que pode ser gravada pela
persistência. `MqttStore` recupera/valida o documento e solicita commit ao ator.
Validação de tópico, payload e quotas ocorre antes de aceitar um estado inválido.

### Aula 8 — Roteamento: router.rs

Crie `src/mqtt/router.rs`. O ator do roteador é o proprietário do estado MQTT.
Ele recebe comandos dos handlers de conexão, prepara a transição e aguarda o
commit durável antes das confirmações pertinentes ou do fan-out. Os canais têm
capacidade limitada. Gerações de conexão permitem recusar comandos de uma
conexão antiga que perdeu a identidade para uma reconexão.

Leia a interação entre `Command`, `Actor`, `Delivery`, `AckKind`, geração de
packet-id e estados QoS. QoS 2 envolve PUBREC, PUBREL e PUBCOMP; não equivale a
confirmar que uma aplicação de negócio processou o conteúdo.

### Aula 9 — Handler de conexão e biblioteca: mod.rs/lib.rs

Crie `src/mqtt/mod.rs` e substitua `src/lib.rs` pela versão histórica completa.
O handler começa exigindo CONNECT, autentica quando o perfil pede, trata pacotes,
monitora keepalive e recebe entregas do roteador. Decodificar um pacote,
autorizar uma operação e gravar estado são responsabilidades distintas.

Os quatro arquivos MQTT referenciam tipos entre si. **Digite os quatro antes
de compilar R06**; um arquivo isolado não representa um checkpoint completo.
Depois rode build e check. Nesta versão, Last Will e filtros +/# ainda não
estão implementados no broker. A biblioteca do client reconhecer um filtro
não torna o servidor capaz de entregá-lo.

## Seção 4 — Integrar os programas executáveis

### Aula 10 — Inicialização do broker, R07

Substitua `src/main.rs` pelo arquivo histórico. Agora o main de apresentação
deixa de existir: o programa passa a iniciar o broker. A macro `#[tokio::main]`
cria o runtime; logging é configurado; variáveis de ambiente escolhem perfil,
bind e estado; o perfil do diretório é verificado; transporte e roteador são
instanciados; o laço atende conexões.

Sem `MQTT_MODE`, o padrão é seguro e exige arquivos/credenciais. Portanto,
`cargo run` sem configurar o perfil pode encerrar com erro de configuração.
Isso é diferente de falha de compilação. Primeiro rode build/check; o laboratório
aberto será descrito depois. O bind seguro histórico contém um IP específico,
que não deve ser presumido como IP da máquina do aluno.

### Aula 11 — Administrador, R08

Crie `src/bin/mqtt-admin/main.rs`. Cargo descobre esse executável automaticamente
pela pasta de binário com `main.rs`. `hash-password` produz hash com salt de uma
senha lida sem echo; `fingerprint` calcula a identificação do certificado.
Ele prepara dados de configuração, não é uma API remota nem um serviço HTTP.
Nesta reconstrução não é necessário inserir suas credenciais para compilar.

### Aula 12 — Client, R09

Crie os cinco arquivos em `src/bin/mqtt-client/`: primeiro `cli.rs`, depois
`credentials.rs`, `tls.rs`, `session.rs` e finalmente `main.rs`.
`cli` interpreta/valida opções; `credentials` lê senha com as proteções da
plataforma; `tls` configura CA/certificado/chave; `session` usa rumqttc para
publicação/assinatura, poll do event loop e tratamento de confirmações; `main`
coordena tudo. Nesta aula o client pertence ao mesmo pacote do broker.

```powershell
cargo build --locked --bins
cargo check --locked --all-targets
cargo run --locked --bin mqtt-client -- --help
```

O primeiro `--` separa opções do Cargo dos argumentos do programa. `--help` é
entendido por este client e não abre conexão. Não suponha que o broker 0.3.0
entende `--version`: essa opção foi adicionada numa versão posterior.

## Seção 5 — Completar os arquivos, validar e criar o commit, R10

### Aula 13 — Documentos, configurações e exemplo

Acrescente os arquivos restantes exibidos em R10: README, CHANGELOG, VERSIONING,
configs, docs e `examples/minimal_mqtt.rs`. O diretório `examples` é executado
somente quando solicitado ao Cargo; esse exemplo usa um bind LAN histórico e
não será iniciado automaticamente pelo roteiro. Configurações Mosquitto são
referência para outro broker; não são configuração que XMQR leia diretamente.

O README histórico menciona uma branch release/0.3. Ela não existe necessariamente
no repositório novo do aluno; siga a sequência deste roteiro. O primeiro commit
ainda não tinha LICENSE: esse arquivo foi adicionado num commit posterior. A
reprodução exata mantém essa ausência; a licença atual do XMQR está no repo atual.

### Aula 14 — Validar o código final

```powershell
cargo build --locked --bins
cargo check --locked --all-targets
cargo fmt --all -- --check
```

Build gera executáveis; check confere tipos também nos alvos de teste/exemplo;
fmt verifica formatação, sem alterar o código com `--check`. No Ubuntu/WSL,
use também `cargo test --locked` e `cargo clippy --locked --all-targets -- -D warnings`.
Teste executa o código dos testes; Clippy procura problemas e warnings são
tratados como erro quando se passa `-D warnings` após o separador `--`.
Se um gate falhar no código histórico, registre a falha: uma correção deve ser
uma nova etapa/branch, preservando a comparação exata do snapshot.

Na verificação atual, build/check e os 52 testes Linux passaram; Clippy 1.99
com warnings como erro apontou `assert_is_empty` em `src/mqtt/store.rs:305`.
A versão histórica usa `debug_assert!(remainder.is_empty());`. A sugestão é
`debug_assert_eq!(remainder, []);`, que também mostra o valor se a asserção falhar.
Para reproduzir exatamente o primeiro commit, mantenha a linha original e
registre esse resultado. Para uma evolução posterior, crie uma branch/cópia de
correção, aplique a mudança e repita fmt, testes e Clippy. O material contém a
evidência do ensaio dessa mudança numa cópia separada, fora de R10/codigo/.

### Aula 15 — Pub/sub no laboratório local Ubuntu/WSL

Use somente um estado novo de estudo e uma porta de loopback diferente da do
serviço existente. Abra três terminais na pasta do projeto dentro do Ubuntu.
Para abrir o Ubuntu a partir do PowerShell, use `wsl -d Ubuntu-26.04`. `-d`
seleciona a distribuição pelo nome; `wsl --list --verbose` mostra os nomes
instalados caso o seu seja diferente. Já no terminal Linux, para a pasta
criada na primeira aula:

```bash
cd /mnt/d/projects/my-project/rapidez-projects/xmqr-curso-03
rustc --version
cargo --version
export CARGO_TARGET_DIR="$HOME/.cache/xmqr-curso-r10-target"
cargo build --locked --bins
```

`/mnt/d` corresponde ao disco D do Windows. Rust no Ubuntu é uma instalação
separada do Rust no Windows: confira as duas ferramentas no próprio Ubuntu.
`export CARGO_TARGET_DIR` escolhe um diretório de compilação Linux fora do
target usado pelo Windows, só nesse terminal. Isso evita misturar os arquivos
gerados por sistemas diferentes. Repita o export nos três terminais do exercício.
Use o mesmo caminho do projeto e do target em todos.

Terminal 1:

```bash
mkdir -p "$HOME/.local/share/xmqr-curso-r10"
chmod 700 "$HOME/.local/share/xmqr-curso-r10"
MQTT_MODE=open-lab MQTT_BIND=127.0.0.1:18839 \
MQTT_STATE_DIR="$HOME/.local/share/xmqr-curso-r10" RUST_LOG=info \
cargo run --locked --bin mqtt-broker
```

`$HOME` é a pasta pessoal no Ubuntu. O estado fica fora do projeto para não
entrar acidentalmente no commit, inclusive seu marcador de perfil. As
atribuições antes de Cargo definem ambiente só daquele
comando. `chmod 700` dá acesso ao proprietário do diretório. Esse perfil recusa
bind não loopback e não exige certificados. O diretório não deve ser reutilizado
entre perfis de segurança. Se já contém dados de outro exercício, escolha nome novo.

Terminal 2:

```bash
cargo run --locked --bin mqtt-client -- sub --open-lab \
  --topic 'aula/mensagem' --host 127.0.0.1 --port 18839 \
  --client-id 'curso-r10-sub' --qos 0
```

Terminal 3:

```bash
cargo run --locked --bin mqtt-client -- pub --open-lab \
  --topic 'aula/mensagem' --message 'Ola, XMQR!' \
  --host 127.0.0.1 --port 18839 --client-id 'curso-r10-pub' --qos 0
```

O assinante deve receber `Ola, XMQR!`. Termine os processos do exercício com
Ctrl+C nos terminais correspondentes. Esse teste simples não comprova TLS,
conformidade completa ou durabilidade perante queda de energia. A persistência
e leitura privada de arquivos do projeto têm requisitos Unix: compilar no
Windows não garante que esse laboratório funcione integralmente nele.

### Aula 16 — Criar seu primeiro commit

Retorne à raiz da pasta nova de estudo, que contém os 35 arquivos finais.
Mantenha guias e ZIPs fora dessa pasta se deseja comparar seu conteúdo ao snapshot.

```powershell
git init --initial-branch=main
git status --short
git add .
git diff --cached --stat
git diff --cached --check
git commit -m "feat: reconstruir XMQR 0.3.0"
git log -1 --oneline
```

`init` cria o repositório local. `status` mostra arquivos novos/modificados.
`add .` coloca os arquivos não ignorados na preparação do commit; `.gitignore`
exclui target e vários arquivos gerados/de credenciais. Ele não cobre todo
arquivo que uma aplicação possa criar: mantenha estado e guias fora do projeto.
Revise a lista antes de
prosseguir: não inclua chaves, senhas, estado ou os binários compilados.
`diff --cached` mostra o que foi preparado; `--stat` resume as mudanças;
`--check` procura problemas de whitespace. `commit -m` grava a versão e sua
mensagem; `log -1` mostra o registro criado.

Se Git pedir identidade, configure **somente este repositório**, com seus dados:

```powershell
git config user.name 'SEU NOME'
git config user.email 'SEU EMAIL DE COMMIT'
```

Substitua os textos em maiúsculas pelos dados escolhidos, por exemplo o email
noreply fornecido pela sua conta GitHub. Repita o comando commit após configurar.
Não precisa de tag/release para criar esse primeiro commit. Publicar no GitHub
é uma etapa posterior num repositório de estudo próprio; não force push sobre
o XMQR existente para tentar substituir seu primeiro registro.

## Resultado esperado

Você terá digitado os arquivos de aplicação, compreendido as responsabilidades
dos módulos, usado Cargo para compilar e Git para gravar sua primeira versão.
R10 contém o mesmo código do primeiro commit histórico; seu SHA novo e os
registros do curso identificam sua reconstrução. Consulte VALIDACAO.json para
distinguir resultados executados agora, limitações e instruções ainda não ensaiadas.

Fontes de ferramentas: [Rust/Cargo](https://doc.rust-lang.org/book/ch01-03-hello-cargo.html),
[manifesto e lock](https://doc.rust-lang.org/cargo/guide/cargo-toml-vs-cargo-lock.html),
[Git init](https://git-scm.com/docs/git-init).
