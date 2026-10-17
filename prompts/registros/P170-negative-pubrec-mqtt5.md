# P170 — PUBREC negativo MQTT 5 aceito parcialmente

O [prompt P170](../broker/170-negative-pubrec-mqtt5.md) foi commitado antes da funcionalidade (`549b9c6`). Fonte exata `ec6aca0c6fba103be417f493a0880c9257066101`: 199 testes de biblioteca PASS/6 ignorados, demais alvos, fmt, Clippy, build release, inventário de licenças e 6 contratos de distribuição PASS localmente; [CI PASS](https://github.com/licodevone/xmqr/actions/runs/39024240051), incluindo os gates TCP e pacote Ubuntu 26.04.

PUBREC recebido do client MQTT 5 aceita `0x00`, `0x80`, `0x83`, `0x87`, `0x90`, `0x91`, `0x97` ou `0x99`, Reason String única e User Property repetida; recusa `0x10` exclusivo do servidor, códigos/propriedades inválidos, duplicata e truncamento. Motivo negativo remove a tentativa QoS2 durável e libera quota/Packet Identifier sem emitir PUBREL; o motivo é registrado sem payload. `scripts/verify_mqtt5_negative_pubrec.py` retornou `P170_NEGATIVE_PUBREC_PASS`: a conexão seguiu recebendo, o fluxo QoS2 seguinte concluiu e não houve replay após restart. O teste do ator confirma que uma vaga Receive Maximum=1 é liberada. MQTT 3.1.1 e PUBREC de sucesso mantêm a semântica anterior.

Sem migração nem tag/release isolada. Redistribuição de grupo compartilhado não foi prometida; PUBREL/PUBCOMP negativos e aceites globais 6A/6C continuam abertos.
