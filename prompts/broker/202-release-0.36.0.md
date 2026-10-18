# P202 — marco experimental broker/admin legado 0.36.0

Entrada: broker/admin legado 0.35.0 publicado, estado durável v15. P199/P200 aceitos após a tag anterior; P201 em validação. Client independente 0.30.0 e admin independente 0.10.0 publicados. Este prompt precede qualquer mudança de versão 0.36.0; o candidato aguarda CI e registro P201.

Objetivo: distribuir P199 (CONNECT completo com estrutura inválida), P200 (flags reservadas SUBSCRIBE/UNSUBSCRIBE/PUBREL) e P201 (pacotes exclusivos do servidor enviados pelo client) no broker e `mqtt-admin` legado 0.36.0. Atualizar Cargo/lock, Dockerfile, README, CHANGELOG, VERSIONING, nota de release e checklist. Não alterar client/admin independente, nem afirmar conformidade MQTT 5 integral ou fases 6A–6D/7–9 completas. Estado v15 não muda; preservar backup privado antes de downgrade.

Aceite da fonte: fmt, suíte completa, Clippy, build release, licenças, seis contratos de distribuição e fixtures/regressões P199–P201. CI do commit exato, inclusive pacote Ubuntu 26.04 amd64 e unit, antes da tag/release. Aceite da distribuição: `.deb` 0.36.0-1 com metadata e SHA-256; upgrade 0.35.0 → 0.36.0 → rollback descartável preservando configuração/estado; imagens numeradas broker/admin legado com usuário não privilegiado, labels de fonte, verificadores Docker/admin e execução por digest remoto. Tag anotada imutável `v0.36.0`, prerelease com oito anexos e tamanhos/hashes remotos conferidos. Não mover Docker `latest`, instalar no WSL do operador nem publicar APT.

Registrar desvio e repetir gate essencial se houver falha. Evidência: registro P202 com hash da fonte/tag, CI, checksum do pacote, digests das duas imagens, ciclo descartável, URL da release e limites. Atualizar o índice local de instaladores e curso após publicação validada.
