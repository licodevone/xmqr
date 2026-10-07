# P42 - Incremento 0.6.0: retained e Last Will

Versao 1.0, 2026-10-07. Base verificada: HEAD59c9e70 e tag remota/local
v0.5.0. Working tree inicialmente limpo. Retained existente; Will recusado.

Implementar Will MQTT3.1.1 flags/QoS/retain/topic/payload no codec, ACL no
CONNECT e na publicacao, associacao a conexao e persistencia antes do CONNACK.
Cancelar por DISCONNECT duravel; publicar na queda/timeout/protocolo/takeover
ou recovery apos falha. Publicacao/remocao atomicas pelo ator com quotas.
Preservar retained atual e testar exclusao por payload vazio, wildcard,
1024UTF8, QoS0/1/2, takeover, sessoes e restart. Novo documento v2, leitura v1;
rollback somente backup completo anterior. Nao persistir credenciais.
Corrigir lint Clippy preexistente assert_is_empty para liberar gates autorizados.
Arquivos: codec/router/store/handler, tests, docs, Cargo.toml/lock, skills/context.
Gates fmt/test/clippy/inventario/build e integracao independente socket mais
cliente proprio em recursos temporarios WSL /mnt/d. Mosquitto NOT_RUN.
Sem MQTT5, alteracao MIT, instalacoes, commit/push/tag/release.
Fonte OASIS: MQTT-3.1.2-8..17, -24; MQTT-3.1.3-1; MQTT-3.14.4-3.
Proximos incrementos somente apos este marco estavel, prompt e gates proprios.
