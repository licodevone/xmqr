# Ubuntu 26.04 / WSL: pacote e systemd

Alvo inicial: Ubuntu 26.04 amd64 com systemd. No Windows, use a distribuição
WSL Ubuntu-26.04. A inicialização automática ocorre quando essa distribuição
inicia, não significa que o Windows a iniciará automaticamente.

## Construir e instalar

Com Rust, Python3, dpkg-dev e ferramentas nativas de build disponíveis:

```sh
python3 scripts/build_deb.py
sudo apt install ./dist/xmqr-broker_0.10.0-1_amd64.deb
```

O pacote contém `/usr/bin/mqtt-broker`, `/usr/bin/mqtt-admin`, unit systemd,
licenças e `/etc/xmqr/broker.env` registrado como conffile. Dependências ABI
são derivadas dos binários por dpkg-shlibdeps. Compile no Ubuntu26; binários
Windows ou de outra distribuição não servem como entrada comprovada.

O usuário `xmqr` é criado sem login. `/var/lib/xmqr` é privado e pertence a ele.
Instalação não habilita/inicia o serviço. Prepare certificados, chave e bundle
dinâmico conforme [segurança dinâmica](security/dynamic-security.md), ajuste
`broker.env` e valide CA/SAN. Bundle e chave privados: proprietário xmqr,
modo0600; nunca forneça segredos no Git ou na linha de comando.

```sh
sudo systemctl enable --now xmqr-broker.service
systemctl status xmqr-broker.service
journalctl -u xmqr-broker.service -f
sudo systemctl restart xmqr-broker.service
sudo systemctl stop xmqr-broker.service
```

SIGTERM/SIGINT fecham o listener, processam comandos anteriores à barreira de
parada, publicam Wills duravelmente para sessões offline, preservam sessões
persistentes/inboundQoS2, sincronizam snapshot e encerram o writer. Só um
DISCONNECT real do cliente cancela seu Will. Não há promessa de entrega aos
clientes transitórios durante a parada. Timeout interno15s; systemd20s, com
SIGKILL como último recurso. Falhas de persistência não são anunciadas como
parada durável bem-sucedida. Não há sd_notify/Watchdog; active não prova ready.

`systemctl reload xmqr-broker` envia SIGHUP: só o bundle dinâmico é recarregado;
reload válido exige reautenticação de clientes. TLS, bind e env precisam de
restart. Para configuração legada sem bundle, não use reload.

## Atualização e remoção

`sudo apt install ./novo.deb` preserva conffiles editados conforme dpkg.
Upgrade para o serviço e não o reinicia automaticamente; revise configuração
e execute `systemctl start` depois. Backups exigem broker parado; execute admin
como xmqr para acessar estado privado. Um backup MQTT não inclui credenciais.

`sudo apt remove xmqr-broker` para e desabilita a unit, preservando estado e
configuração. `purge` remove conffiles fornecidos pelo pacote; estado MQTT,
certificados/bundles fornecidos pelo operador e usuário são preservados para
evitar destruição de dados. Exclua esses itens só por decisão administrativa.

## Distribuição

GitHub prerelease fornece `.deb` e SHA-256. Instalar deb local via apt resolve
dependências. Ainda não há repositório APT próprio: `apt install xmqr-broker`
sem caminho exige configurar um repositório assinado futuro. Não há validação
Ubuntu24, arm64, MSRV1.88 exato nem prontidão de produção nesta etapa.

Referências: [systemd.service](https://github.com/systemd/systemd/blob/main/man/systemd.service.xml),
[conffiles Debian](https://www.debian.org/doc/debian-policy/ap-pkg-conffiles.html),
[Will MQTT3.1.1 §3.1.2.5](https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html).
