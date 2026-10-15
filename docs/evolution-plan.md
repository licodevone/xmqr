# Evolução do broker e dos clients — referência Mosquitto

Planejamento original P53, 2026-10-11; acompanhamento atualizado em 2026-10-13
por P80/C43/P81/P82/P83/P84/P85/C44/P86/P87/P88 e fechamentoP89–P95/C45–C46.
Versões publicadas atuais: broker/admin legado0.11.6; client independente0.9.0;
xmqr-admin independente0.1.0, com pin preservado. Fase3 aceita no recorte finito;
[aceite e distribuição](phase3-acceptance.md). MQTT5 continua fase6 futura.
O [plano detalhado de paridade](plano-paridade-mosquitto.md), atualizado em
2026-10-13 por P78/C42/P86/P88, fecha o planejamento de funções, dependências e gates
para broker/admin/client. Planejamento concluído não encerra as fases pendentes.
Estimativas para uma sequência de desenvolvimento
com dedicação regular, contadas do início da execução, não datas prometidas.
Cada fase depende do aceite anterior; recalcular prazo após medições e falhas.
O objetivo é paridade funcional relevante com Mosquitto, não copiar internals,
formatos privados ou prometer o mesmo desempenho. Este inventário agrupa
capacidades; não substitui auditoria opção por opção de uma versão Mosquitto.

## Base existente

Broker: MQTT3.1.1 QoS0/1/2, retained, sessões persistentes, filtros +/# e regra $,
UNSUBSCRIBE, keepalive, takeover e Last Will durável; TLS/mTLS, senha e ACL;
bundle de segurança com grupos/papéis e reload SIGHUP; WAL/snapshot, backup,
monitor HTTP opcional loopback, shutdown, systemd, Docker e deb Ubuntu26 amd64.
TOML geral P52 e quotas configuráveis foram aceitos e empacotados na fase 1.
Esses recursos
têm regressões locais, mas isso não prova conformidade completa nem produção.
Client CLI: publicação/assinatura, QoS, TLS/mTLS, retained/Will, reconexão,
diagnósticos e integração systemd/deb. Confirmar cobertura de cada nova opção
antes de anunciar equivalência com mosquitto_pub/mosquitto_sub.

## Checklist de execução — estado atual

Use `- [x] ~~Entrega concluída~~` para marcar e riscar o texto; use
`- [ ] Entrega pendente` para manter a tarefa aberta. Marcar somente após aceite,
com link para a evidência. Uma entrega parcial não conclui toda a fase.
Este checklist é o resumo atual; os checkpoints ao final preservam o histórico.

### Fase 1 — concluída

- [x] ~~Configuração TOML, precedência e limites de conexões TCP (P52/P54).~~
- [x] ~~Quotas de sessões, retained, assinaturas, offline e inflight; redução sem descarte (P55).~~
- [x] ~~Limites de pacote/payload e negativos no broker e client (P58/C38).~~
- [x] ~~Keepalive e timeout configuráveis e diagnósticos do client (C37/C38).~~
- [x] ~~Integrações Unix, recuperação e interoperabilidade Mosquitto open-lab.~~
- [x] ~~Pacotes Ubuntu 26 amd64: instalação, upgrade e rollback.~~
- [x] ~~Aceite combinado e marco broker 0.11.0/client 0.7.0 (P61/C39).~~

Evidências: [aceite da fase 1](phase1-acceptance.md),
[P61](../prompts/registros/P61-aceite-final-fase1.md) e
[C39](../../xmqr-client/prompts/registros/C39-release-fase1.md).

### Fase 2 — concluída no escopo validado

- [x] ~~Harness separado da CLI e baseline de RAM/CPU, conexões ociosas e latência PUBACK QoS1 com retained (P62).~~
- [x] ~~Medições QoS0/1/2, fan-out 1/8 e mTLS: 36 cenários com entregas conferidas (P72).~~
- [x] ~~Broker: conexões simultâneas, assinantes lentos, filas e saturação (60 cenários P80).~~
- [x] ~~Broker: corrigir shutdown TLS que retinha vaga do cliente não leitor; liberação comprovada (0.11.4).~~
- [x] ~~Client e broker: matriz Mosquitto2.0.22 mTLS/QoS/retained/Will/sessão e negativos (59 cenários C43).~~
- [x] ~~Broker: avaliar quotas por identidade; mantidas, com risco de isolamento explícito (ADR0006).~~
- [x] ~~Todos/software: relatório de capacidade e critérios de saída (P80/C43).~~
- [x] ~~ESP32: associação/IP/SNTP/mTLS e loopback1024bytes/QoS0/1/2 na COM4, primeira fatia P83.~~
- [x] ~~ESP32: retained create/update/replay/delete e bytes/flags por fixture wire independente do Rust/SDK na COM4 (P84).~~
- [x] ~~ESP32: Will/quebra de link, reconexão/backoff, negativos, memória/probe, retained restart e Mosquitto/QoS2 na DevKitV1 real (P85).~~

Evidências da parte concluída: [baseline P62](performance-baseline.md) e
[campanha P72](performance-fanout.md).
A medição não comprova throughput máximo nem capacidade de produção.
Veja [P80](performance-pressure.md), [aceite por componente](phase2-acceptance.md)
e [checklist ESP32](esp32-phase2-checklist.md). Fase2 global ACCEPTED apósP85.
MemóriaMCU é probe quantizado, não heap total; sem conformidade/produção
inferida. P85 não iniciou fase3; próxima fatia requer prompt próprio.

### Fase 3 — concluída no recorte validado

- [x] ~~B06: erros de leitura/gravação, ENOSPC/EIO, escrita curta, snapshot e corrupção; 54 casos determinísticos e patch0.11.5 (P86).~~
- [x] ~~B07: corpus/mutações reais com watchdog, três seeds e18processos PASS; não LibFuzzer/ASAN (P90/P95).~~
- [x] ~~B08:3repetições>=600s TCP/mTLS,30min8,946s reais, wire19/TLS12/matriz87 PASS (P91).~~
- [x] ~~C07:prazo total/jitter/cancelamento, idle90s real,63testes einterop TLS/mTLS/ACL ampliada (C45/C46).~~

EvidênciaB06: [falhas de armazenamento](storage-faults.md) e
[registroP86](../prompts/registros/P86-falhas-disco.md). Falhas injetadas não
equivalem a disco físico cheio/energia. [Aceite da fase3](phase3-acceptance.md):
B06/B07/B08/C07 ACCEPTED no recorte finito, com falhas históricas e limites.
Clones/licenças/ciclo de pacotes PASS; publicação coordenada em P92.
Não significa conformidade MQTT integral ou produção.

### Fases 4–5 — entregas restantes
- [x] ~~Admin independente0.1.0: CLI, painel local autenticado de leitura, prompts e release/deb/Docker próprio (P88).~~
- [ ] Fase 4: múltiplos listeners, políticas por endpoint, TLS sem certificado cliente quando configurado e rotação de certificados.
- [ ] Fase 4: perfis reutilizáveis do client e testes de rotação/erros de credenciais.
- [x] ~~P96/B09 parcial: até três endpoints mTLS adicionais com roteador, estado e limite de conexões compartilhados; integração cruzada e restart.~~
- [x] ~~C47/C05 parcial: perfis TOML opt-in do client, precedência de flags e caminhos relativos; integração mTLS e negativos.~~
- [x] ~~A05/U02 parcial: validação offline de bundle seguro no admin independente, sem escrita nem reload.~~
- [ ] Fase 5: gestão administrativa de grupos/papéis/ACL, auditoria e métricas operacionais.
- [x] ~~Client: --ignore-retained/--retained-only na saída; count filtrado e ACKs QoS1/2 preservados (C41).~~
- [ ] Fase 5: exclusão de tópicos, outros formatos de saída, repetição com intervalo e demais opções prioritárias pub/sub.
- [x] ~~Parcela operacional já entregue: ciclo de release experimental e pacotes com checksums/rollback (P61/C39/P63/P64/C40).~~

Evidências da parcela operacional: [P63](../prompts/registros/P63-docker-distribuicao.md),
[P64](../prompts/registros/P64-version-cli.md) e
[C40](../../xmqr-client/prompts/registros/C40-docker-distribuicao.md).
Evidência dos filtros: [C41](../../xmqr-client/prompts/registros/C41-filtros-retained.md).
As fases 4–5 continuam abertas; a entrega operacional não encerra a fase 5.
O [novo admin](https://github.com/licodevone/xmqr-admin) foi antecipado como
interface somente de leitura; A01/A02/A03 em seu repositório são IDs locais,
não o aceite de A02grupos/A03revogação/A09canal online desta matriz. Evidência:
[P88](../prompts/registros/P88-admin.md). mqtt-admin legado permanece intacto.

### Fases 6–9 e distribuição — pendentes

- [ ] Fase 6A: negociação MQTT5, codec, propriedades e reason codes no broker e client.
- [ ] Fase 6B: Clean Start, expiração de sessão/mensagem, Will Delay e migração do estado.
- [ ] Fase 6C: flow control, Receive Maximum, Maximum Packet Size, Topic Alias e propriedades de publicação.
- [ ] Fase 6D: opções de assinatura, Subscription Identifier, shared subscriptions e AUTH.
- [ ] Fase 7: WebSocket/WSS no broker e client, com regressão TCP/TLS.
- [ ] Fase 8: bridge, reconexão, mapeamento de tópicos e prevenção de loops.
- [ ] Fase 9: Windows nativo, serviço, instalador, persistência e permissões homologados.
- [ ] Distribuição: homologar instalação/units Ubuntu24, arm64 e repositório APT assinado.
- [ ] Extensões de paridade: avaliar plugins/hooks, TLS PSK, sockets Unix e opções avançadas conforme demanda.

Após cada entrega aceita, atualizar este checklist, a linha da fase no cronograma
e o link do registro. Manter itens em validação desmarcados e indicar seu bloqueio.

## Lacunas frente à referência

| Área | Situação no XMQR | Entrega necessária |
| --- | --- | --- |
| Configuração e quotas | ~~TOML e quotas globais configuráveis aceitos na fase1~~ | Limites por identidade/listener; rate limits e timeouts adicionais conforme contrato |
| Capacidade | ~~Baseline RAM/CPU/PUBACK QoS1 medida em P62~~; sem teto de produção medido | Ampliar QoS/fan-out/TLS e saturação; relatório de capacidade |
| Robustez | Recuperação e backup existentes, cobertura incompleta | Disco cheio, erro de escrita, pressão de filas, fuzzing, testes prolongados e matriz3.1.1 |
| Listeners | Um listener por processo/perfil | Múltiplos listeners, políticas por listener e TLS com senha sem exigir certificado cliente quando configurado |
| Administração | CRUD/backup legado; novo xmqr-admin0.1.0 com CLI e painel autenticado de agregados; bundle/SIGHUP no broker | Gestão segura de grupos/papéis/ACL, auditoria e contrato administrativo; plugins são trilha posterior |
| Métricas/logs | Monitor básico e tracing | Métricas operacionais, formatos/exportação definidos e decidir suporte MQTT $SYS |
| MQTT5 | Ausente | Codec/propriedades, negociação, sessões/expiração, fluxo, assinaturas e autenticação estendida |
| WebSocket | Ausente | WS/WSS no broker e conexão correspondente no client |
| Bridge | Ausente | Ligação entre brokers com TLS, reconexão, mapeamento de tópicos e proteção de loops |
| Distribuição | Deb26 amd64; sem APT próprio | Ubuntu24 validado, arm64, repositório APT assinado e política de upgrade |
| Windows nativo | Não homologado | Persistência/locks/CRUD/sinais adaptados, serviço Windows, instalador e testes |
| Clients | CLI própria; ~~keepalive/timeout e limites aceitos~~; sem paridade exaustiva | Perfis, saída/filtros, repetição e MQTT5; validar firmware ESP32 como consumidor |
| Extensibilidade | Sem API de plugins equivalente | Avaliar hooks de autenticação/ACL e integração externa depois de estabilizar o núcleo |

TLS PSK, sockets Unix, opções avançadas de TLS/logs, API de controle e políticas
administrativas são backlog explícito de paridade; definir demanda e testes
antes de adotar. Alta disponibilidade/cluster é estudo separado e não condição
para igualar um broker Mosquitto isolado.

## Cronograma recomendado

| Fase | Janela estimada | Broker | Client/consumidores | Critério de saída |
| --- | --- | --- | --- | --- |
| ~~1 — concluída~~ | ~~Semanas1–2~~ | ~~Quotas via TOML; redução validada; P52 empacotado~~ | ~~Diagnósticos de limites, testes de payload/pacote/fila e conexão~~ | ~~Defaults, negativos, estado preservado e install/upgrade/rollback aceitos P61/C39~~ |
| ~~2 — concluída~~ | Semanas3–4 (estimativa histórica) | ~~P62/P72/P80, saturação/quotas avaliadas~~ | ~~C43/Mosquitto e P85/ESP32 físico~~ | ~~Aceite combinado phase2-acceptance.md; métricas/método/limites registrados~~ |
| 3 | Semanas5–7 | Falhas de disco, fuzzing, pressão de filas e fechamento da matriz MQTT3.1.1 | Reconexão/backoff, cancelamento, diagnóstico e testes contra Mosquitto | Recuperação comprovada nos cenários; negativos; interop automatizada; pendências normativas listadas |
| 4 | Semanas8–10 | Listeners com políticas por endpoint, modos TLS e reload de certificados definido | Perfis de conexão, rotação e erros de certificado/credenciais | Isolamento de ACL; TLS/mTLS; rotação/rollback; nenhum laboratório remoto implicitamente habilitado |
| 5 | Semanas11–12 | Administração de bundle, auditoria, métricas e ciclo de release | Paridade prioritária pub/sub e documentação sincronizada | Operação sem editar segredos manualmente em casos cobertos; release com anexos/checksums e rollback |
| 6A | Semanas13–15 | Desenho MQTT5, codec, validação de propriedades e reason codes | Escolha explícita3.1.1/5; vetores e testes de negociação | Negativos normativos e coexistência3.1.1; apenas subconjunto5 anunciado |
| 6B | Semanas16–18 | Clean Start, Session Expiry, Message Expiry, Will Delay e estado versionado | Testes de expiração/reconexão; opções correspondentes | Crash/restart, migração e relógio/expiração tratados sem perda silenciosa |
| 6C | Semanas19–21 | Receive Maximum, Maximum Packet Size, Topic Alias e propriedades de publicação | Flow control, User Properties, Content Type, Response Topic/Correlation Data | Negociação bilateral, limites, QoS0/1/2 e persistência testados |
| 6D | Semanas22–24 | Opções de assinatura, Subscription Identifier, shared subscriptions e AUTH conforme contrato | No Local, Retain Handling/As Published, assinaturas compartilhadas e autenticação5 | Matriz5 por cláusula, interop externa, recursos ausentes declarados; sem alegação integral prematura |
| 7 | Semanas25–27 | WebSocket/WSS com limites e segurança equivalentes | Transporte WS/WSS e testes de browser quando existir consumidor | Regressão TCP/TLS, fragmentação, limites e desconexão aprovados |
| 8 | Semanas28–31 | Bridge incremental | CLI de diagnóstico; testes com Mosquitto nas duas pontas | Reconexão limitada, loops, QoS, retenção e ACL explícitos |
| 9 | Semanas32–35 | Windows nativo e extensões de paridade escolhidas | Serviço/instalador Windows e CLI homologada | Instalar/upgrade/remover, recuperação e permissões testados em Windows |

Reservar 20–30% de folga adicional; as 35 semanas são uma hipótese inicial de
planejamento, não previsão validada. MQTT5 pode exigir mais tempo após desenho
do estado durável. Não fixar tags0.11/0.12 antecipadamente; cada versão descreve
o conjunto efetivamente aprovado. Uma fase pode gerar várias entregas menores.

Distribuição Ubuntu24/26 e arm64 começa depois da fase3, com estimativa adicional
de 2–3 semanas. APT assinado depende de hospedagem/domínio, chave de assinatura
e política de manutenção; é publicação própria, distinta de GitHub Releases.
Pode ser antecipado sem bloquear MQTT5 quando houver disponibilidade.

## Sequência de execução de cada entrega

1. Criar e apresentar prompt no repositório responsável, com estado de entrada,
   escopo, requisitos normativos, migração, testes e critério de saída.
2. Implementar uma fatia utilizável no broker; implementar no client as opções
   necessárias para exercitá-la. Consumidores ESP32 permanecem fora do núcleo.
3. Validar unitários, negativos, integração broker/client e cliente independente
   Mosquitto; para texto, validar links/formatos sem repetir testes funcionais.
4. Se falhar, registrar o resultado, revisar o prompt antes de corrigir e repetir
   os checks afetados. Nenhuma etapa seguinte começa para esconder falhas.
5. Atualizar README, changelog, matriz de paridade e registro de evidências.
6. Commit/push após aceite. Tag imutável e prerelease apenas com binários/pacotes
   testados, notas, hashes e procedimento de upgrade/rollback. Versões independentes.

Fase2 encerrada por P85/C44, conforme [checklist de placa](esp32-phase2-checklist.md).
Próxima etapa: preparar uma fatia da fase3 (robustez); não foi executada nesta
campanha. SoftwareP80/C43 e placaP85 aceitos têm escopos/limitações próprios.
~~P55 — quotas do estado~~ foi aceito em P61; não é mais a próxima entrega.
Não iniciar MQTT5, WebSocket e bridge juntos. Reavaliar este cronograma
ao encerrar cada fase e registrar desvios nos prompts correspondentes.

## Fontes e evidências

- [Configuração oficial Mosquitto](https://mosquitto.org/man/mosquitto-conf-5.html): referência de listeners, quotas, TLS, plugins e bridges.
- [MQTT5 OASIS](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html): contrato normativo; não usar opções Mosquitto como especificação MQTT.
- [Configuração XMQR](architecture/configuration.md), [registro P52](../prompts/registros/P52-configuracao-toml.md) e [matriz3.1.1](conformance/mqtt311-status.md).

Estado baseado na leitura do código/documentação e nas evidências P52 anteriores;
esta tarefa de planejamento não executou novos testes funcionais.


## Histórico de execução

Os checkpoints abaixo retratam o estado em cada execução. Seus bloqueios antigos
não substituem o checklist atual; P61/C39 concluiu a fase 1 e P62 iniciou a fase 2.

## Retomada após P54 — 2026-10-11

Commit local 7d5f371: admissão TCP configurável por TOML/ambiente, default64,
faixa1..64, restart necessário. Quotas duráveis permanecem fixas. Registro
[P54](../prompts/registros/P54-limite-conexoes.md) informa 92 testes e gates WSL
aprovados, recusa/liberação TCP e 4 integrações C27. Revisão desta retomada
conferiu código e evidências, sem reexecutar testes ou verificar publicação remota.

[P55](../prompts/broker/55-quotas-estado.md) está preparado, não implementado:
sessões, retained, assinaturas, offline e inflight configuráveis com rejeição de
redução incompatível sem truncar dados. A fase1 continua aberta; payload/pacote,
client e instalação/upgrade precisam de avaliação própria antes do aceite.


## Execução local P55 — aceite pendente

Quotas lógicas implementadas localmente; validação portável Windows aprovada.
Recuperação durável e integração Linux/WSL pendentes: não há distribuição WSL
visível nesta sessão. A fase1 segue aberta e nenhuma tag/release de aceite foi criada.
Veja prompts/registros/P55-quotas-estado.md e retome gates Unix antes de avançar.

## Retomada paralela P55/C37 — 2026-10-11

Escopos preparados antes do código: P55 rev3/revisões posteriores e C37 rev4. Agentes independentes implementaram broker/client e revisaram os diffs; alterações preexistentes AGENTS.md do broker e .serena/project.yml do client foram preservadas.

P55 recebeu correção local para Will saturada: recusa encerra o ator/conexões, mantendo a imagem comprometida e a obrigação pendente; recuperação aguarda encerramento do writer em erro antes de retornar. Negativos cobrem startup real com imagens v1/v2 acima de cada quota, ausência de listener, arquivos duráveis idênticos e reabertura imediata. Harness isolado acrescenta limites N/N+1 e QoS0/1/2 com CLI independente. Fmt, Clippy, build e compilação dos testes passaram em Windows; a suíte geral tem falhas de fsync Unix, e os novos negativos duráveis foram ignorados nesta plataforma. Aceite P55 continua BLOCKED, sem tag/release. Resultados detalhados no [registro P55](../prompts/registros/P55-quotas-estado.md).

C37 foi implementado no client 0.6.0: --keepalive-seconds 1..65535 (default30) e --timeout-seconds 1..300 (default8), preservando reconexão, TLS/SAN, QoS e budgets existentes. Gates debug/release aprovados: 28 unitários e 17 wire em cada perfil, fmt, Clippy e builds. ZIP Windows portátil e SHA-256 verificados após extração. Commit local 6ee5aa87d0e1eb16c48c625408eeaf227197da14, tag anotada local v0.6.0 no mesmo commit. Push atômico do commit/tag falhou por credencial GitHub inacessível (wincredman); não houve publicação remota nem release Ubuntu. Detalhes no [registro C37](../../xmqr-client/prompts/registros/C37-timeout-keepalive.md).

A fase1 permanece aberta. Próxima retomada: aceitar P55 em Linux/WSL com recuperação, harness de quotas, regressão P54 e integrações pertinentes; depois preparar escopo próprio para payload/pacote e distribuição. A revisão identificou diferença na borda do teto64KiB: broker conta Remaining Length, client conta pacote completo; definir contrato uniforme e negativos antes de alterar esse limite. Instalação/upgrade/rollback e interoperabilidade externa permanecem pendentes. Não iniciar fase2 para contornar esses gates.

## Retomada de fechamento fase1 — P58/C38/P59/P60

Pedido explícito de finalizar fase1 executado em paralelo. BrokerP58 corrige teto para pacote completo65536 e reforça payload4096/N+1; clientC38 cobre SUBSCRIBE/payload, diagnósticos e recepção conservadora65531 de corpo (exceção1byte canônica explicitada). P59 adiciona lifecycle upgrade/rollback em container e runner único de gates Unix; .deb candidato passa a conter exemplo/guia TOML sem ativação automática. Portáveis passaram (brokercodec12 e client49), mas suíte geralbrokerWindows falha por fsyncUnix.

[Quadro de aceite atual](phase1-acceptance.md): ACCEPTANCE_BLOCKED. Ubuntu26 do operador está aberto e contém versões instaladas, mas não é acessível à conta lico\codexsandboxoffline desta sessão. O runner usa fontes/testes/estado temporários e pode ser executado no loginUbuntu, sem remover ou alterar instalações existentes. Lifecycle somente em container descartável. Aguarda evidência Unix/interop e pacotes; fase1 não foi artificialmente encerrada e fase2 não foi iniciada.

## Checkpoint de aceite P61/C39, 2026-10-11

Fase1 concluída no Ubuntu26/WSL: broker0.11.0/client0.7.0, configuração e
quotas, limites de pacotes, integrações e pacote install/upgrade/rollback aceitos.
Os BLOCKED anteriores desta página são históricos. Ver [aceite da fase1](phase1-acceptance.md).
Naquele checkpoint, fase2 ainda não havia sido executada. Posteriormente, P62
entregou a baseline inicial; a fase2 permanece em andamento, conforme checklist.
