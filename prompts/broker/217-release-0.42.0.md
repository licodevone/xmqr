# P217 — distribuição experimental broker/admin legado 0.42.0

Entrada: 0.41.0 publicado; P216 aceito em `main` com allowlist HTTPS exata para `Origin` WSS mTLS; client C119/C120 aceito em `main`. Este prompt precede mudança de versão, tag e release.

Objetivo: distribuir broker/admin legado 0.42.0 com P216, sem mudar estado durável v15 ou a versão do admin independente 0.10.0. `Origin` não autorizado permanece recusado; certificado, CA, senha, ACL e opt-in remoto continuam obrigatórios.

Escopo: manifests/lock, versão CLI, changelog/README/versionamento, pacote Ubuntu 26.04 amd64, imagens Docker numeradas e nota de prerelease. Não alterar WSL instalado, tags publicadas ou `latest`.

Gate: CI da fonte candidata exata (Rust/pacote), suite/fmt/Clippy/licenças, WSS/TCP e negativos, `.deb` com SHA-256/metadata, ciclo descartável upgrade/rollback desde 0.41.0 e client 0.34.0, imagem por digest remoto com integração MQTT 3.1.1/5 e Origin permitido/negado, tags imutáveis, prerelease e hashes remotos conferidos. Registrar PASS/FAIL/BLOCKED honestamente. Fases globais continuam abertas.
