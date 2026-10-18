# P224 — contrato QoS 1 da bridge

- [Prompt P224](../broker/224-bridge-qos1-contract.md) foi publicado antes da implementação (`fdf87e1`). O broker 0.42.0 não foi alterado; o sidecar do client implementou [C126](../../../xmqr-client/prompts/registros/C126-bridge-qos1-manual-ack.md).
- [CI C126 exata](https://github.com/licodevone/xmqr-client/actions/runs/39129588351) PASS nos três jobs, inclusive testes com brokers XMQR reais e Mosquitto 2.0.22 em ambas as direções de topologia, QoS 0/1. A fixture de dois XMQR cobre atualização/replay retained e redelivery após crash da bridge no intervalo entre PUBACK destino e ACK origem.
- Entrega parcial: MQTT 3.1.1 QoS 1 at-least-once, sem entrega única, sem protocolo de commit externo e sem loop guard entre instâncias. Sidecar ainda fora do `.deb`/Docker. Fase 8 continua `[ ]`.
