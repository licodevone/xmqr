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
- Publicação: tag anotada imutável `v0.14.0` no commit
  `ca1fa3e08333cd5da6b15d4b171fad61cd8e9263`, push de `main`/tag e
  [prerelease GitHub](https://github.com/licodevone/xmqr/releases/tag/v0.14.0)
  confirmados. Os 8 assets (.deb Ubuntu 26.04 amd64, exports Docker do broker
  e admin legado, manifesto e seus SHA-256) tiveram digests remotos iguais
  aos arquivos locais; manifesto aponta para esse commit.
- Imagens numeradas Docker Hub confirmadas, sem mover `latest`:
  `lepinheiro100/xmqr-broker:0.14.0` digest
  `sha256:4700c9c215ed71ab895d1dbe920b120ae40754e84d01003f1d052f5456724e1e`
  e `lepinheiro100/xmqr-admin:0.14.0` digest
  `sha256:fa315d4103744bc0b96ab7a90763851e9c7b3bd014610b5ee7c17eefa9912d14`.
