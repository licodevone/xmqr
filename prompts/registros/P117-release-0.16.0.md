# P117 — preparação da release 0.16.0

- Prompt [P117](../broker/117-release-0.16.0.md) criado antes do bump.
- Base funcional `b8aebf0`: [CI](https://github.com/licodevone/xmqr/actions/runs/38951626762) PASS, incluindo Mosquitto e pacote Ubuntu26.
- Versão candidata 0.16.0 em Cargo/lock/Dockerfile; `mqtt-broker --version` e `mqtt-admin --version` confirmados no WSL.
- Ubuntu26/WSL após bump: fmt, 132 testes de biblioteca/6 ignored mais integrações, Clippy, build, inventário MIT, 6 contratos de distribuição, 6 interop Mosquitto e integração cruzada com client0.14.0 PASS. Nenhum estado instalado do operador foi alterado.
- Commit de release, CI desse SHA, tag, assets e publicação: registrar após execução; não presumir PASS.
