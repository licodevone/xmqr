# P143 — prerelease experimental broker 0.22.0

- [Prompt P143](../broker/143-release-0.22.0.md) criado antes do bump. Base funcional P142 `de6517c249f59153764919c5b36d8f477c362411` com [CI PASS](https://github.com/licodevone/xmqr/actions/runs/39000015530) e C78 `6820aad128ede9e9d85f4356ca297b1ce746ef9a` com [CI PASS](https://github.com/licodevone/xmqr-client/actions/runs/39000007226).
- Cargo/lock, Dockerfile, changelog, README, VERSIONING, plano e nota de release preparados. Documento durável v10 requer backup privado v8 anterior à migração para rollback ao broker 0.21.0. Gates da fonte exata, tag, pacote, imagens e prerelease pendentes.
- Gate local pré-commit: fmt, 164 testes principais PASS/6 ignorados, demais suítes Rust, Clippy `-D warnings`, 6 testes de distribuição e inventário de licenças PASS. Build release e CI da versão 0.22.0 ainda pendentes.
