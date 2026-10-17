# P171 — motivos de conclusão QoS 2 MQTT 5 aceitos parcialmente

O [prompt P171](../broker/171-qos2-completion-reasons-mqtt5.md) foi commitado antes do código (`3055176`). A primeira CI da fonte `25c980d` não iniciou por recuo inválido no workflow; o prompt foi revisto e commitado (`40db47d`) antes da correção (`53d70c9`). A fonte corrigida `53d70c93ce273ff0f7d04a1299b80482ed701a6c` passou na [CI](https://github.com/licodevone/xmqr/actions/runs/39024661424), com jobs Rust e pacote Ubuntu 26.04, incluindo interop Mosquitto/Paho e TCP P169/P170/P171.

Localmente: 199 testes de biblioteca PASS/6 ignorados, demais alvos PASS, fmt, Clippy, build release, inventário de licenças e 6 contratos de distribuição PASS. O YAML corrigido passou validação sintática. `scripts/verify_mqtt5_qos2_completion_reasons.py` retornou `P171_QOS2_COMPLETION_PASS`: PUBREL `0x92` recebeu PUBCOMP, PUBCOMP `0x92` concluiu saída, a próxima entrega QoS2 funcionou e não houve replay após restart.

PUBREL/PUBCOMP MQTT 5 aceitam `0x00` ou `0x92`, Reason String única e User Property repetida; ID zero, códigos/propriedades inválidos, duplicata, truncamento e extensões MQTT 3.1.1 são recusados. O broker registra apenas o motivo `0x92`. Nenhuma migração de estado nem tag/release isolada. A matriz normativa completa e os aceites globais 6A/6C permanecem abertos.
