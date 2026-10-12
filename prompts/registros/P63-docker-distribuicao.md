# P63 — broker0.11.1/client0.7.1 Docker

Base brokeraa5fda4/client890829f, árvores limpas. PromptsP63/C40 antes de arquivos.
Patch de empacotamento, sem mudança runtime/protocolo/quotas/CLI. Dockerfiles
OCIversion/revision/source/licenses eSIGTERM; runtimeDebianBookworm, UID10001.

Buildslinux/amd64PASS. Teste inicial aguardoustderr quando tracing usa stdout;
rev3 antes de corrigir. Depois assert procurava payload literal emJSON cuja
representação é payload_bytes; rev4 antes da decodificação. Restart recusou
SUBACK porque fixtureautorizava sensor/# e pediu sensor/value; rev5 diagnóstica
e rev6 reusam filtro permitido, sem ampliar ACL/runtime. Todas tentativas falhas
limparam containers/redes/volumes próprios. WSLDocker indisponível, docker.exe
interop recusado; rev2 adotou DockerWindows, OpenSSLGit e hash público WSL.

Builds finais de commits729981a87483c2576c63b813b142351b027aacaa e
c4f6abfa867c75c559f5e576406ad6f8a0f9d627; labels registram esses commits.
Commits finais acrescentam somente registros/documentação, sem mudar fonte de
runtime ou conteúdo de imagem. Report em target/p63-assets/docker-acceptance.json.

DOCKER_MTLS_PUB_SUB_RESTART_NEGATIVES_PASS: pub/subQoS1, bytes/topic/retain,
volume retido/restart e stop0 durável, CA e senha inválidas recusadas. Rootfs
read-only/capsALL removidas/no-new-privileges, sem ports do operador usados.
Artefatos docker save gzip, docker loadPASS e imageID idêntico antes/depois;
STOPSIGNAL=SIGTERM, UID10001 e versãoCLI0.7.1 verificados. Sem publishregistry.

NativeUbuntu26release builds e debPASS. Lifecycle em containerUbuntu26amd64:
install0.11.0/0.7.0, upgrade0.11.1/0.7.1, rollback, remove/purge,
preservação/docscmpPASS. Logs/builds emtarget, nenhum software real operado.

| Imagem exportada | SHA-256 |
| --- | --- |
| xmqr-broker-0.11.1-linux-amd64.tar.gz | 7c24e74c41d89912e178cdc59e443a38b6e1af957836f35a9cea24e5dbb7beaf |
| xmqr-client-0.7.1-linux-amd64.tar.gz | 3e8b8c5ee275057df36847f11086a50252d131108527405b176f74c9a1671384 |

Publicação autorizada: tagsv0.11.1/v0.7.1, prereleasescomdebs/checksums,
dockerarchives/checksums e report sem segredos. Tags antigas imutáveis.
Gates proporcionais: Docker/nativebuilds, integração real, package lifecycle,
ASTPython, links/diff e fonteRust igual às versões anteriores. Não repetir
suite funcional por labels/docs; nada ampliado unilateralmente.

Sólinux/amd64 testado. Dockerhost precisa de kernel/arquitetura/runtime
compatíveis; não homologar todasdistros/arm64 ou declarar produção/MQTT5.
Segredos gerados só volumes temporários e não incorporados nas imagens.
