# P125 rev1 — liberação explícita do lock do Store

Entrada: `main` `621ac36`, broker 0.16.0. A CI [38983313941](https://github.com/licodevone/xmqr/actions/runs/38983313941) falhou no teste de falhas de snapshot em `Store::open` após `drop(store)`, com `AlreadyOpen` (`fault_tests.rs:177`). É a terceira ocorrência observada após P114 e P118; o teste de MQTT5 P123 passou na mesma suíte.

Objetivo: liberar explicitamente o lock exclusivo ao destruir `Store`, antes do fechamento do arquivo, sem afrouxar a exclusão entre escritores. Acrescentar teste de reabertura imediata após o drop e manter os testes de falha de snapshot/WAL.

Aceite: teste dirigido repetido, `cargo fmt --all -- --check`, `cargo test --locked`, `cargo clippy --locked --all-targets -- -D warnings`, `cargo build --locked --bins`, CI completa e pacote Ubuntu26 PASS. Não usar retry ou espera, não mudar formato durável, não instalar pacote no WSL do operador. Registrar qualquer falha residual e não publicar 0.17.0 antes de CI verde.

Rev2: a primeira implementação passou testes completos, mas Clippy rejeitou o uso explícito do campo `_lock` (`used_underscore_binding`). Renomear o campo para `lock` antes de repetir todos os gates.
