# P103 — distribuição experimental broker/legado admin 0.14.0

- Prompt [P103](../broker/103-release-0.14.0.md); versão 0.14.0 em Cargo,
  lock e default Docker. P100/B11 e P101/B09 são a mudança funcional; client
  C50/C05 tem versão/release independente 0.12.0/C51.
- Ubuntu26/WSL após bump: fmt, `cargo test --locked` (114 testes lib PASS,
  6 campanhas explícitas ignoradas, demais binários/integrações PASS), Clippy
  `-D warnings`, build release, inventário e 6 contratos de distribuição PASS.
  Binários release broker0.14.0/client0.12.0 integrados por P96/P97/P100/P101:
  mTLS, TLS-senha, CA/CRL/cert/key, rollback, ACL, QoS0/1/2, retained e C50.
- Firmware E02: cross-build ESP release, fmt, Clippy e inventário PASS; flash
  físico verificado e seis rotações TLS concluídas na COM4. [P102](P102-e02-fisico.md)
  e [aceite](../../docs/phase4-acceptance.md) registram o escopo e os limites.
- Publicação: pendente neste checkpoint; preencher commit/tag, .deb, imagens,
  checksums, assets e confirmação remota após o ciclo de distribuição.
