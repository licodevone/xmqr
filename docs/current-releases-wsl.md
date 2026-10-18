# Versões publicadas e instalação no WSL

Fotografia verificada em 2026-10-18. As três releases abaixo são experimentais para Ubuntu 26.04 amd64; cada repositório tem sua própria numeração.

| Sistema | Versão | Pacote `.deb` | Comando de versão | Release |
| --- | --- | --- | --- | --- |
| Broker | 0.39.0 | `xmqr-broker_0.39.0-1_amd64.deb` | `mqtt-broker --version` | [xmqr v0.39.0](https://github.com/licodevone/xmqr/releases/tag/v0.39.0) |
| Client | 0.32.0 | `xmqr-client_0.32.0-1_amd64.deb` | `mqtt-client --version` | [xmqr-client v0.32.0](https://github.com/licodevone/xmqr-client/releases/tag/v0.32.0) |
| Admin independente | 0.10.0 | `xmqr-admin_0.10.0-1_amd64.deb` | `xmqr-admin --version` | [xmqr-admin v0.10.0](https://github.com/licodevone/xmqr-admin/releases/tag/v0.10.0) |

O pacote do broker inclui também o comando legado `mqtt-admin`. Ele é diferente do programa `xmqr-admin` independente. Os hashes SHA-256 dos `.deb`, respectivamente, são:

```text
b076e728dd00af4b74546974857714eab0137621dfdc3944eea481a9a2f45b26  xmqr-broker_0.39.0-1_amd64.deb
634c9d558acb610697d2bd222dab2c557f7f84bf4c2280e1748369e15e581d62  xmqr-client_0.32.0-1_amd64.deb
1d5d50adbac415a84aead1bcb8c0d4630f587970c4d77cbf930dbd4a714e9f7c  xmqr-admin_0.10.0-1_amd64.deb
```

Baixe os três `.deb` e seus `.sha256` pelas páginas de release. Na distribuição Ubuntu 26.04 do WSL, dentro da pasta de downloads, confirme `dpkg --print-architecture` como `amd64` e execute:

```sh
sha256sum -c xmqr-broker_0.39.0-1_amd64.deb.sha256
sha256sum -c xmqr-client_0.32.0-1_amd64.deb.sha256
sha256sum -c xmqr-admin_0.10.0-1_amd64.deb.sha256
sudo apt install ./xmqr-broker_0.39.0-1_amd64.deb ./xmqr-client_0.32.0-1_amd64.deb ./xmqr-admin_0.10.0-1_amd64.deb
mqtt-broker --version
mqtt-client --version
xmqr-admin --version
```

O `--version` do broker funciona sem `MQTT_STATE_DIR`. Instalar o broker não inicia o serviço; antes de habilitá-lo, configure `/etc/xmqr/broker.env` e os arquivos de segurança conforme [Ubuntu/systemd](ubuntu-systemd.md). Para upgrade, confirme compatibilidade do estado e backup no guia de cada release.

O [plano de evolução](evolution-plan.md) registra as fases 1–5 aceitas no escopo delimitado. As fases 6A–6D acumulam entregas parciais de MQTT 5, mas os critérios globais ainda estão abertos. A fase 7 tem WS local no broker/client, mas WSS, navegador e acesso remoto seguem abertos; fases 8 (bridge) e 9 (Windows nativo) também. P210 integra o broker 0.39.0 e C112 o client 0.32.0; isso não equivale a MQTT 5 integral ou homologação para produção.
