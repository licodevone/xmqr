# P129 rev1 — prerelease experimental broker 0.18.0

Entrada: `main` P128 `564e373`, árvore limpa, versão publicada 0.17.0. P127/C66 CIs PASS, CIs P128/C67 pendentes. O documento durável passa a v6 com expiração finita MQTT 5; binários 0.17.0 não podem abri-lo. Fases 6A–6D abertas.

Objetivo: publicar checkpoint experimental 0.18.0 do broker/mqtt-admin legado com Clean Start e Session Expiry 0/finita/infinita, após CI funcional PASS. Elevar Cargo/lock, Dockerfile, changelog, VERSIONING, README/plano e nota de release. O xmqr-admin independente 0.4.0 não muda.

Aceite: gates fmt/test/Clippy/build, integração cruzada, Mosquitto e inventário MIT no commit exato; pacote Ubuntu26 amd64 e imagens Docker numeradas verificados sem instalar no WSL do operador; tag anotada imutável v0.18.0; prerelease GitHub com assets, SHA-256, manifesto, orientação explícita de backup v5/rollback e limites. Publicar Docker Hub numerado somente com digest remoto conferido, nunca mover latest. Não declarar fase 6 concluída nem conformidade MQTT 5 integral.
