# P206 — marco experimental broker/admin legado 0.37.0

Entrada: broker 0.36.0 publicado; P203–P205 aceitos em `main`. P205 corrige o motivo MQTT 5 de flags inválidas em PINGREQ/DISCONNECT, que a release 0.36.0 ainda responde como `0x82`. Este prompt precede qualquer mudança de versão 0.37.0.

Objetivo: distribuir P203 (tipo zero reservado), P204 (AUTH com flags reservadas) e P205 (PINGREQ/DISCONNECT com `0x81` corrigido) no broker e no `mqtt-admin` legado. Atualizar Cargo/lock, Dockerfile, changelog, README, versionamento, nota e checklist sem alterar client/admin independente nem estado durável v15. Não declarar MQTT 5 integral ou encerramento das fases globais.

Aceite da fonte: fmt, suíte, Clippy, build release, licenças, seis contratos de distribuição e regressões P178/P201/P203–P205; CI do commit fonte exato, inclusive pacote Ubuntu 26.04 amd64. Aceite da distribuição: `.deb` 0.37.0-1 com metadata e SHA-256; upgrade 0.36.0 → 0.37.0 → rollback em ambiente descartável preservando configuração/estado, com client 0.30.0. Imagens numeradas broker/admin legado com usuário não privilegiado, labels da fonte, verificadores Docker/admin, publicação e execução por digest remoto. Tag anotada imutável `v0.37.0`, prerelease com oito anexos, SHA-256 e tamanhos remotos conferidos. Não mover Docker `latest`, instalar no WSL do operador nem publicar APT.

Registrar falhas e repetir gate essencial. Evidência P206 com hash de fonte/tag, CI, pacote, digests, ciclo descartável, release e limites. Atualizar índice local de instaladores e curso após publicação validada.

Revisão 2: os gates de fonte locais (fmt, suíte, Clippy, build release, licenças, seis contratos, P201/P203–P205) passaram, mas a primeira invocação de `build_deb.py` recebeu um SHA no campo `--revision`, que aceita apenas número Debian. Não houve pacote candidato nessa tentativa. Reexecutar com revisão padrão `1`, validar metadata e hash, sem alterar a fonte candidata por esse erro de comando.
