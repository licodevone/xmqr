# P151 rev1 — marco experimental broker 0.25.0, estado v12

Entrada: P150 Subscription Identifier/estado v12 em CI; C87 client aceito. Este prompt precede o bump de versão. Só avançar à distribuição após CI P150 PASS.

Objetivo: publicar broker e `mqtt-admin` legado 0.25.0 com Subscription Identifier MQTT 5, client parceiro 0.23.0/C88 e documento durável v12. Atualizar Cargo/lock, Dockerfile, changelog, README, VERSIONING, plano e nota. Broker 0.24.0/admin independente 0.6.0 não reabrem v12; rollback exige backup privado v11 anterior à migração. Fases 6A–6D e 7–9 continuam abertas.

Aceite: gates locais e CI do commit exato; pacote Ubuntu26 amd64 e imagens broker/admin legado numeradas com revisão/versão corretas; ciclo de instalação/upgrade/downgrade/remove em contêiner descartável com client 0.22→0.23, distinguindo pacote de restauração de estado. Tag anotada `v0.25.0`, prerelease GitHub com anexos e SHA-256 remotos conferidos, Docker Hub numerado e digest remoto. Não mover `latest`, alterar tags antigas, instalar no WSL do operador nem executar ESP32.
