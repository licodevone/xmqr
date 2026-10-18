# P225 — contrato de topologia sem ciclos

- [Prompt P225](../broker/225-bridge-topology-cycle-guard.md) foi publicado antes do código (`12428d8`). O sidecar do client implementou [C127](../../../xmqr-client/prompts/registros/C127-bridge-topology-cycle-guard.md); broker 0.42.0 não mudou.
- [CI exata C127](https://github.com/licodevone/xmqr-client/actions/runs/39130449630) PASS em três jobs. Cadeia real de duas bridges/três brokers TLS/mTLS entregue, com ciclos de dois/três links e prefixos sobrepostos recusados. QoS 0/1 e negativos TLS/ACL preservados.
- A prova cobre um manifesto completo compartilhado. MQTT 3.1.1 não transporta rastro de origem; outras bridges ou manifestos divergentes não são detectados. A fase 8 continua `[ ]`; C128 cuidará da distribuição experimental.
