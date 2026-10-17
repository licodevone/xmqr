# P169 — PUBACK negativo MQTT 5 aceito parcialmente

O [prompt P169](../broker/169-negative-puback-mqtt5.md) foi commitado antes da funcionalidade (`a12d32f`). Fonte exata `eda78c5dfc6e7c0efdcf04ad50f82b06b1e45adf`: 197 testes de biblioteca PASS/6 ignorados, demais alvos, fmt, Clippy, build release, inventário de licenças e 6 contratos de distribuição PASS localmente; [CI PASS](https://github.com/licodevone/xmqr/actions/runs/39023837532), incluindo o gate TCP e pacote Ubuntu 26.04.

O parser aceita PUBACK do client MQTT 5 com `0x00`, `0x80`, `0x83`, `0x87`, `0x90`, `0x91`, `0x97` ou `0x99`, Reason String única e User Property repetida. Recusa `0x10` exclusivo do servidor, códigos desconhecidos, duplicata/truncamento e propriedades ilegais; MQTT 3.1.1 conserva o contrato anterior. PUBACK negativo conclui a tentativa QoS1 no ator, libera inflight/quota e registra só o código. `scripts/verify_mqtt5_negative_puback.py` retornou `P169_NEGATIVE_PUBACK_PASS`: outra publicação foi entregue na mesma conexão e o restart não repetiu a entrega rejeitada. Não se afirma que o assinante aceitou o payload; redistribuição de grupo compartilhado não foi prometida.

Sem migração nem tag/release isolada. PUBREC/PUBREL/PUBCOMP negativos e aceite global 6A/6C continuam abertos.
