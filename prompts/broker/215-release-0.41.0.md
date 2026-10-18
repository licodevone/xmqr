# P215 — distribuição experimental broker/admin legado 0.41.0

Entrada: broker/admin legado 0.40.0 publicado; P214 adiciona opt-in remoto WSS mTLS em `main` com testes locais e Docker PASS. CI da fonte funcional ainda em execução ao abrir este prompt. Client C117 é o par remoto. Este prompt precede mudança de versão, tag ou release.

Objetivo: publicar broker/admin legado 0.41.0 com P214, sem migração do estado v15 e sem mover `latest`. Admin independente permanece 0.10.0. WSS remoto exige flag explícita e mTLS/ACL; navegador não entra no marco.

Escopo: manifests/lock, `--version`, CHANGELOG, VERSIONING, README, nota de release, plano e registro; pacote Ubuntu 26.04 amd64 e imagens Docker numeradas broker/admin. Não tocar WSL instalado do operador, nem sobrescrever tag/asset publicado.

Gate: CI da fonte candidata exata em Rust e pacote Ubuntu; regressões WSS local/remoto, TCP/TLS, segurança de CA/SAN/senha/ACL, fmt, suíte, Clippy, licenças/distribuição. Verificar metadata/SHA-256 do `.deb`, upgrade/rollback descartável de broker 0.40/client 0.33 para broker 0.41/client 0.34, imagens por digest remoto com pub/sub 3.1.1/5, tags anotadas imutáveis, prereleases e hashes de todos os anexos baixados. Marcar PASS/FAIL/BLOCKED reais. Fases globais 6A–6D/7–9 continuam abertas.
