# P208 — flags reservadas nos ACKs QoS MQTT 5

- [Prompt P208](../broker/208-qos-ack-fixed-header-flags-mqtt5.md) enviado antes do código (`e8ceb53`). Implementação e CI da fonte exata `6f0cf7fb967c42fb6f1c296ce8ef3642b0bcddb9`.
- PUBACK `0x41`–`0x4f`, PUBREC `0x51`–`0x5f` e PUBCOMP `0x71`–`0x7f` recebem DISCONNECT `0x81` antes de interpretar o corpo; os cabeçalhos válidos e PUBREL/P200 permanecem. MQTT 3.1.1 fecha sem novo DISCONNECT MQTT 5.
- Unitário cobre 45 cabeçalhos, corpo vazio/inválido, válidos e MQTT 3.1.1. TCP real `P208_QOS_ACK_FLAGS_PASS` cobre limites de cada tipo, Will, fechamento e conexão saudável. Regressões P200/P205/P207 PASS. Ubuntu 26.04/WSL: 222 testes de biblioteca PASS, seis campanhas ignoradas explicitamente; fmt, Clippy `-D warnings`, build release, inventário de licenças e seis contratos de distribuição PASS.
- [CI da fonte exata](https://github.com/licodevone/xmqr/actions/runs/39111635790) PASS nos jobs `rust` e `ubuntu-package`, incluindo a nova fixture. Sem tag/release isolada; broker publicado 0.37.0 ainda não inclui P208. Fases globais 6A–6D/7–9 abertas.
- Referência: [OASIS MQTT 5, §2.1.3 e §4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html).
