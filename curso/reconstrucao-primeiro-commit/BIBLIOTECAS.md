# Bibliotecas do primeiro commit: leia antes de usá-las

Uma crate é uma unidade de código Rust. Cargo lê `Cargo.toml`, obtém as crates
declaradas e as dependências delas, fixa as versões no lock e as compila. O nome
da dependência com hífen costuma aparecer no código com sublinhado. `std` é a
biblioteca padrão, fornecida com Rust; `use` apenas torna nomes acessíveis no
módulo, não baixa nem inicia uma biblioteca.

## tokio — trabalhar enquanto outras operações aguardam

O broker atende conexões que passam boa parte do tempo aguardando bytes. Tokio
fornece runtime, sockets assíncronos, timers e canais. Runtime significa a
infraestrutura que trabalha durante a execução do programa, aqui agendando
tarefas quando há eventos. `async fn` devolve uma operação que pode ser aguardada;
`.await` permite suspendê-la até haver resultado. Não cria uma thread exclusiva
para cada conexão. Arquivos e hashes custosos precisam de tratamento separado
para não bloquear workers.

No manifesto, `macros` habilita `#[tokio::main]`/testes e macros; `rt-multi-thread`
habilita runtime com workers; `net` oferece sockets; `io-util` oferece extensões
de leitura/escrita; `sync` habilita canais/semaphore; `time` habilita timers;
`signal` habilita APIs de sinais, mas declarar essa feature não instala um handler
de encerramento automaticamente. O primeiro broker não tem todas as evoluções
de shutdown das versões posteriores.

`mpsc` possui vários remetentes e um receptor; uma capacidade limita comandos
pendentes. `oneshot` transporta uma resposta única. `Semaphore` limita vagas.
Encontrado em persistência/ator, transporte, roteador e client.
Fonte: [documentação Tokio](https://docs.rs/tokio/).

## serde e toml — transformar dados em tipos

Serde fornece os traits `Serialize` e `Deserialize`. Eles descrevem como
converter entre tipos Rust e uma representação externa. Não escolhe sozinho um
formato de arquivo. A crate `toml` fornece esse formato e conecta-o aos traits:
uma tabela `[secao]`, campos `nome = valor` e listas podem virar structs.
`#[derive(Deserialize)]` gera a implementação; atributos Serde restringem ou
ajustam campos. A leitura bem-sucedida não substitui validar tamanhos, quotas e
regras do domínio. O projeto faz essa validação explicitamente.

Usadas na configuração de usuários/ACL e no documento de estado MQTT. O broker
0.3.0 não possui o TOML geral de servidor das versões posteriores: não confunda
esses usos. Fontes: [Serde](https://serde.rs/) e [TOML Rust](https://docs.rs/toml/).

## argon2 — verificar senha sem guardar a senha em texto

Argon2 transforma senha e salt em um hash com custo de memória/processamento.
Salt é um valor aleatório individual que impede que senhas iguais gerem sempre
o mesmo registro. O hash é uma representação para verificação, não senha
criptografada que o servidor deveria conseguir recuperar. `PasswordHasher`
produz a representação; `PasswordVerifier` verifica uma tentativa; `PasswordHash`
interpreta o formato PHC, que também registra parâmetros.

`argon2_context` centraliza os parâmetros aceitos pelo projeto. Limites de senha
e de hashes em paralelo evitam consumo ilimitado de recursos. Usada em auth e
mqtt-admin. Fonte: [Argon2 RustCrypto](https://docs.rs/argon2/).

## rand_core — obter aleatoriedade para o salt

Fornece interfaces de geradores aleatórios. `OsRng`, habilitado pela feature
`getrandom` desta versão, obtém aleatoriedade do sistema operacional. O admin
usa isso para gerar salt, em vez de um contador ou uma senha fixa. Não imprime
uma credencial e não cria certificado. Fonte: [rand_core](https://docs.rs/rand_core/0.6.4/).

## rpassword — ler uma senha sem mostrá-la no terminal

`prompt_password` lê texto sem echo. O client usa o prompt no modo seguro; o
admin pede senha e confirmação. Isso evita mostrar a senha durante a digitação,
mas não a transforma automaticamente num hash nem substitui proteção de memória.
Argon2 e Zeroizing têm responsabilidades diferentes. Nunca passe sua senha real
como argumento de uma linha de comando gravada em material de curso.
Fonte: [rpassword](https://docs.rs/rpassword/).

## rustls — estabelecer TLS e conferir identidade

TLS protege os bytes da conexão e verifica o servidor por sua cadeia de
certificados e nome/endereço esperado. mTLS acrescenta verificação do certificado
do client pelo servidor. `ServerConfig`, `ClientConfig` e `RootCertStore` representam
essas escolhas. Ter TLS válido não concede automaticamente autorização num
tópico: ainda existem autenticação MQTT e ACL.

O manifesto desativa features padrão e escolhe `aws_lc_rs` como provedor de
criptografia, `std`, `logging`, `tls12` e `prefer-post-quantum`. Esta última
permite preferências criptográficas suportadas pelo provedor/versão; não é prova
de uma negociação específica nem exige que todo peer use o mesmo algoritmo.
O provedor pode precisar de ferramentas de compilação C/C++.
Fonte: [Rustls](https://docs.rs/rustls/).

## rustls-pemfile — interpretar os arquivos PEM

PEM é uma forma textual de representar certificados e chaves, com cabeçalhos e
conteúdo codificado. Essa crate lê os itens e entrega tipos que Rustls utiliza.
Não cria uma CA, não assina certificados, não decide em quem confiar e não pede
automaticamente a senha de uma chave criptografada. As rotinas do projeto
conferem conteúdo vazio, limites e formato esperado antes de montar a configuração.
Fonte: [rustls-pemfile](https://docs.rs/rustls-pemfile/).

## tokio-rustls — unir sockets assíncronos e TLS

Adapta Rustls à entrada/saída do Tokio. `TlsAcceptor` conduz o handshake do
servidor; o stream resultante continua oferecendo leitura/escrita assíncrona.
Usada no transporte seguro. As features selecionam o provedor AWS-LC e suporte
TLS1.2; TLS e deadlines são responsabilidades combinadas com o código do projeto.
Fonte: [tokio-rustls](https://docs.rs/tokio-rustls/).

## rumqttc — client MQTT, não o broker

Implementa o protocolo do lado do client. `MqttOptions` reúne endereço, identidade,
QoS, keepalive e opções; `AsyncClient` envia solicitações; `EventLoop` precisa ser
consultado com `poll().await` para fazer progresso e receber eventos. Enfileirar
uma publicação não é receber confirmação do broker. Por isso o código observa
eventos e aplica timeouts conforme a operação.

No manifesto, `=0.25.1` fixa exatamente a versão. `use-rustls-no-provider` evita
selecionar outro provedor automaticamente, enquanto o projeto fornece sua
configuração Rustls. Encontrada somente no client histórico, embora ele ainda
pertença ao pacote mqtt-broker. Fonte: [rumqttc 0.25.1](https://docs.rs/rumqttc/0.25.1/).

## sha2 — calcular SHA-256 dos bytes do certificado

SHA-256 produz um resumo de tamanho fixo. `Sha256`/`Digest` são usados para
fingerprint do certificado em DER. Fingerprint ajuda a comparar a identidade
configurada com a apresentada; calcular um hash não valida a cadeia de confiança
TLS e não é a mesma operação que verificar senha com Argon2.
Fonte: [sha2](https://docs.rs/sha2/).

## subtle — comparações projetadas para evitar variação óbvia por byte

Fornece `ConstantTimeEq`, utilizado nas comparações sensíveis previstas pelo
código. Reduz diferenças de tempo de comparação que poderiam revelar onde dois
valores diferem. Não garante sozinho que toda a aplicação execute em tempo
constante ou que não exista outro canal lateral. Fonte: [subtle](https://docs.rs/subtle/).

## zeroize — limpar buffers sensíveis quando forem descartados

`Zeroizing` envolve um valor e o limpa ao ser descartado. Usado em senhas e
materiais sensíveis nas rotinas que escolhem essa proteção. Não remove copies
que outra função possa ter criado, não apaga logs e não substitui controle de
acesso a arquivos. Fonte: [zeroize](https://docs.rs/zeroize/).

## thiserror — definir erros próprios com mensagens e conversões

A macro `#[derive(Error)]` gera implementações necessárias a tipos de erro.
`#[error(...)]` define mensagem e `#[from]` permite conversões explícitas para
uma variante. Isso torna visíveis situações como documento inválido, canal
encerrado e erro de I/O. Não recupera uma falha automaticamente: o chamador ainda
decide entre propagar, rejeitar ou encerrar. Fonte: [thiserror](https://docs.rs/thiserror/).

## crc32fast — detectar corrupção dos registros de disco

Calcula CRC32 de bytes de um registro/snapshot. A recuperação pode detectar um
conteúdo alterado ou uma gravação incompleta em vez de aceitá-la como válida.
CRC é verificação de integridade acidental, não assinatura criptográfica nem
autenticação contra alguém que possa modificar o arquivo e recalcular o CRC.
Fonte: [crc32fast](https://docs.rs/crc32fast/).

## fs2 — exclusão de escritores por lock de arquivo

`FileExt` oferece operações de lock usadas na persistência. O arquivo de lock
protege o diretório de estado contra outro processo escritor. Ele não é um
mutex para todas as mensagens em memória e não muda a semântica de fsync.
O sistema operacional e filesystem influenciam as operações disponíveis.
Fonte: [fs2](https://docs.rs/fs2/).

## futures-util — operações adicionais sobre futuros

`FutureExt` acrescenta métodos aos futuros. O transporte utiliza recursos como
`catch_unwind` para conter panic no atendimento de uma conexão quando o futuro
é consultado. O perfil release mantém `panic = "unwind"` por essa estratégia;
abortar o processo seria diferente de capturar a falha de uma tarefa.
Fonte: [futures-util](https://docs.rs/futures-util/).

## tracing e tracing-subscriber — produzir e apresentar eventos

`tracing` fornece macros como info!, warn! e debug!, com campos estruturados.
`tracing-subscriber` configura quem recebe/apresenta os eventos. O main escolhe
formato compacto e `EnvFilter`; `RUST_LOG` define os níveis desejados. Essas
crates registram observações, não garantem persistência de dados MQTT nem sucesso
de negócio. Uma política de logs deve evitar senha, chave e payload privado.
Fontes: [tracing](https://docs.rs/tracing/) e [tracing-subscriber](https://docs.rs/tracing-subscriber/).

## tempfile — diretórios temporários para testes

Está em dev-dependencies. Os testes criam diretórios e arquivos de estado
fictício sem reutilizar o estado do operador. Um TempDir normalmente remove
seu conteúdo quando o valor é descartado. É apoio de teste, não gerenciador de
dados persistentes de produção. Fonte: [tempfile](https://docs.rs/tempfile/).

## Opções de perfil e lints do manifesto

`panic = "unwind"` seleciona desenrolar a pilha em panic; `strip = "symbols"`
retira símbolos do binário de release; `lto = "thin"` habilita otimização entre
unidades na linkagem release. Não afetam um build debug da mesma maneira.
`unsafe_code = "forbid"` proíbe unsafe no código do pacote. Os lints Clippy
selecionam grupos e severidades; `cargo build` não executa Clippy automaticamente.
Fonte: [perfis Cargo](https://doc.rust-lang.org/cargo/reference/profiles.html).
