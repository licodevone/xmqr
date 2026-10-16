# P116 — execução da assinatura MQTT 5 inicial

- Prompt: [P116 rev1–2](../broker/116-assinatura-mqtt5-inicial.md), criado antes do código. Entrada `502f7b1`, 0.15.0.
- Implementado: decoder SUBSCRIBE5 com propriedades vazias, packet ID e opções padrão QoS0/1; SUBACK5 por filtro; entrega PUBLISH5 viva/retained e PUBACK QoS1. MQTT3.1.1 preservado. Sem alteração do documento durável.
- Ubuntu26/WSL: `cargo fmt --all -- --check` PASS; `cargo test --locked` PASS (132 testes de biblioteca, 6 ignored, integrações); `cargo clippy --locked --all-targets -- -D warnings` PASS; `cargo build --locked --bins` PASS.
- Integração real: `scripts/verify_mqtt5_cross.py` PASS nas duas direções, incluindo retained/QoS1; `scripts/verify_interop.py` PASS (6 casos, Mosquitto mqttv5 como assinante e publicador).
- Negativos: zero packet ID, propriedade/No Local/QoS2/payload vazio recusados em teste de codec. Rev2 corrigiu aceitação inicial de QoS2 antes do roteador; suíte repetida.
- Aceite local PASS para este subconjunto. CI do commit remoto será registrada separadamente; fase6A integral permanece aberta.
