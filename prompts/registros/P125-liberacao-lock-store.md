# P125 — liberação do lock do armazenamento

- [Prompt P125 rev1–2](../broker/125-liberacao-lock-store.md) criado antes da correção. A [CI funcional P123](https://github.com/licodevone/xmqr/actions/runs/38983313941) teve pacote Ubuntu26 PASS e job Rust FAIL em `fault_tests.rs:177` (`AlreadyOpen` após `drop(store)`); a CI [C64](https://github.com/licodevone/xmqr-client/actions/runs/38983320426) passou inteira.
- `Store` agora libera explicitamente o lock exclusivo em `Drop`; o teste novo tenta abrir o segundo escritor enquanto o primeiro vive e reabre imediatamente após seu descarte, cem vezes. A exclusão original, WAL, snapshots e documento durável permanecem.
- Ubuntu26/WSL: teste dirigido de reabertura e teste de falhas de snapshot PASS; suíte completa 138 PASS/6 campanhas ignored, demais testes PASS; fmt, Clippy, build e inventário MIT PASS. Primeira tentativa Clippy falhou pelo campo `_lock`; renomeado para `lock` e todos os gates repetidos com PASS.
- CI do commit corretivo pendente. Não instalar pacote no WSL do operador; não publicar versão 0.17.0 antes da CI verde.
