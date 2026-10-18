# P213 — distribuição experimental broker/admin legado 0.40.0

Entrada: broker/admin legado 0.39.0 publicado, estado v15; P212 aceito em `main` com WSS mTLS local e CI da fonte funcional PASS. Client C114 em validação para o par WSS. Este prompt precede mudança de versão, tag ou release.

Objetivo: publicar broker/admin legado 0.40.0 com P212 depois do aceite cruzado com client C114, preservando o estado v15 e as políticas anteriores. WSS é opt-in em loopback `secure-mtls`, sem navegador, remoto ou TLS-senha via WSS. Fases globais 6A–6D/7–9 continuam abertas.

Escopo: manifests/lock, `--version`, CHANGELOG, VERSIONING, README, nota de release, matriz/checklist e registro; pacote Ubuntu 26.04 amd64, exports Docker broker/admin com tags numeradas, hashes e anexos. Não tocar `latest`, WSL instalado do operador nem versão do admin independente.

Gate: CI da fonte candidata exata em Rust e pacote Ubuntu 26.04; fixture P212 e integração com client C114, fmt, suíte, Clippy, build, licenças e distribuição. Validar metadados e SHA-256 do `.deb`, upgrade/rollback descartável de broker0.39/client0.32 para broker0.40/client0.33 preservando configuração/estado e arquivo privado; Docker mTLS e WSS pub/sub por digest remoto. Somente depois disso criar tag anotada imutável `v0.40.0` no commit candidato e prerelease com manifesto e checksums, baixar anexos para conferir tamanho/hash. Registrar PASS/FAIL/BLOCKED reais. Sem alegar fase 7 completa ou produção.
