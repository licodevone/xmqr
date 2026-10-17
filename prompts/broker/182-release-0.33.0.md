# P182 — marco experimental broker/admin legado 0.33.0

Entrada: broker 0.32.0 publicado; P180 implementa User Property contextual de assinatura e P181 acrescenta DISCONNECT para identificador impróprio ou duplicado. Estado durável v15, sem migração. Client C102 na árvore independente aceita as propriedades; admin independente 0.10.0 permanece compatível. Este prompt antecede qualquer mudança de versão.

Objetivo: distribuir broker e admin legado 0.33.0 em Cargo/lock, Dockerfile, README, CHANGELOG, VERSIONING e nota de release. Explicar os dois motivos `0x81`/`0x82` de P181 e os limites de P180. Fases 6A–6D e 7–9 continuam abertas; não declarar conformidade integral MQTT 5. Não alterar a versão do client nem do admin independente.

Aceite: CI da fonte exata após gates Rust/fmt/Clippy/build/licença/distribuição e regressões P175–P181; pacote Ubuntu 26.04 amd64 com upgrade 0.32.0 → 0.33.0 → rollback em container descartável preservando estado privado; imagens numeradas broker/admin legado executadas por digest; tag anotada e prerelease com anexos, tamanhos e SHA-256 remotos. Não mover Docker `latest` nem instalar no WSL do operador. Se algum gate falhar, registrar e rever o prompt antes de corrigir.
