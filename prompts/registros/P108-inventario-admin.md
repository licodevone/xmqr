# P108 — inventário administrativo parcial

- Prompt: [P108 rev1](../broker/108-sessoes-retained-admin.md).
- Entrada: broker `7c25e3f`, admin CLI `01565ec`, Ubuntu 26.04/WSL.
- Implementação: `sessions_list` (máx. 16) e `retained_list` (máx. 8) pelo socket local operator, cursor lexical, sem payload. O ator lê o estado em memória; admin independente acrescenta `channel sessions|retained`.
- Gates broker: `cargo test --locked -q --lib` 118 PASS/6 ignored, fmt e Clippy PASS, build bins PASS, `verify_admin_channel.py` PASS. Gates admin após rev2: 21 unitários/6 integrações, Clippy, release build e integração `CHANNEL_CLI_PASS` com processo isolado.
- Negativos: viewer proibido, limite excessivo recusado, paginação por cursor sem duplicata e resposta sem payload. Os inventários não são snapshot atômico entre páginas.
- Estado: A07/A09 parcial. Ações auditadas, falhas de storage/concorrência e auditoria de longo prazo ainda pendentes. Nenhuma release nesta fatia.
