# P107 rev4–5 — primeiro reload online

- Pedido: continuar a fase 5 nos três sistemas; prompt P107 preparado antes da implementação.
- Data/ambiente: 2026-10-15, Ubuntu 26.04 em WSL, broker 0.14.0, base `d243672`.
- Escopo: socket local existente recebe `reload` do operator e `receipt` de ambos os papéis; hash do bundle, CAS, ID de 128 bits, recibo auditável no mesmo commit da reconciliação. SIGHUP legado preservado.
- Estado: documento MQTT v3 lê v1/v2; 128 recibos sem evicção. O binário 0.14.0 não lê v3: backup offline prévio é necessário para rollback. Não houve migração de estado real.
- Gates executados: `cargo fmt --all -- --check` PASS; `cargo test --locked -q` PASS (117 testes de biblioteca, 6 ignorados, integrações); `cargo clippy --locked --all-targets -- -D warnings` PASS; `cargo build --locked --bins` PASS; `python3 scripts/verify_admin_channel.py --broker target/debug/mqtt-broker` PASS (`ADMIN_CHANNEL_RELOAD_PASS`). Teste v1/v2→v3 adicional PASS.
- Negativos reais: viewer não muta, token errado, ID conflitante, geração obsoleta, request grande, política estática e restart com deduplicação. Teste unitário cobre recibo/restart. Não foram simuladas perda de energia, concorrência saturada ou falha de auditoria em disco.
- Aceite: incremento de reload PASS; A09 global e fase 5 permanecem abertos até integração com admin, sessões/retained e campanha de falhas. Nenhuma release nesta fatia parcial.
