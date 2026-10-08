# Contexto verificado â€” XMQR

Estado de entrada: inspeÃ§Ã£o local em 2026-10-07; nÃ£o executados testes nesta tarefa.
Nome: XMQR. LicenÃ§a do cÃ³digo: MIT. Pacote: mqtt-broker 0.5.0, nÃ£o publicado;
binÃ¡rios mqtt-broker, mqtt-client e mqtt-admin. Rust ediÃ§Ã£o 2024, mÃ­nimo 1.88.
Tokio, Rustls/tokio-rustls, rumqttc no cliente, Serde/TOML, Argon2 e Tracing.

Leia [contrato-base](../contrato-base.md) e [cobertura](../COBERTURA.md).
O XMQR Ã© um broker experimental MQTT 3.1.1 usado pelo projeto consumidor
mqtt-broker. O consumidor nÃ£o Ã© o destino destas alteraÃ§Ãµes.

Existentes: TCP de laboratÃ³rio, TLS/mTLS seguro, autenticaÃ§Ã£o vinculada ao
fingerprint no modo seguro, ACL, pub/sub QoS 0/1/2, retained, sessÃµes persistentes,
UNSUBSCRIBE, filtros +/# e regra $, WAL/snapshot versionados e CRUD local de usuÃ¡rios.
NÃ£o existentes: MQTT 5.0, WebSockets, cluster, API administrativa,
configuraÃ§Ã£o geral versionada/reload e endpoints de mÃ©tricas/health/readiness.
NÃ£o hÃ¡ declaraÃ§Ã£o de prontidÃ£o de produÃ§Ã£o ou conformidade integral.

Limites atuais: tÃ³pico/filtro 1024 bytes UTF-8 compartilhados no broker e CLI apÃ³s P41. Payload 4096; pacote 64 KiB; 64 sessÃµes; 256 subscriptions
por sessÃ£o; 64 offline e 32 inflight. Limites fixos, sem capacidade medida garantida.
PersistÃªncia MQTT: agregado v1; WAL/snapshot v1. ACK condicionado ao commit.
ConfiguraÃ§Ã£o: ambiente para servidor; TOML somente usuÃ¡rios/ACL.

Plataforma: evidÃªncia documental Linux/WSL; administraÃ§Ã£o atÃ´mica de usuÃ¡rios
retorna Unsupported fora de Unix. Abrir a cÃ³pia Windows nÃ£o prova execuÃ§Ã£o nela.
Interop documentada: Mosquitto 2.0.18 em open-lab; ampliar TLS/mTLS, ACL e
clientes independentes. Metas de carga, SLA e requisitos de implantaÃ§Ã£o seguem abertos.
NÃ£o assumir IP, diretÃ³rio pessoal ou certificado de outra mÃ¡quina.

Origem do contexto anterior: [cÃ³pia preservada](../origem/broker/00-project-context.md).


## Atualizacao autorizada P42 - 0.6.0 local

Base tag v0.5.0 confirmada; Cargo.toml/lock agora 0.6.0 local. Last Will
implementado em codec/handler/ator com pending_wills duravel no documento v2
(leitura v1; WAL/snapshot v1). Retained preservado/revisado. As referencias
anteriores a Will ausente e documento MQTT v1 descrevem a base anterior.
Veja docs/last-will.md e registro P42. Proximo marco aguarda publicacao pelo
mantenedor; nenhuma tag/release criada aqui. MQTT5 continua fora do escopo.


## P43 - 0.7.0 em validaÃ§Ã£o

Base bc4cc55/tag v0.6.0 verificada. Monitoramento opcional implementado em
monitoring.rs, com HTTP loopback limitado, probe real do ator/writer e mÃ©tricas
de labels finitos. Cargo local 0.7.0; sem novas dependÃªncias ou mudanÃ§a MIT.
Documento MQTT v2 e quotas preservados. ReferÃªncias anteriores a endpoints
ausentes descrevem a base anterior. Aceite completo/release ainda pendentes.
Veja docs/monitoring.md e prompts/registros/P43-0.7.0.md (caminhos da raiz).
NÃ£o avanÃ§ar para 0.8, extrair clientes ou criar commit/push/tag nesta tarefa.

## C25 - projetos separados

Cliente independente em ../xmqr-client, pacote xmqr-client 0.7.0 local,
binÃ¡rio mqtt-client. Broker contÃ©m mqtt-broker/mqtt-admin; rumqttc nÃ£o integra
mais suas dependÃªncias. Gates Windows do cliente PASS; check/build/Clippy
all-targets do broker PASS. IntegraÃ§Ã£o Unix/monitor e aceite completo P43
pendentes; nÃ£o declarar release. Prompts histÃ³ricos continuam referÃªncia.
Cada melhoria do cliente segue seus prÃ³prios prompts e AGENTS. Ver registro C25.

## Checkpoint P43 validado - 2026-10-08

Mesmo repo via WSL/Rust1.99:72 testes e gates completos PASS,6 integraÃ§Ãµes
monitoring e9 Will PASS, incluindo1024UTF-8/retained/offline. Cliente independente
baseline commit26c1019 usado sem editar melhorias C26 paralelas. Bloqueios Unix
anteriores resolvidos. MIT/quotas/documento preservados. PublicaÃ§Ã£o0.7 fica com
usuÃ¡rio; sem commit/push/tag aqui. P44 seguranÃ§a dinÃ¢mica preparado apenas.
Mosquitto/TLS/mTLS externo NOT_RUN; sem conformidade integral ou produÃ§Ã£o.


## P44 - seguranÃ§a dinÃ¢mica, 0.8.0 local

Base HEAD e tag v0.7.0: 3a3dde7, confirmada antes da implementaÃ§Ã£o autorizada.
Bundle privado opt-in Linux/WSL com usuÃ¡rios, grupos, papÃ©is e ACL; reload por
SIGHUP local. Reload vÃ¡lido encerra todas as conexÃµes dinÃ¢micas e exige nova
autenticaÃ§Ã£o, preservando responsabilidade inbound QoS 2. Documento durÃ¡vel,
quotas, dependÃªncias e MIT preservados; cliente independente nÃ£o alterado.
A versÃ£o aguarda registro dos gates finais; nÃ£o hÃ¡ publicaÃ§Ã£o automÃ¡tica.
DocumentaÃ§Ã£o: docs/security/dynamic-security.md; evidÃªncia:
prompts/registros/P44-0.8.0.md (caminhos relativos Ã  raiz do repositÃ³rio).
ReferÃªncias anteriores a P44 apenas preparado descrevem checkpoints histÃ³ricos.
