# Versões publicadas e instalação no WSL

Fotografia verificada em 19 de outubro de 2026. As três releases são experimentais para Ubuntu 26.04 amd64 e têm numeração independente.

| Sistema | Versão | Pacote `.deb` | Comando de versão | Release |
| --- | --- | --- | --- | --- |
| Broker | 0.43.0 | `xmqr-broker_0.43.0-1_amd64.deb` | `mqtt-broker --version` | [xmqr v0.43.0](https://github.com/licodevone/xmqr/releases/tag/v0.43.0) |
| Client / bridge | 0.43.0 / 0.5.0 | `xmqr-client_0.43.0-1_amd64.deb` | `mqtt-client --version`; `mqtt-bridge --version` | [xmqr-client v0.43.0](https://github.com/licodevone/xmqr-client/releases/tag/v0.43.0) |
| Admin independente | 0.11.0 | `xmqr-admin_0.11.0-1_amd64.deb` | `xmqr-admin --version` | [xmqr-admin v0.11.0](https://github.com/licodevone/xmqr-admin/releases/tag/v0.11.0) |

O pacote do broker também instala o comando legado `mqtt-admin` versão 0.43.0. Ele é diferente do programa independente `xmqr-admin`. SHA-256 dos pacotes publicados:

```text
c2341ab3a341b1854e85ebb2f0bec9535968374b226a12a60cee58aa7cef3d4e  xmqr-broker_0.43.0-1_amd64.deb
e4d09cec660a0dba20790181727b17c44040913425a3340d3838e45113241f76  xmqr-client_0.43.0-1_amd64.deb
fe03ffc858e7583e7d8ce6808b4f56495c688beb69d47870db7fe0c1b8b55469  xmqr-admin_0.11.0-1_amd64.deb
```

Baixe cada `.deb` e seu `.sha256` na respectiva página de release. No Ubuntu 26.04 do WSL, dentro da pasta de downloads, confirme `dpkg --print-architecture` como `amd64` e execute:

```sh
sha256sum -c xmqr-broker_0.43.0-1_amd64.deb.sha256
sha256sum -c xmqr-client_0.43.0-1_amd64.deb.sha256
sha256sum -c xmqr-admin_0.11.0-1_amd64.deb.sha256
sudo apt install ./xmqr-broker_0.43.0-1_amd64.deb ./xmqr-client_0.43.0-1_amd64.deb ./xmqr-admin_0.11.0-1_amd64.deb
mqtt-broker --version
mqtt-client --version
mqtt-bridge --version
xmqr-admin --version
```

O `--version` do broker funciona sem `MQTT_STATE_DIR`. A instalação não inicia automaticamente o serviço; antes de habilitá-lo, configure `/etc/xmqr/broker.env` e os arquivos de segurança conforme [Ubuntu/systemd](ubuntu-systemd.md).

**Upgrade do broker 0.42.0 para 0.43.0:** preserve um backup privado do estado v15 antes da primeira inicialização da 0.43.0. A nova versão grava estado v16; o binário 0.42.0 recusa esse estado. Para rollback executável, restaure o backup v15 em diretório novo com o broker parado. O ciclo em container Ubuntu 26.04 passou; veja a [nota da release](releases/0.43.0.md) e o [aceite da fase 6](phase6-acceptance.md).

**Migração e rollback do client0.43.0:** o modo MQTT5 nas duas pontas exige diretório/IDs novos para journalformato2 após drenar a rota antiga. Draftv2MQTT5→3.1.1 exige `legacy_metadata_policy="drop"`; v1 mantém seu contrato. Para voltar a0.42.1, drene/pare o modo novo e preserve seu journal; retome apenas configuração/estado anteriores compatíveis. Obrigações pendentes/Refused exigem análise offline, sem apagar estado. O ciclo descartável de pacote passou; nenhuma atualização foi aplicada à instalação do operador. [Guia e limites](https://github.com/licodevone/xmqr-client/blob/main/docs/bridge-mqtt5.md).

O [plano de evolução](evolution-plan.md) registra fases1–8 aceitas em seus contratos finitos, incluindo [MQTT5/fase6](phase6-acceptance.md), [WS/WSS/fase7](phase7-acceptance.md) e [bridge/fase8](phase8-acceptance.md). Certificação integralMQTT5, produção e cluster têm critérios próprios; fase9/Windows permanece planejada.

A fonte A23–A25 do admin acrescentou console, contas e indicadores depois da release0.11.0. Esse pacote não contém automaticamente os incrementos posteriores: confira caminho/commit do executável além de `--version`. O admin0.11.0 é compatível com o core/estado16 do broker0.43.0.
