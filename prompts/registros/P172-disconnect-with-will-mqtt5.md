# P172 — DISCONNECT com Will MQTT 5 aceito parcialmente

O [prompt P172](../broker/172-disconnect-with-will-mqtt5.md) foi commitado antes do código (`64e3601`). O gate inicial de formatação falhou; a revisão do prompt (`51b41ff`) precedeu a correção. Fonte exata `cbd3c60899354538931bca3bf5c0fc7cc55b63ef`: 199 testes de biblioteca PASS/6 ignorados, demais alvos, fmt, Clippy, build release, inventário de licenças e 6 contratos de distribuição PASS localmente. [CI PASS](https://github.com/licodevone/xmqr/actions/runs/39025077171) nos jobs Rust e pacote Ubuntu 26.04, incluindo Mosquitto/Paho e teste TCP novo.

DISCONNECT do client MQTT 5 com `0x04` usa a transição durável de Will, inclusive Will Delay, expiração da sessão, ACL e recuperação. `0x00` continua cancelando o Will. Ambos aceitam Reason String única, User Property repetida e Session Expiry Interval válido; códigos/propriedades fora do recorte, duplicatas, truncamento e extensões em MQTT 3.1.1 são recusados. `scripts/verify_mqtt5_disconnect_with_will.py` retornou `P172_DISCONNECT_WITH_WILL_PASS` para Will solicitado, cancelamento normal e publicação atrasada após restart. Os gates existentes de Will Delay, Session Expiry e Mosquitto passaram novamente.

Sem migração de estado nem tag/release isolada. Outros motivos DISCONNECT e os aceites globais 6A/6B seguem abertos.
