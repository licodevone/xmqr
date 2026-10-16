# P122 — QoS 2 MQTT 5

- Prompt [P122 rev1–3](../broker/122-qos2-mqtt5.md) criado antes da funcionalidade. Entrada `85c915b`, versão publicada 0.16.0 preservada.
- Codec aceita PUBLISH/SUBSCRIBE QoS2 sem propriedades avançadas e os ACKs PUBREC/PUBREL/PUBCOMP de sucesso com identificador. CONNACK omite Maximum QoS (padrão normativo 2) e mantém Maximum Packet Size 65536. ACL negada responde PUBREC `0x87` sem commit; MQTT 3.1.1 permanece compatível.
- Ubuntu26/WSL: vetores de codec, negativo ACL/sem commit e entrega cruzada QoS2→assinante MQTT 3.1.1 PASS. `cargo fmt --all -- --check`, `cargo test --locked`, `cargo clippy --locked --all-targets -- -D warnings` e `cargo build --locked --bins` PASS. Primeira suíte completa encontrou vetor antigo que exigia recusa de SUBSCRIBE QoS2; prompt rev3 corrigiu a expectativa e o gate foi repetido com PASS.
- Integração real com C63 via `scripts/verify_mqtt5_acl_reason.py` PASS: QoS2 nas duas direções, recusa PUBREC e encerramento por UNSUBACK. Interop com Mosquitto 2.0.22 MQTT5 QoS2 nas duas direções PASS, usando IDs e credenciais isolados de teste.
- [CI do commit funcional `c993bfc`](https://github.com/licodevone/xmqr/actions/runs/38974169685) PASS, incluindo Rust, interop e pacote Ubuntu26. Sem tag/release isolada; fases 6A–6D permanecem abertas.
