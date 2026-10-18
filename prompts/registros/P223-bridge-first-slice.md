# P223 — contrato inicial da fase 8

- [Prompt P223](../broker/223-bridge-first-slice.md) foi publicado antes do sidecar (`c51abea`). [C125 no client](../../../xmqr-client/prompts/registros/C125-bridge-one-way-tls.md) implementou a primeira direção única TLS/mTLS. [CI C125](https://github.com/licodevone/xmqr-client/actions/runs/39128666957) passou nos três jobs, incluindo XMQR↔Mosquitto e XMQR↔XMQR.
- A escolha do sidecar mantém o broker 0.42.0 sem mudança de processo/estado. Não confundir um teste entre dois brokers com alta disponibilidade nem com a bridge T02 completa. QoS 0 melhor esforço, retained, persistência, loop guard e empacotamento precisam de fatias próprias. Fase 8 continua `[ ]`.
