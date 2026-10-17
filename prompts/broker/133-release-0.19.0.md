# P133 rev1 — prerelease experimental broker 0.19.0

Entrada: `main` após P132, broker publicado 0.18.0, documento durável v8; fases 6A–6D abertas.

Objetivo: publicar checkpoint 0.19.0 de P130–P132: Message Expiry, DISCONNECT Session Expiry e Will Delay MQTT 5. Bump Cargo/lock, Dockerfile, changelog, VERSIONING, README/plano e nota. O `mqtt-admin` legado acompanha; `xmqr-admin` independente não muda.

Aceite: CI funcional verde no commit anterior e da fonte exata; fmt/test/Clippy/build, integração real e licenças; pacote Ubuntu26 e imagens Docker numeradas testados sem instalar no WSL do operador; tag anotada v0.19.0 e prerelease GitHub com `.deb`, imagens, SHA-256 e manifesto conferidos; Docker Hub numerado com digest remoto conferido, `latest` intacta. Rollback de v8 exige backup privado anterior v6/v7. Não declarar fase 6 completa.
