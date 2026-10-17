# P179 — marco experimental broker 0.32.0

Entrada: 0.31.0 distribuiu P168–P172. P174–P178 acrescentam motivos de DISCONNECT recebidos/enviados pelo broker para erros selecionados (`0x81`, `0x82`, `0x94`, `0x95`) sem migração do estado v15. C101 permanece no client independente ainda 0.27.0; admin independente 0.10.0 continua compatível. Este prompt antecede qualquer mudança de versão.

Objetivo: distribuir broker/admin legado 0.32.0 com Cargo/lock, Dockerfile, README, CHANGELOG, VERSIONING e notas coerentes. Manter fases 6A–6D e 7–9 abertas e não declarar a matriz normativa completa. Não alterar a versão do client ou do admin independente.

Aceite: Rust/fmt/Clippy/build release/licença/distribuição e CI do commit fonte exato; pacote Ubuntu 26.04 amd64 e ciclo descartável de upgrade 0.31.0 → 0.32.0 → rollback com dados privados preservados; imagens numeradas broker/admin legado verificadas por digest; tag anotada/prerelease com anexos, tamanhos e SHA-256 remotos. Não mover Docker `latest` nem instalar no WSL do operador. Sem promessa de produção.
