# P119 — PUBACK MQTT 5 com motivo de recusa ACL

- Prompt: [P119 rev1–2](../broker/119-puback-mqtt5-acl.md), criado antes do código. Entrada `14f060b`, 0.16.0.
- Implementado: publicação QoS 1 negada pela ACL retorna PUBACK MQTT 5 `0x87` com comprimento de propriedades zero, sem chamar o roteador; a conexão pode publicar em tópico permitido depois. MQTT 3.1.1 continua encerrando a conexão. Formato durável e versão não mudam.
- Ubuntu26/WSL: `cargo fmt --all -- --check` PASS; `cargo test --locked` PASS (133 testes da biblioteca, 6 ignored, demais integrações PASS); `cargo clippy --locked --all-targets -- -D warnings` PASS; `cargo build --locked --bins` PASS; `scripts/verify_interop.py` PASS (6 casos Mosquitto).
- Negativo real: `mqtt5_acl_denial_reports_puback_reason_without_committing` PASS para `0x87`, contagem de commits sem mudança, publicação posterior aceita e recusa 3.1.1 por fechamento. `xmqr-client/scripts/verify_mqtt5_acl_reason.py` PASS com broker/client reais em loopback e arquivos temporários, incluindo SUBACK negado.
- Primeira rodada Clippy FAIL por teste com 103 linhas; rev2 extraiu helper de CONNECT autenticado, gates repetidos PASS. CI do commit: PENDING até publicação no GitHub.
- Compatibilidade: MQTT 5 QoS 0 negado ainda fecha; reason string/propriedades adicionais, QoS2 e conformidade MQTT 5 integral seguem pendentes. Sem tag/release isolada.
