# Matriz de cobertura â€” inspeÃ§Ã£o em 2026-10-07

Estado baseado em leitura, nÃ£o testes executados nesta tarefa. EvidÃªncias sÃ£o
relativas Ã  raiz XMQR; referÃªncias a testes significam cÃ³digo/documentaÃ§Ã£o de
testes existente, nÃ£o PASS novo. Os prompts novos tÃªm critÃ©rios de aceite futuros.

| Capacidade | Estado verificado / limite | EvidÃªncia local | Prompts |
| --- | --- | --- | --- |
| Nome, pacote, licenÃ§a, versÃ£o | XMQR, mqtt-broker 0.5.0 em desenvolvimento, MIT | Cargo.toml; LICENSE; VERSIONING.md | contexto; 40 |
| Arquitetura assÃ­ncrona | Tokio, mÃ³dulos em pacote existente, Rust 2024/MSRV 1.88 | Cargo.toml; src/lib.rs; src/transport/mod.rs | 02â€“05; 39 |
| Codec 3.1.1 | CONNECT/CONNACK, QoS ACKs, SUB/UNSUB, PING, DISCONNECT | src/mqtt/codec.rs; src/mqtt/mod.rs | 04â€“05; 38 |
| QoS 0/1/2 | implementados, commit antes dos ACKs pertinentes | src/mqtt/mod.rs; router.rs; store.rs | 07; 25â€“28 histÃ³ricos; 36; 39 |
| SessÃµes e takeover | CleanSession, offline QoS>0, geraÃ§Ãµes e vÃ­nculo principal | src/mqtt/router.rs; store.rs | 05; 08; 27 histÃ³rico; 39 |
| Retained | estado separado, payload vazio remove, replay/dedup | src/mqtt/router.rs; store.rs | 08; 29 histÃ³rico; 33; 36 |
| UNSUBSCRIBE | remoÃ§Ã£o literal e persistÃªncia | src/mqtt/codec.rs; mod.rs; router.rs | 27 histÃ³rico; 33; 36 |
| Wildcards +/#, nÃ­veis vazios, $ | existentes; sobreposiÃ§Ã£o com QoS mÃ¡ximo aplicÃ¡vel | src/mqtt/topic.rs; router.rs; docs/architecture/adr-0002-topic-filters.md | 06; 33 atualizado; 36 |
| ACL literal e entrega/restore | deny-by-default, filtro exato concedido e match concreto | src/auth/mod.rs; router.rs; docs/security/auth-acl.md | 10; 23 histÃ³rico; 33; 34; 36 |
| TLS/mTLS, Argon2id, fingerprint | existentes no perfil seguro; CRL opcional | src/auth/mod.rs; transport/mod.rs; src/main.rs | 10; 23 histÃ³rico; 34; 36 |
| Quatro modos e estado por perfil | existentes; sem TLS sÃ³ loopback; variÃ¡veis incompatÃ­veis recusadas | src/main.rs; docs/laboratorio-mqtt-aberto.md | **34 novo** |
| CRUD de usuÃ¡rios | create/list/update-password/delete atÃ´micos; Unix/WSL, sem provisionamento de certificado | src/bin/mqtt-admin/{main,users}.rs; docs/administracao-usuarios.md | **35 novo** |
| CLI atual | rumqttc; pub/sub, QoS, retained, CleanSession, count, senha privada e modos | src/bin/mqtt-client/{cli,credentials,session,tls}.rs | clients/19â€“23 histÃ³ricos; **clients/24 novo** |
| PersistÃªncia e recuperaÃ§Ã£o | agregado MQTT v1, WAL/snapshot v1, escritor exclusivo, fsync e quotas | src/mqtt/store.rs; src/persistence/{mod,actor}.rs | 25 histÃ³rico; **39 novo** |
| Limites e backpressure | pacote 64 KiB, payload 4096, 64 sessÃµes, 256 assinaturas, 64 offline, 32 inflight | codec.rs; store.rs; router.rs; transport/mod.rs | 10; 14; 36; 39 |
| Limite tÃ³pico/filtro | **broker/CLI 1024 bytes UTF-8**, alinhados por P41; outros limites preservados | mqtt/mod.rs MAX_TOPIC_BYTES; topic.rs; cli.rs; CHANGELOG.md | 37 histÃ³rico da decisÃ£o; **41 implementado, resultados no registro** |
| Client ID e keep-alive | CLI restrita; recusa de ID vazio pendente; deadlines existentes sem matriz ampliada | cli.rs; codec.rs; mqtt/mod.rs; docs/conformance/mqtt311-status.md | **38 novo, proposta/validaÃ§Ã£o** |
| Last Will | nÃ£o implementado; flags recusadas | src/mqtt/codec.rs; matriz MQTT | 32 atualizado, proposta |
| MQTT 5.0 / WS / cluster | fora do nÃºcleo atual, sem implementaÃ§Ã£o comprovada | README.md; docs/ROADMAP.md; codec.rs | 09 futuro; 02/16 para avaliaÃ§Ã£o, sem promessa |
| Logs vs mÃ©tricas/health/reload | Tracing existente; endpoints e configuraÃ§Ã£o geral versionada sÃ£o futuros | src/main.rs; docs/ROADMAP.md | 11 proposta, 10/16 gates |
| Interop automatizada | script Mosquitto/fixtures; evidÃªncia documental open-lab, TLS/ACL externa incompleta | scripts/verify_interop.py; docs/conformance/mqtt311-status.md | 12; 15; **36 novo** |
| Fuzzing/carga/operaÃ§Ã£o | cobertura ampla e benchmarks ainda pendentes; testes gerados nÃ£o sÃ£o campanha de fuzzing | docs/ROADMAP.md; docs/wildcard-subscriptions.md | 13â€“16, gates nÃ£o aprovados aqui |
| LicenÃ§as, CI, release, clones | inventÃ¡rio/CI existentes; release ainda nÃ£o publicada; sincronizaÃ§Ã£o nÃ£o automÃ¡tica | scripts/license_inventory.py; .github/workflows; VERSIONING.md | **40 novo** |

## Incertezas e inconsistÃªncias preservadas fora de prompts/

- docs/architecture/rust-tokio-resilience.md ainda diz que sessÃµes MQTT nÃ£o
  estÃ£o integradas ao WAL; store.rs/router.rs mostram integraÃ§Ã£o. P39 pede
  reconciliaÃ§Ã£o em futuro escopo prÃ³prio, sem corrigir esse arquivo agora.
- P41 resolve a divergÃªncia broker256/CLI1024. Rollback para snapshots de 256 bytes exige backup compatÃ­vel se houver nomes longos persistidos.
- NÃ£o foi verificado GitHub remoto, publicaÃ§Ã£o, hardware, serviÃ§o ativo, build
  Windows, disponibilidade externa ou execuÃ§Ã£o atual de testes.
- Os prompts de origem nÃ£o comprovam autoria ou execuÃ§Ã£o histÃ³rica do XMQR.
- Cobertura documental nÃ£o prova cumprimento integral de cada requisito de
  conformidade, seguranÃ§a, desempenho ou operaÃ§Ã£o do prompt.


## Resultado P41 e configuraÃ§Ã£o local

Limite compartilhado 1024 bytes implementado. PASS nos testes de tipos, wire,
CLI e ACL; recuperaÃ§Ã£o Unix e interop desta revisÃ£o continuam pendentes. A suÃ­te
Windows tem falhas esperadas de plataforma e Clippy geral tem avisos preexistentes:
nÃ£o existe PASS global. EvidÃªncia: [registro P41](registros/P41-topicos-1024.md).

O app-server Codex 0.160.1 confirmou por skills/list as trÃªs skills XMQR habilitadas,
sem erros do projeto. Quatro agentes TOML estÃ£o estaticamente vÃ¡lidos; nenhum
foi acionado. Nova sessÃ£o com XMQR como cwd mantÃ©m descoberta/instruÃ§Ãµes adequadas.


## Retomada P41 em Unix

Em 2026-10-07, Rust 1.99/Ubuntu-26.04 validou a mesma copia: 74 testes PASS, incluindo recovery de nomes longos; pub/sub proprio QoS 0/1/2 e retained apos reinicio PASS. Fmt, inventario e build PASS. Clippy falha preexistente assert_is_empty em store.rs:296; interop Mosquitto NOT_RUN. Nao existe PASS global/release. Veja registro P41 e VALIDACAO-P41.json.


## P42 - 0.6.0 local validada

Last Will implementado e retained revisado:81 testes Rust e9 integracoes PASS;
fmt/Clippy/inventario/build PASS em WSL sobre a mesma copia Windows. Documento
MQTT v2 le v1; rollback exige backup anterior. MIT preservada. Veja
[registro P42](registros/P42-0.6.0.md) e VALIDACAO-P42.json. Mosquitto/TLS externo
nao executados. Proximo marco0.7 aguarda publicacao pelo mantenedor.


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
