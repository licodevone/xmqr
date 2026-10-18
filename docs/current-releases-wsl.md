# Versões publicadas e instalação no WSL

Fotografia verificada em 2026-10-18. As três releases abaixo são experimentais para Ubuntu 26.04 amd64; cada repositório tem sua própria numeração.

| Sistema | Versão | Pacote `.deb` | Comando de versão | Release |
| --- | --- | --- | --- | --- |
| Broker | 0.40.0 | `xmqr-broker_0.40.0-1_amd64.deb` | `mqtt-broker --version` | [xmqr v0.40.0](https://github.com/licodevone/xmqr/releases/tag/v0.40.0) |
| Client | 0.33.0 | `xmqr-client_0.33.0-1_amd64.deb` | `mqtt-client --version` | [xmqr-client v0.33.0](https://github.com/licodevone/xmqr-client/releases/tag/v0.33.0) |
| Admin independente | 0.10.0 | `xmqr-admin_0.10.0-1_amd64.deb` | `xmqr-admin --version` | [xmqr-admin v0.10.0](https://github.com/licodevone/xmqr-admin/releases/tag/v0.10.0) |

O pacote do broker inclui também o comando legado `mqtt-admin`. Ele é diferente do programa `xmqr-admin` independente. Os hashes SHA-256 dos `.deb`, respectivamente, são:

```text
4a7421366f6a55367b36b38827b834b71e22f57ec59ef1a8b089d6ee7684450d  xmqr-broker_0.40.0-1_amd64.deb
c26d553f3e5b647762ef171e4154eba97e9ba894ddaea50495589b57987ac820  xmqr-client_0.33.0-1_amd64.deb
1d5d50adbac415a84aead1bcb8c0d4630f587970c4d77cbf930dbd4a714e9f7c  xmqr-admin_0.10.0-1_amd64.deb
```

Baixe os três `.deb` e seus `.sha256` pelas páginas de release. Na distribuição Ubuntu 26.04 do WSL, dentro da pasta de downloads, confirme `dpkg --print-architecture` como `amd64` e execute:

```sh
sha256sum -c xmqr-broker_0.40.0-1_amd64.deb.sha256
sha256sum -c xmqr-client_0.33.0-1_amd64.deb.sha256
sha256sum -c xmqr-admin_0.10.0-1_amd64.deb.sha256
sudo apt install ./xmqr-broker_0.40.0-1_amd64.deb ./xmqr-client_0.33.0-1_amd64.deb ./xmqr-admin_0.10.0-1_amd64.deb
mqtt-broker --version
mqtt-client --version
xmqr-admin --version
```

O `--version` do broker funciona sem `MQTT_STATE_DIR`. Instalar o broker não inicia o serviço; antes de habilitá-lo, configure `/etc/xmqr/broker.env` e os arquivos de segurança conforme [Ubuntu/systemd](ubuntu-systemd.md). Para upgrade, confirme compatibilidade do estado e backup no guia de cada release.

O [plano de evolução](evolution-plan.md) registra as fases 1–5 aceitas no escopo delimitado. As fases 6A–6D acumulam entregas parciais de MQTT 5, mas os critérios globais ainda estão abertos. A fase 7 tem WS de laboratório e WSS mTLS em loopback no broker/client; navegador e acesso remoto seguem abertos. As fases 8 (bridge) e 9 (Windows nativo) também. P212 integra o broker 0.40.0 e C114 o client 0.33.0; isso não equivale a MQTT 5 integral ou homologação para produção.
