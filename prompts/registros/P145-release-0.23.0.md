# P145 — prerelease experimental broker 0.23.0

- [Prompt P145](../broker/145-release-0.23.0.md) criado antes do bump. Fonte P144 e CI aceitas; C81 `dc2364f67ee22300bac0429d1df563d45e538425` passou na [CI](https://github.com/licodevone/xmqr-client/actions/runs/39001984037).
- Preparação: Cargo/lock, Dockerfile, changelog, README, VERSIONING, nota de release e checklist pendente atualizados. Documento durável v10 sem migração; rollback ao 0.22.0 ainda exige ciclo de pacote e backup offline.
- Gate local pré-commit PASS: fmt, 164 testes principais/6 ignorados e 23 integrações Rust, Clippy `-D warnings`, seis testes de distribuição e inventário de licenças. Build release, fonte exata, CI, pacote, tags e publicação pendentes.
