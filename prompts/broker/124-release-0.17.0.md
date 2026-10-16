# P124 rev1 — prerelease experimental broker 0.17.0

Entrada: `main` `621ac36`, árvore limpa, versão publicada 0.16.0, P119–P123 implementados com gates locais e integração real PASS; CI de P123 pendente. Client parceiro C64 em `f68174b`, versão publicada 0.14.0. Fases 6A–6D permanecem abertas.

Rev2: a CI P123 falhou no teste de lock antigo; P125 corrigiu o ciclo de vida do lock em `bb1084b`. [CI corretiva](https://github.com/licodevone/xmqr/actions/runs/38983737064) e [CI C64](https://github.com/licodevone/xmqr-client/actions/runs/38983320426) PASS. Base de release passa a `bb1084b` no broker e `f68174b` no client, sem reescrever a falha histórica.

Objetivo: após CI de P123 PASS, publicar marco experimental 0.17.0 do broker/mqtt-admin legado com QoS2 MQTT5, cancelamento, reason codes ACL e CONNECT informativo. Elevar Cargo/lock e Dockerfile; atualizar changelog, VERSIONING, README/plano e nota de release com limites. Não alterar xmqr-admin independente 0.4.0 nem o formato durável.

Aceite: gates fmt/test/Clippy/build e integração cruzada no commit exato, inventário MIT, contratos de distribuição, `.deb` Ubuntu26 amd64 sem instalar no WSL do operador, imagens Docker numeradas verificadas, tag anotada imutável `v0.17.0`, prerelease GitHub com assets, SHA-256, manifesto, upgrade/rollback. Publicar Docker Hub apenas se imagem local e digest remoto forem verificáveis; nunca mover `latest`. Registrar SHA, CI, anexos e riscos. Não anunciar conformidade MQTT5 integral ou produção.
