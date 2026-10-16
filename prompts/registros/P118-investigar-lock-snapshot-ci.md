# P118 — investigação da reabertura após falha injetada

- Prompt: [P118 rev1](../broker/118-investigar-lock-snapshot-ci.md), criado antes de qualquer alteração funcional neste turno.
- Entrada: `main` `14f060b`, 0.16.0, Ubuntu 26.04/WSL sobre a mesma cópia Windows. A [CI tentativa 1](https://github.com/licodevone/xmqr/actions/runs/38952824693/attempts/1) falhou no teste `snapshot_boundary_failures_keep_all_previously_acknowledged_state`, reabertura de `Store` após `drop(store)` com `AlreadyOpen`.
- PASS: 30 execuções isoladas do teste na cópia local; PASS: `cargo test --locked` completo local; PASS: [rerun da CI tentativa 2](https://github.com/licodevone/xmqr/actions/runs/38952824693/attempts/2), jobs Rust e pacote Ubuntu26.
- Não houve reprodução nem causa identificada. Nenhum retry, mudança no lock ou relaxamento de asserção foi introduzido. A falha inicial permanece registrada como intermitente; se reaparecer, capturar ponto/código da injeção e ambiente do runner antes de alterar persistência.
- Escopo P118 é triagem e restauração do gate de CI; não afirma correção definitiva de uma causa desconhecida. Nenhuma tag/release por triagem documental.
