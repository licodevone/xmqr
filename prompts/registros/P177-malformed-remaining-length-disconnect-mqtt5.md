# P177 — Remaining Length malformado recebe DISCONNECT `0x81` parcialmente

O [prompt P177](../broker/177-malformed-remaining-length-disconnect-mqtt5.md) foi commitado antes do código (`0fe499a`). Fonte exata `b99a7ddf3a99f5b77687d8c803dfbfab97316f55`: 200 testes de biblioteca PASS/6 ignorados, demais alvos, fmt, Clippy, build release, inventário de licenças e 6 contratos de distribuição PASS localmente. [CI PASS](https://github.com/licodevone/xmqr/actions/runs/39027155086) em Rust e pacote Ubuntu 26.04, incluindo o teste TCP.

Quatro bytes de Remaining Length com bit de continuação produzem erro tipado. Após CONNACK MQTT 5, o broker responde `e0 02 81 00` e fecha sem processar o corpo. O teste TCP `scripts/verify_mqtt5_malformed_length_disconnect.py` retornou `P177_MALFORMED_LENGTH_PASS`: cabeçalho parcial não fecha precocemente, Will é publicado após o erro e MQTT 3.1.1 fecha sem DISCONNECT MQTT 5. P175/P176 também passaram na regressão local.

Sem migração nem tag isolada. Outros pacotes malformados e os aceites globais 6A–6D continuam abertos.
