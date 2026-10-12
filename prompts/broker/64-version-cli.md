# P64 rev1 — mqtt-broker --version

Entrada broker121153e/version0.11.1; confirmar HEAD. Arquivos Docker exportados
na raiz são preexistentes e serão preservados, fora do commit. Client inalterado.
Implementar --version/-V como argumento único, antes de logs/configuração/estado.
Versão de env!(CARGO_PKG_VERSION), stdout exato e exit0 mesmo com MQTT_CONFIG
inválido. Sem argumento, startup legado. Argumentos não suportados: erro estático
exit2 antes de configuração, sem reproduzir argv/secrets. Patchbroker0.11.2.
Escopo main/tests, manifests/lock/Dockerlabel, docs e registro. Gates fmt/test/
clippy/build e processo--version/negativos; .debUbuntu26 com lifecycleisolado,
Docker--version semenv/certs/volumes; manter interopmTLS via harnessP63.
Gerar dockerarchive/hash, tag/releaseGitHub comdeb e checksum autorizados.
DockerHub publicação manual pelo usuário; não fazerpushregistry. Prompts antes
das edições e revisões antes de correções. Sem alteração de protocolo/client.
