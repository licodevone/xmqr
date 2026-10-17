# P167 rev1 — marco experimental broker 0.30.0

Entrada: P166 aceita Client Identifier vazio no MQTT 5 com atribuição exclusiva; C97–C99 formam o fluxo de CLI, reconexão manual e sessão durável. O documento persistente permanece v15 e o admin independente 0.10.0 continua compatível. Este prompt precede qualquer mudança de versão.

Objetivo: distribuir P166 no broker/admin legado 0.30.0. Atualizar Cargo/lock, Dockerfile, CHANGELOG, README, VERSIONING, nota de release e checklist factual. Explicar propriedade obrigatória `0x12`, recusa por Maximum Packet Size insuficiente, sessão persistente atribuída e limite de que o client não guarda o próprio estado QoS. Não declarar fases 6A–6D ou 7–9 concluídas; admin independente 0.10.0 permanece na release anterior porque o formato v15 não mudou.

Aceite: integração C97–C99 com broker real, regressões MQTT 3.1.1, Rust/fmt/Clippy/build release/licenças/distribuição/CI do commit exato; pacote Ubuntu 26.04 amd64, ciclo descartável de instalação/upgrade/rollback preservando dados privados; imagens broker/admin legado numeradas verificadas por digest; tag anotada e prerelease com manifesto, SHA-256/tamanhos remotos. Não mover `latest` nem instalar no WSL do operador.
