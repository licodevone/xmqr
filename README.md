# XMQR

XMQR Ã© um broker MQTT escrito em Rust, criado para evoluir em pequenas fatias
testÃ¡veis e interoperÃ¡veis. O foco atual Ã© MQTT 3.1.1; recursos MQTT 5.0 serÃ£o
adicionados apenas quando puderem ser isolados e verificados sem enfraquecer o
nÃºcleo 3.1.1.

**Nome do projeto:** XMQR. Durante a sÃ©rie `0.x`, o crate e os executÃ¡veis
mantÃªm `mqtt-broker` e `mqtt-admin`. O cliente independente `xmqr-client` mantÃ©m
o binÃ¡rio compatÃ­vel `mqtt-client`.

> **Estado do projeto:** experimental. XMQR ainda nÃ£o declara conformidade MQTT
> 3.1.1 completa nem prontidÃ£o para produÃ§Ã£o. Last Will existe na 0.6 local; ainda
> faltam cobertura externa completa, testes de carga e recuperaÃ§Ã£o operacional.

## Por que XMQR?

- implementaÃ§Ã£o assÃ­ncrona em Rust com limites explÃ­citos por conexÃ£o;
- separaÃ§Ã£o entre codec, conexÃ£o, autenticaÃ§Ã£o, roteamento e persistÃªncia;
- QoS 0, 1 e 2 com estado durÃ¡vel e confirmaÃ§Ã£o apÃ³s persistÃªncia;
- sessÃµes persistentes, mensagens retidas e `UNSUBSCRIBE`;
- TLS/mTLS, usuÃ¡rio/senha e ACL deny-by-default no modo seguro;
- laboratÃ³rios locais progressivos para aprender MQTT antes de introduzir TLS;
- testes associados Ã s clÃ¡usulas MQTT 3.1.1 quando aplicÃ¡vel.

## VersÃµes

| VersÃ£o | Estado | Destaques |
| --- | --- | --- |
| `0.3.x` | manutenÃ§Ã£o | laboratÃ³rio QoS 0 aberto, anÃ´nimo e restrito a loopback |
| `0.4.x` | estÃ¡vel experimental | laboratÃ³rios com senha e com ACL; CRUD administrativo de usuÃ¡rios |
| `0.5.x` | tag v0.5.0 verificada | filtros `+`/`#`, regra `$` e testes com Mosquitto |
| `0.6.x` | tag v0.6.0 local/remota verificada | retained revisado e Last Will duravel |
| `0.7.x` | gates Unix e integraÃ§Ãµes aprovados, aguardando publicaÃ§Ã£o | monitoramento HTTP opcional |

VersÃµes publicadas sÃ£o identificadas por tags anotadas, por exemplo
`v0.4.0`. As branches `release/0.3` e `release/0.4` existem apenas para
correÃ§Ãµes compatÃ­veis dessas sÃ©ries. O desenvolvimento futuro ocorre em
`main`. Consulte [VERSIONING.md](VERSIONING.md) e [CHANGELOG.md](CHANGELOG.md).

Consulte [sequencia incremental](docs/incremental-versions.md) e [Last Will](docs/last-will.md).

## Arquitetura

```mermaid
flowchart LR
    C[Cliente MQTT] --> T[Transporte TCP ou TLS/mTLS]
    T --> K[Codec MQTT 3.1.1]
    K --> A[AutenticaÃ§Ã£o e ACL]
    A --> R[Roteador e sessÃµes]
    R --> P[PersistÃªncia durÃ¡vel]
    R --> S[Assinantes]
```

O caminho assÃ­ncrono nÃ£o executa I/O de disco diretamente. AlteraÃ§Ãµes durÃ¡veis
sÃ£o serializadas por um ator de persistÃªncia; ACKs que transferem
responsabilidade sÃ£o enviados somente depois do nÃ­vel de durabilidade
configurado.

## Release atual e próxima versão

A tag publicada mais recente é `v0.8.0`, com segurança dinâmica por bundle
privado e reload local por SIGHUP. O próximo candidato é `0.9.0`: backup
offline verificável e restauração em diretório novo. O backup exige broker
parado e Linux/WSL; consulte [persistência](docs/architecture/persistence.md).
A imagem local, parâmetros de segurança e montagem dos volumes estão em
[Docker](docs/docker.md); não há publicação de imagem nesta etapa.

## Funcionalidades MQTT 3.1.1

| Recurso | SituaÃ§Ã£o |
| --- | --- |
| `CONNECT`/`CONNACK` | implementado para os perfis documentados |
| `PUBLISH` QoS 0/1/2 | implementado |
| `PUBACK`/`PUBREC`/`PUBREL`/`PUBCOMP` | implementado |
| `SUBSCRIBE`/`SUBACK` | implementado |
| `UNSUBSCRIBE`/`UNSUBACK` | implementado |
| Mensagens retidas | implementado |
| SessÃµes persistentes (`CleanSession=0`) | implementado |
| Filtros `+` e `#` | implementado na sÃ©rie 0.5 em desenvolvimento |
| Last Will | implementado em 0.6 local, com persistencia e ACL |
| MQTT 5.0 | fora do escopo atual |

A evidÃªncia disponÃ­vel fica na
[matriz MQTT 3.1.1](docs/conformance/mqtt311-status.md). A tabela nÃ£o representa
uma declaraÃ§Ã£o de conformidade completa.

## ComeÃ§o rÃ¡pido: laboratÃ³rio aberto

Requisitos:

- Rust estÃ¡vel `1.88` ou mais recente;
- componentes `rustfmt` e `clippy` (`rustup component add rustfmt clippy`);
- Linux ou WSL2 para o fluxo administrativo atÃ´mico;
- OpenSSL apenas para preparar certificados do modo seguro.

Compile broker/admin e o cliente independente na pasta vizinha:

```bash
git clone https://github.com/licodevone/xmqr.git
cd xmqr
export CARGO_TARGET_DIR="$HOME/.cache/xmqr-target"
cargo build --locked --release --bins
cargo build --manifest-path ../xmqr-client/Cargo.toml --locked --release --bin mqtt-client
```

No primeiro terminal, inicie o broker local sem autenticaÃ§Ã£o:

```bash
mkdir -p "$HOME/.local/share/xmqr-open-lab"
chmod 700 "$HOME/.local/share/xmqr-open-lab"

MQTT_MODE=open-lab \
MQTT_BIND=127.0.0.1:1883 \
MQTT_STATE_DIR="$HOME/.local/share/xmqr-open-lab" \
RUST_LOG=info \
"$CARGO_TARGET_DIR/release/mqtt-broker"
```

No segundo terminal, assine o tÃ³pico:

```bash
export CARGO_TARGET_DIR="$HOME/.cache/xmqr-target"
"$CARGO_TARGET_DIR/release/mqtt-client" sub \
  --open-lab \
  --topic 'aula/mensagem' \
  --host 127.0.0.1 \
  --port 1883 \
  --client-id 'exemplo-sub' \
  --qos 0
```

No terceiro terminal, publique manualmente:

```bash
export CARGO_TARGET_DIR="$HOME/.cache/xmqr-target"
"$CARGO_TARGET_DIR/release/mqtt-client" pub \
  --open-lab \
  --topic 'aula/mensagem' \
  --message 'OlÃ¡, XMQR!' \
  --host 127.0.0.1 \
  --port 1883 \
  --client-id 'exemplo-pub' \
  --qos 0
```

O roteiro completo, incluindo senha e ACL, estÃ¡ em
[docs/laboratorio-mqtt-aberto.md](docs/laboratorio-mqtt-aberto.md).

O broker deve registrar `OPEN LAB listener started...`; o assinante deve mostrar
`Assinatura ativa...` e, depois da publicaÃ§Ã£o, imprimir `OlÃ¡, XMQR!`. Pressione
`Ctrl+C` no assinante e no broker para encerrar. Reutilize o diretÃ³rio de estado
somente com o mesmo perfil; para comeÃ§ar limpo, mova o diretÃ³rio antigo para um
backup enquanto o broker estiver parado.

## Perfis de seguranÃ§a

| `MQTT_MODE` | Transporte | Identidade | AutorizaÃ§Ã£o | Uso |
| --- | --- | --- | --- | --- |
| `open-lab` | TCP simples | anÃ´nimo | qualquer tÃ³pico vÃ¡lido | primeira aula local |
| `password-lab` | TCP simples | usuÃ¡rio + senha | qualquer tÃ³pico vÃ¡lido | aula de autenticaÃ§Ã£o |
| `acl-lab` | TCP simples | usuÃ¡rio + senha | ACL deny-by-default | aula de autorizaÃ§Ã£o |
| `secure-mtls` | TLS/mTLS | certificado + usuÃ¡rio + senha | ACL deny-by-default | modo endurecido padrÃ£o |

Os trÃªs modos de laboratÃ³rio aceitam somente `127.0.0.1` ou `::1`. Senhas e
payloads trafegam sem criptografia em `password-lab` e `acl-lab`; nunca exponha
esses modos Ã  LAN ou Ã  internet.

## AdministraÃ§Ã£o de usuÃ¡rios

```bash
"$CARGO_TARGET_DIR/release/mqtt-admin" user create --users-file users.toml --username dispositivo-01
"$CARGO_TARGET_DIR/release/mqtt-admin" user list --users-file users.toml
"$CARGO_TARGET_DIR/release/mqtt-admin" user update-password --users-file users.toml --username dispositivo-01
"$CARGO_TARGET_DIR/release/mqtt-admin" user delete --users-file users.toml --username dispositivo-01
```

Senhas sÃ£o solicitadas interativamente e armazenadas como hash Argon2id. O
arquivo real `users.toml` Ã© ignorado pelo Git; publique somente arquivos
`.example` sem credenciais reais. Veja
[docs/administracao-usuarios.md](docs/administracao-usuarios.md).

## ConfiguraÃ§Ã£o

| VariÃ¡vel | ObrigatÃ³ria em | Finalidade |
| --- | --- | --- |
| `MQTT_MODE` | opcional | perfil; ausÃªncia seleciona `secure-mtls` |
| `MQTT_BIND` | opcional | endereÃ§o; laboratÃ³rios usam `127.0.0.1:1883` |
| `MQTT_STATE_DIR` | todos | WAL, snapshot e marcador do perfil |
| `MQTT_USERS_FILE` | senha, ACL e seguro | usuÃ¡rios e hashes Argon2id |
| `MQTT_ACL_FILE` | ACL e seguro | permissÃµes de publicaÃ§Ã£o e assinatura |
| `MQTT_SERVER_CERT` | seguro | cadeia do certificado do servidor |
| `MQTT_SERVER_KEY` | seguro | chave privada do servidor |
| `MQTT_CLIENT_CA` | seguro | CA usada para validar clientes |
| `MQTT_CLIENT_CRL` | seguro, opcional | lista de certificados revogados |

Cada perfil precisa de seu prÃ³prio `MQTT_STATE_DIR`. XMQR recusa reutilizar o
estado de um perfil diferente.

## Desenvolvimento

```bash
cargo fmt --all -- --check
cargo test --locked
cargo clippy --locked --all-targets -- -D warnings
python3 scripts/license_inventory.py --check
```

Para os testes externos no Linux/WSL, instale os clientes Mosquitto e execute:

```bash
sudo apt install mosquitto-clients
cargo build --locked --bins
python3 scripts/verify_interop.py --broker "${CARGO_TARGET_DIR:-target}/debug/mqtt-broker"
```

O script usa portas loopback descobertas e diretÃ³rios temporÃ¡rios prÃ³prios.
Veja [filtros, evidÃªncias e migraÃ§Ã£o](docs/wildcard-subscriptions.md).

MudanÃ§as de protocolo devem incluir testes unitÃ¡rios e, quando cruzarem
componentes, testes de integraÃ§Ã£o ou interoperabilidade. Consulte
[CONTRIBUTING.md](CONTRIBUTING.md).

## Estrutura do repositÃ³rio

```text
src/auth/            autenticaÃ§Ã£o, identidades e ACL
src/mqtt/            codec, mÃ¡quina de conexÃ£o, roteamento e sessÃµes
src/persistence/     WAL, snapshots e ator de persistÃªncia
src/transport/       TCP local e TLS/mTLS
../xmqr-client/      projeto independente do cliente MQTT
src/bin/mqtt-admin   administraÃ§Ã£o segura de usuÃ¡rios
configs/             configuraÃ§Ãµes-modelo sem segredos
docs/                arquitetura, seguranÃ§a, conformidade e laboratÃ³rios
examples/            exemplos mÃ­nimos
```

## DocumentaÃ§Ã£o

- [HistÃ³rico de versÃµes](CHANGELOG.md)
- [PolÃ­tica de versÃµes](VERSIONING.md)
- [Cliente MQTT](docs/mqtt-client.md)
- [LaboratÃ³rio progressivo](docs/laboratorio-mqtt-aberto.md)
- [AutenticaÃ§Ã£o e ACL](docs/security/auth-acl.md)
- [Transporte seguro](docs/security/secure-transport.md)
- [PersistÃªncia](docs/architecture/persistence.md)
- [Roadmap](docs/ROADMAP.md)

## SeguranÃ§a e suporte

NÃ£o abra uma issue pÃºblica para vulnerabilidades ainda nÃ£o corrigidas. Siga
[SECURITY.md](SECURITY.md). Para perguntas de uso, consulte [SUPPORT.md](SUPPORT.md).

## Contribuindo

ContribuiÃ§Ãµes sÃ£o bem-vindas, principalmente em conformidade MQTT 3.1.1,
interoperabilidade, testes de falha, seguranÃ§a e observabilidade. Leia
[CONTRIBUTING.md](CONTRIBUTING.md) antes de abrir uma pull request.

## LicenÃ§a

O XMQR Ã© distribuÃ­do sob a licenÃ§a MIT. Consulte o arquivo
[LICENSE](LICENSE) para conhecer os termos.
As dependÃªncias conservam suas licenÃ§as originais. Consulte o
[inventÃ¡rio](docs/third-party-licenses.md) e a
[polÃ­tica de distribuiÃ§Ã£o](docs/licensing.md).

## Monitoramento opcional

P43 adiciona `/health`, `/ready` e `/metrics`, desabilitados por padrÃ£o e
restritos a loopback. Consulte [configuraÃ§Ã£o e semÃ¢ntica](docs/monitoring.md).
Gates Unix e integraÃ§Ãµes locais aprovados; publicaÃ§Ã£o 0.7 aguarda o mantenedor.

## Resultado atual P43

2026-10-08:72 testes Unix, fmt/Clippy/inventÃ¡rio/build e6 integraÃ§Ãµes monitoring
mais9 regressÃµes Will PASS, com cliente independente baseline26c1019. Seis
recusas de configuraÃ§Ã£o reais tambÃ©m PASS. HistÃ³rico de bloqueios anteriores
nÃ£o descreve o estado atual. Mosquitto/TLS/mTLS externo NOT_RUN. Aguardar
publicaÃ§Ã£o do mantenedor; ver registro P43. Nenhuma implementaÃ§Ã£o0.8 executada.


## P44 - seguranÃ§a dinÃ¢mica, 0.8.0 local

Base HEAD e tag v0.7.0: 3a3dde7, confirmada antes da implementaÃ§Ã£o autorizada.
Bundle privado opt-in Linux/WSL com usuÃ¡rios, grupos, papÃ©is e ACL; reload por
SIGHUP local. Reload vÃ¡lido encerra todas as conexÃµes dinÃ¢micas e exige nova
autenticaÃ§Ã£o, preservando responsabilidade inbound QoS 2. Documento durÃ¡vel,
quotas, dependÃªncias e MIT preservados; cliente independente nÃ£o alterado.
A versÃ£o aguarda registro dos gates finais; nÃ£o hÃ¡ publicaÃ§Ã£o automÃ¡tica.
DocumentaÃ§Ã£o: docs/security/dynamic-security.md; evidÃªncia:
prompts/registros/P44-0.8.0.md (caminhos relativos Ã  raiz do repositÃ³rio).
ReferÃªncias anteriores a P44 apenas preparado descrevem checkpoints histÃ³ricos.
