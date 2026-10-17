# P173 rev1 — marco experimental broker 0.31.0

Entrada: 0.30.0 distribuiu Client Identifier atribuído. P168–P172 acrescentam interoperabilidade Paho e motivos/propriedades selecionados de PUBACK/PUBREC/PUBREL/PUBCOMP/DISCONNECT MQTT 5. O estado permanece v15 e o admin independente 0.10.0 é compatível. Este prompt antecede a mudança de versão.

Objetivo: distribuir broker/admin legado 0.31.0 com Cargo/lock, Dockerfile, README, CHANGELOG, VERSIONING e notas coerentes. Não declarar fases 6A–6D ou 7–9 concluídas. O client independente permanece 0.27.0 e o admin independente 0.10.0, sem nova tag deles.

Aceite: Rust/fmt/Clippy/build release/licença/distribuição e CI do commit exato; pacote Ubuntu 26.04 amd64 e ciclo descartável de upgrade 0.30.0 → 0.31.0 → rollback preservando dados privados; imagens numeradas broker/admin legado verificadas por digest; tag anotada/prerelease com 8 anexos, SHA-256 e tamanhos remotos. Não mover Docker `latest` nem instalar no WSL do operador. Sem mudança de esquema ou promessa de produção.
