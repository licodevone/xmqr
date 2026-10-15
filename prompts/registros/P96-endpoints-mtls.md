# P96 — endpoints mTLS compartilhados

- Prompt: [P96 rev1–9](../broker/96-multiplos-endpoints-mtls.md).
- Entrada: `cce3549`, broker 0.11.6; mudanças parciais de P96 preservadas e concluídas.
- Plataforma: Ubuntu 26.04/WSL, Rust local, recursos de teste em diretórios temporários.
- Entrega: TOML v1 aceita até três binds mTLS extras; todos compartilham TLS,
  política, roteador, estado, monitor e semáforo/IDs. Modos de laboratório
  recusam adicionais; binds inválidos/sobrepostos falham antes de aceitar clientes.
- Gates finais: `cargo fmt --all -- --check`, `cargo clippy --locked
  --all-targets -- -D warnings`, `cargo build --locked --release` e
  `python3 scripts/license_inventory.py --check` PASS. `cargo test --locked
  -- --test-threads=1` PASS (114 lib, 6 ignored, 22 outros); teste
  `actor_acks_after_commit` passou 10 vezes isolado.
- Ocorrência: uma execução paralela da suíte falhou em teste de persistência
  preexistente com `AlreadyOpen`; não foi reproduzida nas 10 repetições ou
  na suíte serial. Risco residual de intermitência documentado; sem alteração
  da persistência nesta fatia.
- Integração de binários release: `scripts/verify_multi_endpoint.py` PASS para
  QoS0/1/2 cruzados, limite global N/N+1, retained após restart, bind ocupado,
  CA/usuário/senha incorretos com perfis de client; senha de fixture gerada por
  execução, não versionada. Versões executadas:
  broker 0.12.0 e client 0.10.0.
- Revisão de segurança: mTLS obrigatório nos endpoints adicionais; nenhuma
  política permissiva implícita, segredo em argv/log ou novo estado persistido.
  Cobertura limitada ao recorte P96 e fixtures locais, sem auditoria integral.
- Compatibilidade: opt-in/restart-only; TOML sem campo preserva listener único.
  B09 parcial: políticas por endpoint, TLS sem certificado e rotação pendentes.
- Publicação: candidato à tag de código `v0.12.0` após revisão do diff.
