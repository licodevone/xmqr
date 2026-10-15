# P99 — default de distribuição do broker

- Entrada: tag de código `v0.13.0` em `4d26cc3`, sem GitHub Release.
- Falha real: `python3 scripts/test_distribution.py` — 1/6 falhou porque
  `ARG VERSION=0.12.0` divergia de Cargo0.13.0. Corrigido após prompt
  [P99](../broker/99-default-versao-distribuicao.md).
- Solução: Dockerfile default e Cargo/lock0.13.1; funcionalidade P97 preservada.
  A tag0.13.0 não foi reescrita e não será distribuída. O marco de publicação
  é 0.13.1 após gates/artefatos do novo commit.
- Após correção, `scripts/test_distribution.py`: 6/6 PASS. Ubuntu26/WSL:
  fmt, suíte Rust serial, Clippy `-D warnings`, build release e inventário MIT
  PASS. Integração de binários release P97/C48 e regressão P96 PASS antes da
  correção de versão, sem mudança funcional posterior. Artefatos ainda requerem
  validação antes da publicação.
