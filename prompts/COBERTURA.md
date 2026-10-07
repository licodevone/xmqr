# Matriz de cobertura — inspeção em 2026-10-07

Estado baseado em leitura, não testes executados nesta tarefa. Evidências são
relativas à raiz XMQR; referências a testes significam código/documentação de
testes existente, não PASS novo. Os prompts novos têm critérios de aceite futuros.

| Capacidade | Estado verificado / limite | Evidência local | Prompts |
| --- | --- | --- | --- |
| Nome, pacote, licença, versão | XMQR, mqtt-broker 0.5.0 em desenvolvimento, MIT | Cargo.toml; LICENSE; VERSIONING.md | contexto; 40 |
| Arquitetura assíncrona | Tokio, módulos em pacote existente, Rust 2024/MSRV 1.88 | Cargo.toml; src/lib.rs; src/transport/mod.rs | 02–05; 39 |
| Codec 3.1.1 | CONNECT/CONNACK, QoS ACKs, SUB/UNSUB, PING, DISCONNECT | src/mqtt/codec.rs; src/mqtt/mod.rs | 04–05; 38 |
| QoS 0/1/2 | implementados, commit antes dos ACKs pertinentes | src/mqtt/mod.rs; router.rs; store.rs | 07; 25–28 históricos; 36; 39 |
| Sessões e takeover | CleanSession, offline QoS>0, gerações e vínculo principal | src/mqtt/router.rs; store.rs | 05; 08; 27 histórico; 39 |
| Retained | estado separado, payload vazio remove, replay/dedup | src/mqtt/router.rs; store.rs | 08; 29 histórico; 33; 36 |
| UNSUBSCRIBE | remoção literal e persistência | src/mqtt/codec.rs; mod.rs; router.rs | 27 histórico; 33; 36 |
| Wildcards +/#, níveis vazios, $ | existentes; sobreposição com QoS máximo aplicável | src/mqtt/topic.rs; router.rs; docs/architecture/adr-0002-topic-filters.md | 06; 33 atualizado; 36 |
| ACL literal e entrega/restore | deny-by-default, filtro exato concedido e match concreto | src/auth/mod.rs; router.rs; docs/security/auth-acl.md | 10; 23 histórico; 33; 34; 36 |
| TLS/mTLS, Argon2id, fingerprint | existentes no perfil seguro; CRL opcional | src/auth/mod.rs; transport/mod.rs; src/main.rs | 10; 23 histórico; 34; 36 |
| Quatro modos e estado por perfil | existentes; sem TLS só loopback; variáveis incompatíveis recusadas | src/main.rs; docs/laboratorio-mqtt-aberto.md | **34 novo** |
| CRUD de usuários | create/list/update-password/delete atômicos; Unix/WSL, sem provisionamento de certificado | src/bin/mqtt-admin/{main,users}.rs; docs/administracao-usuarios.md | **35 novo** |
| CLI atual | rumqttc; pub/sub, QoS, retained, CleanSession, count, senha privada e modos | src/bin/mqtt-client/{cli,credentials,session,tls}.rs | clients/19–23 históricos; **clients/24 novo** |
| Persistência e recuperação | agregado MQTT v1, WAL/snapshot v1, escritor exclusivo, fsync e quotas | src/mqtt/store.rs; src/persistence/{mod,actor}.rs | 25 histórico; **39 novo** |
| Limites e backpressure | pacote 64 KiB, payload 4096, 64 sessões, 256 assinaturas, 64 offline, 32 inflight | codec.rs; store.rs; router.rs; transport/mod.rs | 10; 14; 36; 39 |
| Limite tópico/filtro | **broker/CLI 1024 bytes UTF-8**, alinhados por P41; outros limites preservados | mqtt/mod.rs MAX_TOPIC_BYTES; topic.rs; cli.rs; CHANGELOG.md | 37 histórico da decisão; **41 implementado, resultados no registro** |
| Client ID e keep-alive | CLI restrita; recusa de ID vazio pendente; deadlines existentes sem matriz ampliada | cli.rs; codec.rs; mqtt/mod.rs; docs/conformance/mqtt311-status.md | **38 novo, proposta/validação** |
| Last Will | não implementado; flags recusadas | src/mqtt/codec.rs; matriz MQTT | 32 atualizado, proposta |
| MQTT 5.0 / WS / cluster | fora do núcleo atual, sem implementação comprovada | README.md; docs/ROADMAP.md; codec.rs | 09 futuro; 02/16 para avaliação, sem promessa |
| Logs vs métricas/health/reload | Tracing existente; endpoints e configuração geral versionada são futuros | src/main.rs; docs/ROADMAP.md | 11 proposta, 10/16 gates |
| Interop automatizada | script Mosquitto/fixtures; evidência documental open-lab, TLS/ACL externa incompleta | scripts/verify_interop.py; docs/conformance/mqtt311-status.md | 12; 15; **36 novo** |
| Fuzzing/carga/operação | cobertura ampla e benchmarks ainda pendentes; testes gerados não são campanha de fuzzing | docs/ROADMAP.md; docs/wildcard-subscriptions.md | 13–16, gates não aprovados aqui |
| Licenças, CI, release, clones | inventário/CI existentes; release ainda não publicada; sincronização não automática | scripts/license_inventory.py; .github/workflows; VERSIONING.md | **40 novo** |

## Incertezas e inconsistências preservadas fora de prompts/

- docs/architecture/rust-tokio-resilience.md ainda diz que sessões MQTT não
  estão integradas ao WAL; store.rs/router.rs mostram integração. P39 pede
  reconciliação em futuro escopo próprio, sem corrigir esse arquivo agora.
- P41 resolve a divergência broker256/CLI1024. Rollback para snapshots de 256 bytes exige backup compatível se houver nomes longos persistidos.
- Não foi verificado GitHub remoto, publicação, hardware, serviço ativo, build
  Windows, disponibilidade externa ou execução atual de testes.
- Os prompts de origem não comprovam autoria ou execução histórica do XMQR.
- Cobertura documental não prova cumprimento integral de cada requisito de
  conformidade, segurança, desempenho ou operação do prompt.


## Resultado P41 e configuração local

Limite compartilhado 1024 bytes implementado. PASS nos testes de tipos, wire,
CLI e ACL; recuperação Unix e interop desta revisão continuam pendentes. A suíte
Windows tem falhas esperadas de plataforma e Clippy geral tem avisos preexistentes:
não existe PASS global. Evidência: [registro P41](registros/P41-topicos-1024.md).

O app-server Codex 0.160.1 confirmou por skills/list as três skills XMQR habilitadas,
sem erros do projeto. Quatro agentes TOML estão estaticamente válidos; nenhum
foi acionado. Nova sessão com XMQR como cwd mantém descoberta/instruções adequadas.


## Retomada P41 em Unix

Em 2026-10-07, Rust 1.99/Ubuntu-26.04 validou a mesma copia: 74 testes PASS, incluindo recovery de nomes longos; pub/sub proprio QoS 0/1/2 e retained apos reinicio PASS. Fmt, inventario e build PASS. Clippy falha preexistente assert_is_empty em store.rs:296; interop Mosquitto NOT_RUN. Nao existe PASS global/release. Veja registro P41 e VALIDACAO-P41.json.


## P42 - 0.6.0 local validada

Last Will implementado e retained revisado:81 testes Rust e9 integracoes PASS;
fmt/Clippy/inventario/build PASS em WSL sobre a mesma copia Windows. Documento
MQTT v2 le v1; rollback exige backup anterior. MIT preservada. Veja
[registro P42](registros/P42-0.6.0.md) e VALIDACAO-P42.json. Mosquitto/TLS externo
nao executados. Proximo marco0.7 aguarda publicacao pelo mantenedor.
