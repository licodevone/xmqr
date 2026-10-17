# P165 rev1 — marco experimental broker 0.29.0, estado v15

Entrada: P162 Server Keep Alive, P163 metadados do Will e P164 Message Expiry do Will passaram nos ensaios locais; C94/C95 são o client parceiro. A19 atualiza o admin independente para v15. Este prompt precede qualquer mudança de versão.

Objetivo: distribuir P162–P164 em broker/admin legado 0.29.0 e documento v15. Atualizar Cargo/lock, Dockerfile, CHANGELOG, README, VERSIONING, nota de release e checklist factual. Distinguir prazo de Will Delay do prazo de Message Expiry, iniciado somente na publicação. Explicar leitura v1–v14, primeira gravação v15 e rollback executável apenas com backup privado v14 anterior. Não declarar MQTT 5 integral ou fases 6A/6B concluídas.

Aceite: C95 no broker real, regressão P163/C94/C70, Rust/fmt/Clippy/build release/licenças/distribuição/CI do commit exato; pacote Ubuntu 26.04 amd64, ciclo descartável de upgrade/rollback preservando dados privados e comprovando barreira v15; imagens broker/admin legado numeradas e verificadas por digest; tag anotada e prerelease com manifesto, SHA-256/tamanhos e digests remotos. Não mover `latest` nem instalar no WSL do operador.
