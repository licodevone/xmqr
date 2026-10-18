# P214 — WSS mTLS remoto com opt-in explícito

- [Prompt P214](../broker/214-remote-wss-mtls-bind.md) foi enviado antes do código (`a3f05e7`). Implementação: `4ea70b0`. CI da fonte funcional [39119941550](https://github.com/licodevone/xmqr/actions/runs/39119941550): Rust e pacote Ubuntu 26.04 PASS.
- `MQTT_WSS_REMOTE_ENABLED=true` ou `[broker].wss_remote_enabled=true` autoriza bind WSS fora de loopback somente no perfil `secure-mtls`; a opção sem bind, valor inválido e combinações de bind inseguras são recusadas. mTLS, ACL, quota, router, rotação TLS e recusa de `Origin` permanecem.
- Suíte, fmt, Clippy, licenças, distribuição e fixture local P212 PASS. Integração descartável com client C117 por WSS remoto MQTT 3.1.1/5, perfil, TCP, restart e negativos de opt-in, CA, SAN, senha e ACL: `DOCKER_MTLS_PUB_SUB_RESTART_NEGATIVES_PASS P214_C117_REMOTE_WSS_PASS`.
- Os primeiros gates locais encontraram complexidade Clippy e uma asserção do verificador Docker sobre texto JSONL; ambos foram corrigidos e os gates completos repetidos PASS. Aceite parcial da fase 7; navegador/política de origem e matriz completa ainda abertos. A versão 0.40.0 publicada não contém P214.
