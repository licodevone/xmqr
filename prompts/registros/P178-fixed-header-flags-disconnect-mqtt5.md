# P178 — flags fixas inválidas recebem DISCONNECT `0x82` parcialmente

O [prompt P178](../broker/178-fixed-header-flags-disconnect-mqtt5.md) foi commitado antes do código (`6b4656b`). O primeiro gate parou em formatação de uma asserção, antes dos testes; a revisão do prompt (`3d27f81`) antecedeu a correção. Fonte exata `dad01e4ca1aa9c780d5ee52c324af38fa3ce660f`: 200 testes de biblioteca PASS/6 ignorados, demais alvos, fmt, Clippy, build debug, inventário de licenças, 6 contratos de distribuição e regressão TCP P175–P178 PASS localmente. [CI PASS](https://github.com/licodevone/xmqr/actions/runs/39027294609) nos jobs Rust e pacote Ubuntu 26.04, incluindo o teste TCP.

PINGREQ `c1 00` e DISCONNECT `e1 00` após CONNACK MQTT 5 produzem `e0 02 82 00` e fechamento. `scripts/verify_mqtt5_fixed_header_flags_disconnect.py` retornou `P178_FIXED_HEADER_FLAGS_PASS`: não houve PINGRESP, Will foi publicado em ambos os casos e MQTT 3.1.1 apenas fechou. Falhas de tamanho, alias, Remaining Length, I/O e timeout permanecem classificadas separadamente.

Sem migração nem tag isolada. Outros erros de protocolo e aceites globais 6A–6D continuam abertos.
