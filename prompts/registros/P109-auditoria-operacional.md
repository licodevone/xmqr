# P109 — auditoria consultável e métricas administrativas

- Prompt: [P109 rev1](../broker/109-auditoria-operacional.md).
- Entrada: broker `9b4b9fe`, documento MQTT v4 com recibos duráveis; admin `3253c72`.
- Entrega: `audit_list` operator com cursor numérico e até 16 itens; CLI `channel audit`; cada item contém ID, timestamp, UID, operação, resultado, hash do alvo e gerações, sem payload ou identificação do alvo. Monitor P43 recebe counters de mutações committed/replayed/refused e gauge de recibos, sem labels dinâmicos.
- Validação: Rust fmt/test/Clippy e integração broker/admin `CHANNEL_CLI_PASS` com viewer negado, duas páginas, dados sensíveis ausentes e `/metrics` confirmando três commits/recibos reais. Os contadores representam ações processadas pelo ator; parser/autenticação recusados antes da fila não contam como mutação recusada.
- Limite: recibos append-only até 128, sem descarte. Novas mutações falham fechado ao encher; política segura de rotação/arquivamento ainda pendente, portanto A05 e fase 5 global continuam abertos. Não houve release nesta fatia.
