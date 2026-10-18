# P211 — marco experimental broker/admin legado 0.39.0

Entrada: broker/admin legado 0.38.0 publicado; P210 aceito em `main`; client C112 validado, 0.31.0 publicado. Este prompt precede qualquer alteração de versão 0.39.0.

Objetivo: distribuir P210, listener WebSocket MQTT opt-in em loopback no perfil `open-lab`, com `/mqtt`, subprotocolo `mqtt`, `Origin` recusado e quota compartilhada TCP/WS. Atualizar Cargo/lock, Dockerfile, README, CHANGELOG, VERSIONING, nota de release e checklist. Estado durável v15 sem migração. Não declarar WSS, acesso remoto/browser nem fase 7 completa.

Aceite da fonte: fmt, suíte completa, Clippy, build release, licenças, seis contratos de distribuição, fixture P210 com client C112 e regressões TCP/TLS; CI do commit fonte exato, inclusive pacote Ubuntu 26.04 amd64. Aceite da distribuição: `.deb` 0.39.0-1 com metadata/SHA-256; upgrade 0.38.0 → 0.39.0 → rollback descartável, preservando configuração/estado. Imagens numeradas broker/admin legado com usuário não privilegiado, labels da fonte, verificadores Docker/admin e execução por digest remoto. Tag anotada imutável `v0.39.0`, prerelease com oito anexos e hashes/tamanhos remotos conferidos. Não mover Docker `latest`, instalar no WSL do operador nem publicar APT.

Registrar desvios e repetir gate essencial. Evidência P211 com fonte/tag, CI, checksum do pacote, digests, ciclo descartável, release e limites. Atualizar índice local de instaladores e curso após publicação validada.
