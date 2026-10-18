# P209 — marco experimental broker/admin legado 0.38.0

Entrada: broker/admin legado 0.37.0 publicado, P207 e P208 aceitos em `main`; client independente 0.31.0 e admin independente 0.10.0 publicados. Este prompt precede qualquer mudança de versão 0.38.0.

Objetivo: distribuir P207 (CONNECT inicial com flags reservadas e CONNACK `0x81` quando MQTT 5 é identificável) e P208 (flags reservadas de PUBACK/PUBREC/PUBCOMP e DISCONNECT `0x81`) no broker e `mqtt-admin` legado. Atualizar Cargo/lock, Dockerfile, README, CHANGELOG, VERSIONING, nota e checklist. Estado durável v15 sem migração. Não declarar conformidade MQTT 5 integral nem encerrar fases globais.

Aceite da fonte: fmt, suíte completa, Clippy, build release, licenças, seis contratos de distribuição e fixtures P194/P200/P205/P207/P208; CI do commit fonte exato, inclusive pacote Ubuntu 26.04 amd64. Aceite da distribuição: `.deb` 0.38.0-1 com metadata e SHA-256; upgrade 0.37.0 → 0.38.0 → rollback em ambiente descartável, preservando configuração/estado, com client 0.31.0. Imagens numeradas broker/admin legado com usuário não privilegiado, labels da fonte, verificadores Docker/admin e execução por digest remoto. Tag anotada imutável `v0.38.0`, prerelease com oito anexos e hashes/tamanhos remotos conferidos. Não mover Docker `latest`, instalar no WSL do operador nem publicar APT.

Registrar desvios e repetir gate essencial. Evidência P209 com hash de fonte/tag, CI, checksum do pacote, digests, ciclo descartável, release e limites. Atualizar índice local de instaladores e curso após publicação validada.
