# P123 — propriedades informativas de CONNECT MQTT 5

- Prompt [P123 rev1](../broker/123-connect-properties-mqtt5.md) criado antes do código. Entrada `21162ec`, versão publicada 0.16.0 preservada.
- Codec aceita Request Problem Information `0x17`, Request Response Information `0x19`, Topic Alias Maximum `0x22` e User Property `0x26` repetível no CONNECT 5. Flags são 0/1 e únicas; pares UTF-8 são lidos integralmente. O broker não ecoa, persiste ou registra essas propriedades e não envia Topic Alias/Response Information. AUTH, Maximum Packet Size e expiração não-zero continuam fora do subconjunto.
- Ubuntu26/WSL: teste de codec e contrato TCP com conexão aceita, duplicatas, booleanos inválidos, UTF-8/truncamento e propriedade não suportada PASS; recusas não causaram commit. `cargo fmt --all -- --check`, `cargo test --locked`, `cargo clippy --locked --all-targets -- -D warnings` e `cargo build --locked --bins` PASS.
- Integração real com client C64 no harness `scripts/verify_mqtt5_acl_reason.py` PASS, incluindo pub/sub QoS1/2, ACL, UNSUBACK e Mosquitto 2.0.22. CI do commit funcional pendente após push.
- Sem mudança de documento durável, versão, tag ou instalação WSL do operador. Fase 6A permanece aberta.
