# P117 rev1 — marco experimental MQTT 5 0.16.0

Data 2026-10-16. Entrada `b8aebf0` em `main`, broker 0.15.0, P115/P116 aceitos localmente; CI remota pendente. Versão minor própria para o subconjunto pub/sub MQTT 5 QoS0/1 da fase6A, que continua aberta.

Após CI de P116 aprovada, elevar Cargo/lock e Dockerfile para 0.16.0; atualizar changelog, VERSIONING, plano e nota de release. Validar fmt/test/Clippy/build, inventário, interop Mosquitto, integração cruzada, contratos de distribuição e `.deb` Ubuntu26 amd64. Criar commit limpo, testar o commit exato e tag anotada imutável `v0.16.0`. Publicar prerelease GitHub com pacote, checksums e instruções de upgrade/rollback se os gates de distribuição passarem; imagens Docker numeradas somente se construídas e inspecionadas. Não mover `latest`, não mudar admin independente 0.4.0 nem anunciar conformidade MQTT 5 total/produção. Registrar SHA, CI, assets e limites.
