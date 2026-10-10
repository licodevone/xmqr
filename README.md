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

O pacote publicado é experimental e destinado ao Ubuntu 26.04 **amd64**.
Ainda não há repositório APT próprio: baixe o `.deb` e instale-o com o APT.

1. No Windows, abra sua distribuição pelo PowerShell (confira o nome com
   `wsl --list --verbose`):

```powershell
wsl -d Ubuntu-26.04
```

2. Execute os próximos comandos **no terminal do Ubuntu**. Confirme a versão
   e a arquitetura; este pacote requer Ubuntu 26.04 e `amd64`:

```bash
cat /etc/os-release
dpkg --print-architecture
sudo apt update
sudo apt install -y wget ca-certificates
mkdir -p ~/xmqr-pacotes
cd ~/xmqr-pacotes
```

3. Baixe o pacote e seu checksum da release publicada:

```bash
wget -O xmqr-broker_0.10.0-1_amd64.deb https://github.com/licodevone/xmqr/releases/download/v0.10.0/xmqr-broker_0.10.0-1_amd64.deb
wget -O xmqr-broker_0.10.0-1_amd64.deb.sha256 https://github.com/licodevone/xmqr/releases/download/v0.10.0/xmqr-broker_0.10.0-1_amd64.deb.sha256
sha256sum -c xmqr-broker_0.10.0-1_amd64.deb.sha256
```

Prossiga somente se a verificação mostrar `OK`.

4. Instale e confirme o pacote e a conta de serviço:

```bash
sudo apt install ./xmqr-broker_0.10.0-1_amd64.deb
dpkg-query -W -f='${Status}\n' xmqr-broker
id xmqr
```

O resultado esperado é `install ok installed`. A instalação cria o usuário e
grupo `xmqr`; não é necessário criá-los manualmente. Se `dpkg-query` informar
que não encontrou o pacote, a instalação ainda não foi concluída.

5. Configure os certificados, credenciais e permissões conforme o
   [guia Ubuntu e systemd](docs/ubuntu-systemd.md),
   [transporte seguro](docs/security/secure-transport.md) e
   [administração de usuários](docs/administracao-usuarios.md).
   Revise `/etc/xmqr/broker.env` e instale os arquivos referenciados por ele:
   `server.crt`, `server.key`, `clients-ca.crt` e `security.toml` em `/etc/xmqr`.
   A chave privada e o bundle de segurança devem pertencer a `xmqr:xmqr`, com
   permissão `0600`. Não publique chaves privadas ou senhas no GitHub.

6. Após configurar TLS, usuários e ACL, habilite e inicie o serviço:

```bash
sudo systemctl enable --now xmqr-broker.service
systemctl status xmqr-broker.service
journalctl -u xmqr-broker.service -f
```

Use `Ctrl+C` para sair do acompanhamento dos logs. O pacote não inicia o broker
automaticamente. No WSL, o systemd deve estar habilitado; veja o guia acima.
O serviço habilitado inicia quando a distribuição Ubuntu é iniciada.

Para atualizar, baixe a nova versão, confira o checksum e repita a instalação
com `sudo apt install ./ARQUIVO.deb`. A atualização preserva configuração e
dados, mas para o serviço; revise a configuração e inicie-o novamente com
`sudo systemctl start xmqr-broker.service`.

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

## Publicação verificada

Prerelease atual: [v0.10.0](https://github.com/licodevone/xmqr/releases/tag/v0.10.0),
com debUbuntu26amd64 e checksum. CI Rust e pacote Ubuntu aprovados no
[GitHub Actions](https://github.com/licodevone/xmqr/actions/runs/38085647450).
