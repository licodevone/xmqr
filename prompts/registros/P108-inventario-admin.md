# P108 — inventário administrativo parcial

- Prompt: [P108 rev1–3](../broker/108-sessoes-retained-admin.md).
- Entrada: broker `7c25e3f`, admin CLI `01565ec`, Ubuntu 26.04/WSL.
- Implementação: `sessions_list` (máx. 16) e `retained_list` (máx. 8) pelo socket local operator, cursor lexical, sem payload. O ator lê o estado em memória; admin independente acrescenta `channel sessions|retained`.
- Gates broker: `cargo test --locked -q --lib` 118 PASS/6 ignored, fmt e Clippy PASS, build bins PASS, `verify_admin_channel.py` PASS. Gates admin após rev2: 21 unitários/6 integrações, Clippy, release build e integração `CHANNEL_CLI_PASS` com processo isolado.
- Negativos: viewer proibido, limite excessivo recusado, paginação por cursor sem duplicata e resposta sem payload. Os inventários não são snapshot atômico entre páginas.
- Rev2–3: `retained_delete` e `session_disconnect` usam ator/recibo no mesmo commit; documento MQTT v4 lê v1/v2/v3 e recibo v3 legado. Testes de unidade incluem restart, conflito/not_found, falha WAL, Will e inbound QoS2. Integração broker/admin com MQTT real confirmou retained antes/depois, conexão encerrada, Will retained, QoS2 preservado e replay de ambas ações após restart (`CHANNEL_CLI_PASS`).
- Estado: A07 aceito no recorte local; A09/global ainda abertos por consulta/retenção de auditoria, concorrência, B13/A08 e aceite conjunto. Nenhuma release nesta fatia.
