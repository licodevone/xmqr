# P155 rev1 — marco experimental broker 0.26.0, estado v13

Entrada: P153 shared temporário aceito; P154 shared persistente e estado v13 em CI. C89 client já aceito. Este prompt antecede o bump de versão. Só avançar ao marco após CI P154 PASS; não publicar a release antes de A16/admin independente compatível com v13.

Objetivo: preparar broker e `mqtt-admin` legado 0.26.0 com shared subscriptions MQTT 5 e documento v13. Atualizar Cargo/lock, Dockerfile, changelog, README, VERSIONING, plano e nota de release; registrar limitação QoS1 ao terminar sessão, AUTH e fases abertas. Broker 0.25.0/admin independente 0.7.0 não reabrem v13; rollback exige backup privado v12 anterior à migração. Client parceiro C89 deve ter marco próprio e A16 deve validar estado/backup antes da publicação do broker.

Aceite: gates locais e CI do commit exato; pacote Ubuntu26 amd64 e imagens broker/admin legado numeradas; ciclo descartável de instalação/upgrade/downgrade/remove distinguindo pacote e restauração de estado. Tag anotada `v0.26.0` no commit aprovado, prerelease GitHub com anexos e SHA-256 remotos verificados, Docker Hub numerado e digest remoto. Não mover `latest`, alterar tags antigas, instalar no WSL do operador nem executar ESP32.
