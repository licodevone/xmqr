# P174 — motivos de DISCONNECT do client MQTT 5 aceitos parcialmente

O [prompt P174](../broker/174-client-disconnect-reasons-mqtt5.md) foi commitado antes da funcionalidade (`79a6d9a`). Fonte exata `c43c72ce1de5ae9bb1a73a3c88f7dc1b0aa596bf`: 200 testes de biblioteca PASS/6 ignorados, demais alvos, fmt, Clippy, build release, inventário de licenças e 6 contratos de distribuição PASS localmente. [CI PASS](https://github.com/licodevone/xmqr/actions/runs/39025865690) nos jobs Rust e pacote Ubuntu 26.04, incluindo Mosquitto/Paho e testes TCP P169–P174.

O broker reconhece os motivos de DISCONNECT enviados pelo client da tabela 3-10 (`0x00`, `0x04`, `0x80`–`0x83`, `0x90`, `0x93`–`0x99`). Só `0x00` cancela o Will; os demais seguem a transição durável com Will, se presente. Códigos indefinidos e exclusivos do servidor são recusados; MQTT 3.1.1 continua sem extensões. `scripts/verify_mqtt5_client_disconnect_reasons.py` retornou `P174_CLIENT_DISCONNECT_PASS`: `0x80` publicou Will, `0x93` atrasado foi publicado após restart, e o servidor encerrou as conexões. O log contém apenas o código.

Sem migração ou tag/release isolada. Emissão dos demais motivos pelo servidor e aceites globais 6A/6B continuam abertos.
