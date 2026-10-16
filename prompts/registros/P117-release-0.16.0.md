# P117 — preparação da release 0.16.0

- Prompt [P117](../broker/117-release-0.16.0.md) criado antes do bump.
- Base funcional `b8aebf0`: [CI](https://github.com/licodevone/xmqr/actions/runs/38951626762) PASS, incluindo Mosquitto e pacote Ubuntu26.
- Versão candidata 0.16.0 em Cargo/lock/Dockerfile; `mqtt-broker --version` e `mqtt-admin --version` confirmados no WSL.
- Ubuntu26/WSL após bump: fmt, 132 testes de biblioteca/6 ignored mais integrações, Clippy, build, inventário MIT, 6 contratos de distribuição, 6 interop Mosquitto e integração cruzada com client0.14.0 PASS. Nenhum estado instalado do operador foi alterado.
- Fonte/tag imutável: `e18d2132e6870291c35e8654b545933a03f6b318`/`v0.16.0`; [CI](https://github.com/licodevone/xmqr/actions/runs/38952169758) PASS, incluindo instalação `.deb` Ubuntu26.
- `.deb` `xmqr-broker_0.16.0-1_amd64.deb`; imagens numeradas `lepinheiro100/xmqr-broker:0.16.0` e `lepinheiro100/xmqr-admin:0.16.0`. Oito anexos da [prerelease](https://github.com/licodevone/xmqr/releases/tag/v0.16.0) tiveram nome, tamanho e SHA-256 conferidos contra arquivos locais. Manifesto inclui origem SHA, alvos e hashes.
- Docker Hub: broker `sha256:c3f65cafbfe265c96153c6cdf61827ab8d9dbe391802cb6a8f5f4686c4ed97dd`; admin legado `sha256:b9137db5362da7cf6dafbe1cd8ee1cf58ed936f9ae1e7380a100891636583107`. Digests remotos conferidos e ambos executados por digest com `--version` 0.16.0. `latest` preservada; admin independente 0.4.0 não alterado.
- Release experimental do subconjunto MQTT5, sem conformidade integral/produção. Upgrade/rollback em [nota](../../docs/releases/0.16.0.md). Instalações existentes do operador não foram alteradas.
