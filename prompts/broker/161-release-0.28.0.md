# P161 rev1 — marco experimental broker 0.28.0

Entrada: P158 recusa método AUTH indisponível com motivo MQTT 5 específico; P159 implementa SASL PLAIN inicial sobre TLS; P160 recebe reautenticação PLAIN da mesma identidade e geração de segurança. C91/C92 são os clients parceiros. O estado durável permanece v14 e o admin independente 0.9.0 já o suporta. Este prompt precede qualquer mudança de versão.

Objetivo: distribuir P158–P160 como broker/admin legado 0.28.0. Atualizar Cargo/lock, Dockerfile, changelog, README, VERSIONING, nota de release e checklist factual. Explicitar que o mecanismo é PLAIN sobre TLS/mTLS, com reautenticação apenas para mesma identidade; não há desafio interativo, reautenticação periódica automática ou conformidade MQTT 5 integral. Manter estado v14 e compatibilidade de leitura do admin independente 0.9.0. Não alterar instalação WSL do operador.

Aceite: C92 comprovado contra broker em TLS e mTLS, negativos de AUTH e regressão C91; Rust, fmt, Clippy, build release, licenças, contratos de distribuição e CI do commit exato; pacote Ubuntu 26.04 amd64; ciclo descartável de instalação/upgrade/rollback; imagens broker/admin legado numeradas verificadas; tag anotada e prerelease com manifesto, SHA-256/tamanhos e digests remotos. Publicar somente depois de concluir gates, sem mover `latest` nem marcar fase 6D completa.
