# P118 rev1 — investigar falha de lock na CI do broker

Data: 2026-10-16. Entrada: `main` em `14f060b`, broker 0.16.0 experimental. A CI do commit de documentação falhou no teste `snapshot_boundary_failures_keep_all_previously_acknowledged_state`: a reabertura após `drop(store)` retornou `AlreadyOpen` em `src/persistence/fault_tests.rs:177`. O mesmo teste passou na CI da tag 0.16.0.

## Objetivo e escopo

Identificar a causa da falha de reabertura de `Store` e deixar a CI de `main` verde sem enfraquecer a exclusão de escritor nem mascarar falhas reais de persistência. Inspecionar o ciclo de vida do lock, reproduzir o teste em repetição e em suíte completa, consultar a tentativa de rerun da CI e adicionar diagnóstico mínimo quando necessário. Arquivos candidatos: `src/persistence/{mod,fault_tests}.rs`, registro P118 e plano.

## Limites e aceite

Preservar o lock entre processos, a recuperação de snapshots/WAL, testes de falhas injetadas e o estado durável. Não inserir espera ou retry arbitrário em produção. Se não houver causa reproduzível, registrar a natureza intermitente e evidência da nova CI antes de decidir por alteração. Executar `cargo fmt --check`, `cargo test --locked`, `cargo clippy --locked --all-targets -- -D warnings` e CI do commit; anotar PASS/FAIL/BLOCKED reais. Só marcar este item concluído após CI aprovada.
