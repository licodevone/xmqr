# XMQR

XMQR é um broker MQTT experimental escrito em Rust, com foco inicial em MQTT
3.1.1, limites explícitos e persistência durável. Na série `0.x`, os binários
mantêm os nomes `mqtt-broker`, `mqtt-client` e `mqtt-admin`.

> XMQR ainda não declara conformidade MQTT 3.1.1 completa nem prontidão para
> produção. Last Will, filtros `+`/`#`, interoperabilidade externa completa e
> validação de capacidade ainda são trabalho futuro nesta versão.

## XMQR 0.3.0

Esta versão acrescenta um laboratório local aberto para aprender publicação e
assinatura MQTT antes de introduzir certificados:

- `MQTT_MODE=open-lab`, sem TLS, autenticação ou ACL;
- bind obrigatório em `127.0.0.1` ou `::1`;
- cliente manual com `--open-lab`;
- diretório de estado isolado por perfil;
- QoS 0, 1 e 2, retained e sessões persistentes herdados do núcleo anterior;
- `secure-mtls` continua sendo o modo padrão.

## Começo rápido

Requisitos: Rust estável `1.88+`, `rustfmt`, `clippy` e Linux/WSL2.

```bash
git clone https://github.com/licodevone/xmqr.git
cd xmqr
git switch release/0.3
export CARGO_TARGET_DIR="$HOME/.cache/xmqr-target"
cargo build --locked --release --bin mqtt-broker --bin mqtt-client
```

Terminal 1 — broker:

```bash
mkdir -p "$HOME/.local/share/xmqr-open-lab"
chmod 700 "$HOME/.local/share/xmqr-open-lab"
MQTT_MODE=open-lab \
MQTT_BIND=127.0.0.1:1883 \
MQTT_STATE_DIR="$HOME/.local/share/xmqr-open-lab" \
RUST_LOG=info \
"$CARGO_TARGET_DIR/release/mqtt-broker"
```

Terminal 2 — assinante:

```bash
"$CARGO_TARGET_DIR/release/mqtt-client" sub \
  --open-lab --topic 'aula/mensagem' \
  --host 127.0.0.1 --port 1883 \
  --client-id 'aluno-sub' --qos 0
```

Terminal 3 — publicador:

```bash
"$CARGO_TARGET_DIR/release/mqtt-client" pub \
  --open-lab --topic 'aula/mensagem' \
  --message 'Olá, XMQR!' \
  --host 127.0.0.1 --port 1883 \
  --client-id 'aluno-pub' --qos 0
```

O assinante deve imprimir `Olá, XMQR!`. Pressione `Ctrl+C` no assinante e no
broker para encerrar. Veja o
[roteiro completo](docs/laboratorio-mqtt-aberto.md).

## Modo seguro

Sem `MQTT_MODE`, o broker seleciona `secure-mtls`, que exige TLS/mTLS,
certificado do cliente, usuário/senha e ACL deny-by-default. Consulte:

- [Transporte seguro](docs/security/secure-transport.md)
- [Autenticação e ACL](docs/security/auth-acl.md)
- [Cliente manual](docs/mqtt-client.md)
- [Persistência](docs/architecture/persistence.md)

## Desenvolvimento

```bash
cargo fmt --all -- --check
cargo test --locked
cargo clippy --locked --all-targets -- -D warnings
```

O projeto segue as especificações OASIS como fonte normativa. Mudanças de
protocolo devem registrar as cláusulas afetadas nos testes quando aplicável.

## Versões

Tags `vX.Y.Z` identificam snapshots imutáveis. A branch `release/0.3` recebe
somente correções compatíveis da série; `main` aponta para a versão experimental
mais recente. Consulte [VERSIONING.md](VERSIONING.md) e
[CHANGELOG.md](CHANGELOG.md).

## Licença

A licença será adicionada antes da publicação pública da tag `v0.3.0`.
