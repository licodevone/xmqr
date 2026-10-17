# P149 rev1 — marco experimental broker 0.24.0, estado v11

Entrada: P148 `b8630c8596a89fea651eb82d94f49a52fd6d959c` em CI, C85 aceito. Este prompt precede o bump de versão. Só iniciar o bump após CI PASS de P148.

Objetivo: publicar broker e utilitário legado `mqtt-admin` 0.24.0 com No Local/Retain As Published e documento durável v11. Atualizar Cargo/lock, Dockerfile, changelog, README, VERSIONING, plano e nota de release. Explicitar que broker 0.23.0 e admin independente 0.5.0 não reabrem v11; backup privado v10 anterior à migração é necessário para rollback. Fases 6A–6D e 7–9 permanecem abertas.

Aceite: gates locais e CI do commit exato; pacotes Ubuntu26 amd64 e imagens numeradas broker/admin legada com revisão/versão corretas; ciclo de instalação/upgrade/downgrade/remove em contêiner descartável, sem afirmar restauração de estado v11 por versão anterior. Criar tag anotada `v0.24.0`, prerelease GitHub com anexos e SHA256 remotos conferidos, Docker Hub numerado e digest remoto. Sem mover `latest`, tags antigas, instalar no WSL do operador ou ensaiar ESP32.
