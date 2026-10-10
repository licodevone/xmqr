# XMQR

Broker MQTT3.1.1 experimental em Rust2024/Tokio, licença MIT. Pacote mqtt-broker;
binários mqtt-broker e mqtt-admin. O client é o projeto independente ../xmqr-client.
Não há declaração de conformidade completa ou prontidão para produção.

## Versões

| Versão | Marco |
| --- | --- |
| 0.3 | laboratório aberto restrito a loopback |
| 0.4 | senha, ACL e administração de usuários |
| 0.5 | filtros +/#, regra $ e interoperabilidade |
| 0.6 | Last Will durável e revisão de retained |
| 0.7 | health/readiness/métricas HTTP opcionais loopback |
| 0.8 | segurança dinâmica por bundle e SIGHUP |
| 0.9 | backup/verify/restore offline e Docker; tag v0.9.0 publicada |
| 0.10 | parada coordenada, systemd e deb Ubuntu26.04 amd64 |

Veja [CHANGELOG](CHANGELOG.md), [versionamento](VERSIONING.md) e releases no GitHub.
Tags antigas são imutáveis; releases0.x são experimentais. Histórico de execução
em prompts/registros descreve o resultado de cada marco, não o estado atual.

## Instalação Ubuntu / WSL

Veja [guia Ubuntu26.04 e systemd](docs/ubuntu-systemd.md). O pacote deb instala
binários/unit/configuração, cria usuário xmqr e preserva dados. Não ativa o
serviço antes de configurar certificados e credenciais.

```sh
sudo apt install ./xmqr-broker_0.10.0-1_amd64.deb
sudo systemctl enable --now xmqr-broker.service
systemctl status xmqr-broker.service
journalctl -u xmqr-broker.service -f
```

O enable/start acima deve ocorrer após configurar /etc/xmqr/broker.env e
arquivos TLS/bundle. Não há repositório APT próprio assinado ainda.

## Recursos e limites

QoS0/1/2, retained, sessões persistentes, SUBSCRIBE/UNSUBSCRIBE, filtros +/#,
Last Will durável, TLS/mTLS, senha Argon2id e ACL deny-by-default.
Persistência por WAL/snapshot e ator dedicado, commit durável antes de ACKs
pertinentes. SIGTERM/SIGINT coordenam listener, Wills e shutdown do writer.
MQTT5, WebSockets e bridge não implementados.

Limites:64 conexões/sessões,256 assinaturas por sessão,64 mensagens offline,
32 inflight,1024 bytes UTF-8 por tópico/filtro,4096 bytes por payload e64KiB
por pacote. São quotas de projeto, não benchmarks de capacidade.

secure-mtls é o padrão, com certificado+senha+ACL. open-lab/password-lab/acl-lab
são apenas loopback e usam estados separados. Não exponha os laboratórios à rede.
Backup/administração durável requerem Linux/WSL. Monitoramento é opcional e
loopback; active no systemd não comprova readiness MQTT.

## Compilar e laboratório

Rust1.88 declarado (toolchain exato ainda não validado); build atual Rust1.99.

```sh
cargo build --locked --bins
cargo build --manifest-path ../xmqr-client/Cargo.toml --locked --bin mqtt-client
```

[Laboratório progressivo](docs/laboratorio-mqtt-aberto.md) contém o roteiro de
publicação/assinatura. [Docker](docs/docker.md) explica imagem e volumes;
[cliente independente](../xmqr-client/README.md) tem as opções atuais.

## Validação e documentação

```sh
cargo fmt --all -- --check
cargo test --locked
cargo clippy --locked --all-targets -- -D warnings
python3 scripts/license_inventory.py --check
cargo build --locked --bins
python3 scripts/verify_shutdown.py --broker target/debug/mqtt-broker
```

Interoperabilidade externa: scripts/verify_interop.py requer clientes Mosquitto;
seu CI executa open-lab. Isso não prova TLS/mTLS externo nem conformidade total.

- [Matriz MQTT](docs/conformance/mqtt311-status.md)
- [Persistência e backup](docs/architecture/persistence.md)
- [Segurança dinâmica](docs/security/dynamic-security.md)
- [Transporte seguro](docs/security/secure-transport.md)
- [Administração](docs/administracao-usuarios.md)
- [Monitoramento](docs/monitoring.md)
- [Roadmap](docs/ROADMAP.md)
- [Contribuição](CONTRIBUTING.md)
- [Segurança](SECURITY.md)
- [Licenças de terceiros](docs/third-party-licenses.md)

Preserve MIT e atribuições de terceiros ao redistribuir. Nunca versionar secrets
ou estado MQTT. Registro desta etapa: prompts/registros/P47-systemd-ubuntu.md.
