# P64 — consulta de versão0.11.2

Base121153e/version0.11.1. Prompt criado antes das edições; arquivos Docker
preexistentes na raiz preservados, fora do commit. Client0.7.1 inalterado.
Main síncrono trata --version/-V único antes de chamar runtimeTokio/logs/config.
Versão do manifest, stdout exato/exit0; semargs startup normal; inválidos exit2
sem echo. Tests/version.rs verifica configuração ausente, RUST_LOG inválido,
ausência de estado e argumentos combinados/privados. Sem alteração do protocolo.

Ubuntu26/WSL:105 testesPASS, fmt/clippy-Dwarnings/buildPASS. Logs p64-tests.log
e p64-clippy.log emtarget. Native release build/deb0.11.2-1PASS. LifecycleUbuntu
container: installbroker0.11.1/client0.7.0, upgradebroker0.11.2/client0.7.1,
rollback/remove/purge/docscmp/preservaçãoPASS. Clientartefatos existentes, sem
nova releasecliente. Arquivos/credenciais/serviços em uso não foram operados.

Docker buildlinux/amd64 sourcecommitd5dd3511a4ebb2787400cef20137088e07cbb32a,
labels/version/revision eUID10001. Docker--version com MQTT_CONFIG inexistente,
semcerts/envválidoPASS, stdout mqtt-broker0.11.2 e exit0. HarnessP63 completo
mTLS/pubsubQoS1/restart-retained/SIGTERM/negativosCA-senhaPASS. Report em
target/p64-assets/docker-acceptance.json. Savegzip/load preservou imageID.
ArchiveSHA: deb2b2516bffeb8007ac822e386db86b71ef4e76105d00f8433ea6933dbd9068.

Patch0.11.2; tag/prereleaseGitHub autorizadas comdeb/hash, dockerarchive/hash
e report. Commit final acrescenta só este registro; runtime/imagem correspondem
ao sourcecommit do label. DockerHub permanece publicação manual do operador.
Nova imagem copiada à raiz solicitada, semGit; antiga não substituída.
