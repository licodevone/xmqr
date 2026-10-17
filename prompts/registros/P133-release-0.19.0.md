# P133 — prerelease experimental broker 0.19.0

- [Prompt P133](../broker/133-release-0.19.0.md) criado antes do bump. Base P132 `c5f3cb2` com [CI PASS](https://github.com/licodevone/xmqr/actions/runs/38992393173); client C70 com [CI PASS](https://github.com/licodevone/xmqr-client/actions/runs/38991792436).
- Fonte imutável: commit `fee18c9bd66b876cae7814a2e3e8905a5089c4ec`, tag anotada `v0.19.0`, [CI da fonte PASS](https://github.com/licodevone/xmqr/actions/runs/38992670661). Gates locais fmt, testes, Clippy, build, integração real, licenças e contratos de distribuição PASS.
- [Prerelease](https://github.com/licodevone/xmqr/releases/tag/v0.19.0): `.deb`, imagens broker/admin legado, três SHA-256, manifesto e SHA-256 do manifesto (oito anexos). Tamanho e SHA-256 remotos dos oito anexos conferidos.
- Docker Hub numerado: `lepinheiro100/xmqr-broker:0.19.0` digest `sha256:1d821b4f2d6f63d2efeeec8bd5e986511326b1ae45519369d56c5eeddbd67b9c`; `lepinheiro100/xmqr-admin:0.19.0` digest `sha256:cff07873eaaaf0ee6a078a97433d2125781b8e2b0bb12a2f29ff2d2fb50a611d`. Digests remotos conferidos; versões executadas por digest. `latest` intacta.
- Pacotes 0.18.0/0.16.0 → 0.19.0/0.17.0 → downgrade e remoção testados em contêiner descartável Ubuntu26 (`PACKAGE_LIFECYCLE_PASS`), sem instalar no WSL do operador.
- [Nota de release](../../docs/releases/0.19.0.md): rollback do estado v8 exige backup privado v6 anterior. Admin independente 0.4.0 inalterado. Fases 6A–6D ainda abertas.
