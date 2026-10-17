# Evolução do broker e dos clients — referência Mosquitto

Planejamento original P53, 2026-10-11; checklist atualizado em 2026-10-17.
Versões publicadas atuais: broker/admin legado0.26.0, client independente0.24.0
e xmqr-admin independente0.8.0. Fases1–5 aceitas em seus recortes documentados;
a fase6A avançou para publicação, assinatura, cancelamento, diagnósticos e
propriedades informativas de CONNECT MQTT5 QoS0/1/2 (P115–P123/C57–C64);
segue aberta.
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
- [x] ~~Fase 4/software broker: múltiplos listeners mTLS, políticas estáticas por endpoint, TLS sem certificado cliente quando configurado e rotação transacional de certificados.~~
- [x] ~~Fase 4/software client: perfis reutilizáveis com precedência CLI/ambiente/TOML, mTLS/TLS-senha e negativos de credenciais/rotação.~~
- [x] ~~P96/B09 parcial: até três endpoints mTLS adicionais com roteador, estado e limite de conexões compartilhados; integração cruzada e restart.~~
- [x] ~~P101/B09: arquivos de usuários/ACL por endpoint mTLS, principal e client ID isolados, roteador/estado/limite comuns; replay retained após restart.~~
- [x] ~~P97/B10: modo TLS com senha e ACL sem certificado cliente, opt-in; QoS0/1/2 e negativos CA/SAN/senha/ACL.~~
- [x] ~~P98/B12: decisão de campos recarregáveis e restart-only, transação sem publicação parcial.~~
- [x] ~~P100/B11: rotação SIGUSR1 de certificado/chave/CA/CRL nos endpoints mTLS e TLS-senha, com validação, rollback e conexões ativas preservadas.~~
- [x] ~~P102/E02: campanha física de rotação/revogação na ESP32 COM4, com certificado, CA, CRL, recusas e recuperação.~~ [Evidência](phase4-acceptance.md).
- [x] ~~C47/C05 parcial: perfis TOML opt-in do client, precedência de flags e caminhos relativos; integração mTLS e negativos.~~
- [x] ~~A05/U02 parcial: validação offline de bundle seguro no admin independente, sem escrita nem reload.~~
- [x] ~~Fase 4 concluída no escopo finito B09/B10/B11/B12/C05/E02.~~ [Aceite](phase4-acceptance.md).
- [x] ~~Fase 5: gestão administrativa de grupos/papéis/ACL, auditoria e métricas operacionais no escopo finito da matriz.~~ [Aceite](phase5-acceptance.md).
- [x] ~~Fase 5/A04: contrato do canal administrativo local decidido em ADR 0001 (P105).~~
- [x] ~~Fase 5/B14: decisão de não gerar tópicos $SYS; monitor HTTP existente preservado (P106).~~
- [x] ~~Fase 5/A09 parcial: P107 entrega status e primeiro reload local autenticado, com hash/CAS e recibo auditável no mesmo commit durável; teste de processo e restart.~~
- [x] ~~Fase 5/A09 parcial: CLI independente aplica bundle e consulta recibos; P108 lista sessões/retained com paginação e sem payload.~~
- [x] ~~Fase 5/A07 parcial: exclusão de retained por operator com recibo durável e deduplicação; documento MQTT v4 lê v3.~~
- [x] ~~Fase 5/A07: inventário paginado, exclusão retained e desconexão de sessão ativa com Will/QoS2 e recibo no commit, provados com MQTT real e restart (P108/A08).~~
- [x] ~~Fase 5/A02/A03: editor de grupo/papel/ACL, aplicação online e revogação de usuário com conexão encerrada, nova autenticação negada e inbound QoS2 preservado após restart (P110, laboratório local).~~
- [x] ~~Fase 5/A05 parcial: auditoria paginada operator e consulta por ID, sem payload/segredos; retenção limitada a 128 sem descarte.~~
- [x] ~~Fase 5/B13: monitor loopback inclui contadores administrativos de cardinalidade fixa e ocupação de recibos, sem labels privados.~~
- [x] ~~Fase 5/A05: exportação privada e rotação atômica de auditoria, épocas duráveis e recusa de replay; documento MQTT v5.~~
- [x] ~~Fase 5/A08: diagnóstico sem mutação de bundle, backup, espaço e versões, com saída redigida.~~
- [x] ~~Fase 5/A09: concorrência, limites, falha WAL, restart, auditoria consultável/retenção e aceite local do canal.~~
- [x] ~~Client: --ignore-retained/--retained-only na saída; count filtrado e ACKs QoS1/2 preservados (C41).~~
- [x] ~~Fase 5/client C03: exclusão local de tópicos com count após filtros e ACKs preservados (C52).~~
- [x] ~~Fase 5/client C04: repetição finita de publicação com intervalo monotônico e sem replay incerto (C53).~~
- [x] ~~Fase 5/client C06: decisão e implementação de saída hex/raw sem ambiguidade binária (C54).~~
- [x] ~~Fase 5/client C08: Will binário por arquivo limitado e validado antes da rede (C55).~~
- [x] ~~Fase 5: aceite global do broker, admin e client, com canal A09 e auditoria operacional no recorte local Linux/WSL.~~ [Evidência](phase5-acceptance.md).
- [x] ~~Fase 5: tags e prereleases experimentais do broker0.15.0, admin0.4.0 e client0.13.0 com checksums e limites publicados.~~ [P113](../prompts/registros/P113-release-fase5.md).
- [x] ~~Parcela operacional já entregue: ciclo de release experimental e pacotes com checksums/rollback (P61/C39/P63/P64/C40).~~

Evidências da parcela operacional: [P63](../prompts/registros/P63-docker-distribuicao.md),
[P64](../prompts/registros/P64-version-cli.md) e
[C40](../../xmqr-client/prompts/registros/C40-docker-distribuicao.md).
Evidência dos filtros: [C41](../../xmqr-client/prompts/registros/C41-filtros-retained.md).
A fase 4 e a fase 5 foram aceitas nos respectivos escopos finitos; veja
[fase 4](phase4-acceptance.md) e [fase 5](phase5-acceptance.md). O painel web
administrativo continua somente leitura; o CLI usa o canal local autenticado.
O [novo admin](https://github.com/licodevone/xmqr-admin) foi antecipado como
interface somente de leitura; A01/A02/A03 em seu repositório são IDs locais,
não o aceite de A02grupos/A03revogação/A09canal online desta matriz. Evidência:
[P88](../prompts/registros/P88-admin.md). mqtt-admin legado permanece intacto.

### Fases 6–9 e distribuição — pendentes

- [x] ~~Fase 6A/P114 parcial: recusa de CONNECT nível 5 com CONNACK MQTT 5 `0x84`, fechamento e ausência de commit; MQTT 5 ainda não é aceito.~~ [Estado](conformance/mqtt5-status.md) e [evidência](../prompts/registros/P114-recusa-connect-mqtt5.md).
- [x] ~~Fase 6A/P115/C57 parcial: CONNECT5 limpo e publicação QoS0/1 sem propriedades no broker/client, entrega cruzada a assinante 3.1.1.~~ [Estado](conformance/mqtt5-status.md), [broker](../prompts/registros/P115-publicacao-mqtt5-inicial.md) e [client](../../xmqr-client/prompts/registros/C57-publicacao-mqtt5-inicial.md).
- [x] ~~Fase 6A/P116/C58 parcial: SUBSCRIBE/SUBACK MQTT5 QoS0/1 sem propriedades avançadas, entrega viva/retained e PUBACK; client sub5, integração cruzada e Mosquitto.~~ [Broker](../prompts/registros/P116-assinatura-mqtt5-inicial.md) e [client](../../xmqr-client/prompts/registros/C58-assinatura-mqtt5-inicial.md).
- [x] ~~Distribuição experimental do subconjunto P115/P116/C57/C58: tags independentes v0.16.0/v0.14.0, pacotes Ubuntu26, imagens numeradas e prereleases com SHA-256/rollback.~~ [P117](../prompts/registros/P117-release-0.16.0.md) e [C59](../../xmqr-client/prompts/registros/C59-release-0.14.0.md).
- [x] ~~P118: investigar falha intermitente de lock no teste de snapshot e restaurar gate CI de `main`.~~ [Triagem](../prompts/registros/P118-investigar-lock-snapshot-ci.md); recorrência tratada em [P125](../prompts/registros/P125-liberacao-lock-store.md), monitorar novos runs.
- [x] ~~Fase 6A/P119/C60 parcial: PUBACK MQTT 5 `0x87` para ACL negada em QoS1 sem commit; client mostra motivos de PUBACK/SUBACK.~~ [Broker](../prompts/registros/P119-puback-mqtt5-acl.md) e [client](../../xmqr-client/prompts/registros/C60-diagnostico-reason-code-mqtt5.md); gates locais, integração real e CIs PASS.
- [x] ~~Fase 6A/P120/C61 parcial: SUBACK MQTT 5 `0x87` para ACL negada sem commit total; client mostra motivo de CONNACK recusado.~~ [Broker](../prompts/registros/P120-suback-mqtt5-acl.md) e [client](../../xmqr-client/prompts/registros/C61-connack-mqtt5-reason.md); gates locais, integração real e CIs PASS.
- [x] ~~Fase 6A/P121/C62 parcial: UNSUBSCRIBE/UNSUBACK MQTT 5 com motivo por filtro e confirmação antes do encerramento do client.~~ [Broker](../prompts/registros/P121-unsubscribe-mqtt5.md) e [client](../../xmqr-client/prompts/registros/C62-unsubscribe-mqtt5.md); gates locais, integração real e CIs PASS.
- [x] ~~Fase 6A/P122/C63 parcial: pub/sub MQTT 5 QoS2 com PUBREC/PUBREL/PUBCOMP, recusa ACL sem commit e interop Mosquitto 2.0.22 nas duas direções.~~ [Broker](../prompts/registros/P122-qos2-mqtt5.md) e [client](../../xmqr-client/prompts/registros/C63-qos2-mqtt5.md); gates locais, integração real e CIs PASS.
- [x] ~~Fase 6A/P123/C64 parcial: propriedades informativas de CONNECT MQTT 5 no broker/client, gates locais, integração e CIs PASS.~~ [Broker](../prompts/registros/P123-connect-properties-mqtt5.md) e [client](../../xmqr-client/prompts/registros/C64-connect-properties-mqtt5.md).
- [x] ~~P125: liberação explícita do lock de escritor após falha de snapshot e restauração da CI.~~ [Evidência](../prompts/registros/P125-liberacao-lock-store.md).
- [x] ~~Distribuição P124/C65: tags independentes v0.17.0/v0.15.0, pacotes Ubuntu26, imagens numeradas e prereleases com SHA-256/rollback.~~ [Broker](../prompts/registros/P124-release-0.17.0.md) e [client](../../xmqr-client/prompts/registros/C65-release-0.15.0.md).
- [x] ~~Fase 6A/P126 parcial: ACKs de sucesso e DISCONNECT normal MQTT 5 com motivo explícito/propriedades vazias; gates locais, integração e CI PASS.~~ [Evidência](../prompts/registros/P126-ack-disconnect-mqtt5.md).
- [x] ~~Fase 6B/P127/C66 parcial: Clean Start separado de Session Expiry 0/infinita, Session Present, retomada de QoS1 offline após reinício; gates locais, Mosquitto e CIs PASS.~~ [Broker](../prompts/registros/P127-sessao-mqtt5-zero-infinita.md) e [client](../../xmqr-client/prompts/registros/C66-sessao-mqtt5-zero-infinita.md).
- [x] ~~Fase 6B/P128/C67 parcial: Session Expiry finita com documento v6, remoção automática e CLI correspondente; gates locais e CIs PASS.~~ [Broker](../prompts/registros/P128-expiracao-finita-sessao-mqtt5.md) e [client](../../xmqr-client/prompts/registros/C67-expiracao-finita-sessao-mqtt5.md).
- [x] ~~Distribuição P129/C68: tags independentes v0.18.0/v0.16.0, pacotes Ubuntu26, imagens numeradas e prereleases com SHA-256/rollback.~~ [Broker](../prompts/registros/P129-release-0.18.0.md) e [client](../../xmqr-client/prompts/registros/C68-release-0.16.0.md).
- [x] ~~Fase 6B/P130/C69 parcial: Message Expiry em PUBLISH, limpeza de retidos/offline, documento v7 e opção do client; validação local e CIs PASS.~~ [Broker](../prompts/registros/P130-message-expiry-mqtt5.md) e [client](../../xmqr-client/prompts/registros/C69-message-expiry-mqtt5.md).
- [x] ~~Fase 6B/P131 parcial: Session Expiry no DISCONNECT MQTT 5, transição durável e negativos; validação local e CI PASS.~~ [Broker](../prompts/registros/P131-disconnect-session-expiry-mqtt5.md).
- [x] ~~Fase 6B/P132/C70 parcial: Will Delay MQTT 5, publicação/cancelamento duráveis, documento v8, client com opção CLI; testes locais, TCP real, Mosquitto e CI PASS.~~ [Broker](../prompts/registros/P132-will-delay-mqtt5.md) e [client](../../xmqr-client/prompts/registros/C70-will-delay-mqtt5.md).
- [x] ~~Distribuição P133/C71: tags independentes v0.19.0/v0.17.0, pacotes Ubuntu26, imagens numeradas e prereleases com SHA-256/rollback.~~ [Broker](../prompts/registros/P133-release-0.19.0.md) e [client](../../xmqr-client/prompts/registros/C71-release-0.17.0.md).
- [x] ~~Validação física P135: ESP32 COM4 publicou cinco amostras simuladas variáveis QoS 1; broker e subscriber 0.19.0/0.17.0 no Ubuntu/WSL confirmaram tópico, sequência e payload em duas execuções; laboratório temporário limpo.~~ [Evidência](../prompts/registros/P135-esp32-telemetria-wsl.md). É ensaio MQTT 3.1.1 e não encerra a fase 6.
- [x] ~~Fase 6C/P134/C72 parcial: Receive Maximum de CONNECT MQTT 5 limita PUBLISH QoS1/2 vivo, retained, offline e replay; client expõe `--receive-maximum`; gates locais, interop e CIs PASS.~~ [Broker](../prompts/registros/P134-receive-maximum-mqtt5.md) e [client](../../xmqr-client/prompts/registros/C72-receive-maximum-mqtt5.md). A fase 6C permanece aberta.
- [x] ~~Fase 6C/P136/C73 parcial: Maximum Packet Size do CONNECT MQTT 5 limita saída do broker em bytes completos; PUBLISH excedente é descartado com conclusão durável da obrigação QoS; client expõe `--maximum-packet-size`; gates e CIs PASS.~~ [Broker](../prompts/registros/P136-maximum-packet-size-mqtt5.md) e [client](../../xmqr-client/prompts/registros/C73-maximum-packet-size-mqtt5.md). A fase 6C permanece aberta.
- [x] ~~Distribuição P137/C74: tags v0.20.0/v0.18.0, pacotes Ubuntu26, imagens numeradas e prereleases com manifesto, SHA-256 e rollback.~~ [Broker](../prompts/registros/P137-release-0.20.0.md) e [client](../../xmqr-client/prompts/registros/C74-release-0.18.0.md). Fases 6A–6D ainda abertas.
- [x] ~~Fase 6C/P138 parcial: Topic Alias de entrada MQTT 5 limitado a 16 por conexão, reset em reconnect, ACL sobre tópico resolvido e fallback de CONNACK sob limite de pacote; integração e CI PASS.~~ [Evidência](../prompts/registros/P138-topic-alias-entrada-mqtt5.md). Alias de saída e aceite global 6C pendentes.
- [x] ~~Fase 6C/P139/C75 parcial: broker envia Topic Alias quando o assinante MQTT 5 anuncia suporte; client resolve tópico recebido; testes QoS0/1/2, retained, restart, limites e CIs PASS.~~ Mosquitto 2.0.22 rejeita o segundo pacote abreviado válido até em fixture isolada; essa direção externa não está homologada. [Broker](../prompts/registros/P139-topic-alias-saida-mqtt5.md) e [client](../../xmqr-client/prompts/registros/C75-topic-alias-maximum-mqtt5.md). Propriedades de publicação e aceite global 6C pendentes.
- [x] ~~Distribuição P140/C76: tags 0.21.0/0.19.0, pacotes Ubuntu26, imagens numeradas e prereleases com manifesto, SHA-256 e rollback verificados.~~ [Broker](../prompts/registros/P140-release-0.21.0.md) e [client](../../xmqr-client/prompts/registros/C76-release-0.19.0.md). Fases 6A–6D seguem abertas.
- [x] ~~Fase 6C/P141/C77 parcial: Payload Format Indicator e Content Type no PUBLISH MQTT 5, documento v9, flags do publisher, TCP real, Mosquitto e CIs PASS.~~ [Broker](../prompts/registros/P141-publish-payload-format-content-type-mqtt5.md) e [client](../../xmqr-client/prompts/registros/C77-publish-payload-format-content-type-mqtt5.md). Metadados adicionais P142/C78 aceitos depois; fase 6C global aberta.
- [x] ~~Fase 6C/P142/C78 parcial: Response Topic, Correlation Data e User Property no PUBLISH MQTT 5, documento v10 e flags do publisher; TCP real, Mosquitto e CIs PASS.~~ [Broker](../prompts/registros/P142-publish-request-properties-mqtt5.md) e [client](../../xmqr-client/prompts/registros/C78-publish-request-properties-mqtt5.md). Revisão global de flow control ainda pendente.
- [x] ~~Distribuição P143/C79: tags 0.22.0/0.20.0, pacotes Ubuntu26, imagens numeradas e prereleases com manifesto, SHA-256 e rollback verificados.~~ [Broker](../prompts/registros/P143-release-0.22.0.md) e [client](../../xmqr-client/prompts/registros/C79-release-0.20.0.md). Fases 6A–6D e 7–9 ainda abertas.
- [x] ~~Fase 6C/C80 parcial: `sub --protocol-version 5 --output jsonl` exibe metadados PUBLISH, com binário hexadecimal e pares de usuário ordenados; QoS0/1/2, retained/restart, Mosquitto e CI PASS.~~ [Evidência](../../xmqr-client/prompts/registros/C80-subscriber-publish-metadata-mqtt5.md). O fluxo de envio ainda requer revisão; fase 6C global aberta.
- [x] ~~Fase 6C/P144 parcial: CONNACK MQTT 5 anuncia Receive Maximum inbound 1..32 conforme quota configurada quando cabe; negativos de excesso, restart, Mosquitto e CI PASS.~~ [Evidência](../prompts/registros/P144-connack-receive-maximum-mqtt5.md). Nos limites de pacote 5..7 e 10..15 a propriedade é omitida para preservar o fallback anterior; fase 6C global aberta.
- [x] ~~Fase 6C/C81 parcial: client repete PUBLISH MQTT 5 com confirmação sequencial, propriedades preservadas, negativos de recusa/timeout, broker XMQR, Mosquitto e CI PASS.~~ [Evidência](../../xmqr-client/prompts/registros/C81-repeat-publish-mqtt5.md). Não há mensagens MQTT 5 simultâneas nem Topic Alias compacto; fase 6C global aberta.
- [x] ~~Distribuição P145/C82: broker 0.23.0 e client 0.21.0 com pacotes, imagens numeradas, ciclo de upgrade/rollback, checksums, tags e prereleases.~~ [Broker](../prompts/registros/P145-release-0.23.0.md) e [client](../../xmqr-client/prompts/registros/C82-release-0.21.0.md). Fases 6A–6D e 7–9 continuam abertas.
- [x] ~~Fase 6C/C83 parcial: Topic Alias compacto no publisher MQTT 5 em repetição, com limite negociado e interop XMQR/Mosquitto; CI PASS.~~ [Evidência](../../xmqr-client/prompts/registros/C83-publish-topic-alias-mqtt5.md). Fase 6C global aberta.
- [x] ~~Fase 6C/P146 parcial: sessão QoS2 retomada com quota durável cheia responde PUBREC 0x97 sem perder mensagem anterior; TCP real e CI PASS.~~ [Evidência](../prompts/registros/P146-qos2-resume-quota-mqtt5.md). Fase 6C global aberta.
- [x] ~~Fase 6D/P147/C84 parcial: Retain Handling 0/1/2 por filtro, sessão persistente/restart, interop Mosquitto e CIs PASS.~~ [Broker](../prompts/registros/P147-retain-handling-mqtt5.md) e [client](../../xmqr-client/prompts/registros/C84-retain-handling-mqtt5.md). Fase 6D global aberta.
- [x] ~~Fase 6D/C85 parcial: client envia No Local e Retain As Published por filtro MQTT 5; wire, Mosquitto e CI PASS.~~ [Evidência](../../xmqr-client/prompts/registros/C85-no-local-retain-as-published-mqtt5.md). Broker P148 em validação; fase 6D global aberta.
- [x] ~~Fase 6D/P148 parcial: broker aplica No Local e Retain As Published em sessão durável v11; TCP QoS0/1/2, restart e CI PASS.~~ [Evidência](../prompts/registros/P148-no-local-retain-as-published-mqtt5.md). Admin 0.6.0 lê v11 após [A14](../../xmqr-admin/prompts/registros/A14-core-v11-release-0.6.md); fase 6D global aberta.
- [x] ~~Distribuição P149/C86: broker/admin legado 0.24.0, client 0.22.0, estado v11, pacotes/imagens, ciclo de upgrade/rollback, tags e prereleases verificados.~~ [Broker](../prompts/registros/P149-release-0.24.0.md) e [client](../../xmqr-client/prompts/registros/C86-release-0.22.0.md). Rollback de estado v11 requer backup privado v10.
- [x] ~~Admin A12/A13: core broker 0.23.0 e estado v10 aceitos; admin independente 0.5.0 distribuído com pacotes, imagem numerada, tag e prerelease verificadas.~~ [A12](../../xmqr-admin/prompts/registros/A12-core-broker-0.23-compat.md) e [A13](../../xmqr-admin/prompts/registros/A13-release-core-0.23.md). Painel de escrita e fase 9 seguem abertos.
- [x] ~~Admin A14: core broker 0.24.0/estado v11, backup offline e admin independente 0.6.0 distribuído com CI, pacote, imagem, tag e prerelease verificados.~~ [Evidência](../../xmqr-admin/prompts/registros/A14-core-v11-release-0.6.md). Painel de escrita e fase 9 seguem abertos.
- [x] ~~Fase 6D/C87 parcial: client envia Subscription Identifier MQTT 5 e exibe IDs em JSONL; wire, Mosquitto e CI PASS.~~ [Evidência](../../xmqr-client/prompts/registros/C87-subscription-identifier-mqtt5.md). Broker P150 aceito; fase 6D global aberta.
- [x] ~~Fase 6D/P150 parcial: broker Subscription Identifier por filtro com estado v12, TCP QoS0/1/2, retained/offline/restart e negativos; CI PASS.~~ [Registro](../prompts/registros/P150-subscription-identifier-mqtt5.md). Admin 0.7.0 lê v12 após A15; fase 6D global aberta.
- [x] ~~Distribuição P151/C88: broker/admin legado 0.25.0 e client 0.23.0, pacotes/imagens, ciclo descartável de upgrade/downgrade, tags e prereleases verificados.~~ [Broker](../prompts/registros/P151-release-0.25.0.md) e [client](../../xmqr-client/prompts/registros/C88-release-0.23.0.md). Estado v12 exige backup privado v11 para rollback; admin independente 0.7.0 o lê após A15.
- [x] ~~Admin A15: core broker 0.25.0/estado v12, backup offline e admin independente 0.7.0 distribuído com CI, pacote, imagem, tag e prerelease verificados.~~ [Evidência](../../xmqr-admin/prompts/registros/A15-core-v12-release-0.7.md). Rollback de v12 exige backup privado v11 anterior; painel de escrita e fase 9 seguem abertos.
- [x] ~~Fase 6D/C89 parcial: client valida `$share/grupo/filtro` MQTT 5, respeita CONNACK de indisponibilidade e passou com dois consumidores no Mosquitto 2.0.22 e CI.~~ [Evidência](../../xmqr-client/prompts/registros/C89-shared-subscriptions-mqtt5.md). No marco C89, broker XMQR 0.25.0 ainda não distribuía grupos; fase 6D global aberta.
- [x] ~~Fase 6D/P152 parcial: broker 0.25.0 anuncia indisponibilidade de shared subscriptions e recusa `$share/` com 0x9E; TCP e CI PASS.~~ [Registro](../prompts/registros/P152-shared-subscription-capability.md). P153 substitui esse comportamento na árvore posterior; fase 6D global aberta.
- [x] ~~Fase 6D/P153 parcial: distribuição compartilhada MQTT 5 entre sessões temporárias ativas, sem retained inicial; dois grupos, QoS0/1/2, client e CI PASS.~~ Sessões persistentes e AUTH ainda pendentes neste marco. [Registro](../prompts/registros/P153-live-shared-subscriptions-mqtt5.md).
- [x] ~~Fase 6D/P154 parcial: grupos compartilhados MQTT 5 persistentes no estado v13, fila offline e retomada QoS2; testes e CI PASS.~~ Admin A16 distribuído; AUTH e recomendação de redistribuição QoS1 após término da sessão seguem pendentes. [Registro](../prompts/registros/P154-durable-shared-subscriptions-mqtt5.md).
- [x] ~~Distribuição P155/C90/A16: broker 0.26.0, client 0.24.0 e admin independente 0.8.0, com estado v13; CI, pacotes, imagens, rollback, tags e prereleases verificados.~~ [Broker](../prompts/registros/P155-release-0.26.0.md), [client](../../xmqr-client/prompts/registros/C90-release-0.24.0.md), [admin](../../xmqr-admin/prompts/registros/A16-core-v13-release-0.8.md). Fases 6A–6D e 7–9 seguem abertas.
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
| Listeners | Até três endpoints mTLS adicionais, políticas por endpoint, TLS-senha e rotação aceitos na fase4 | Ampliar além do limite atual somente com nova demanda e validação |
| Administração | Canal local autenticado, bundle, ações, auditoria e diagnóstico aceitos na fase5; painel somente leitura | Administração remota e plugins permanecem fora do escopo atual |
| Métricas/logs | Monitor loopback e contadores administrativos de cardinalidade fixa; `$SYS` não gerado por decisão B14 | Exportação adicional conforme demanda |
| MQTT5 | P115–P123/C57–C64: pub/sub QoS0/1/2 e unsub com sessão limpa, diagnóstico parcial e propriedades informativas de CONNECT | Codec/propriedades completos, negociação de sessões, expiração, fluxo, opções de assinatura e autenticação estendida |
| WebSocket | Ausente | WS/WSS no broker e conexão correspondente no client |
| Bridge | Ausente | Ligação entre brokers com TLS, reconexão, mapeamento de tópicos e proteção de loops |
| Distribuição | Deb26 amd64; sem APT próprio | Ubuntu24 validado, arm64, repositório APT assinado e política de upgrade |
| Windows nativo | Não homologado | Persistência/locks/CRUD/sinais adaptados, serviço Windows, instalador e testes |
| Clients | CLI própria com perfis, saída/filtros, repetição e MQTT5 parcial; sem paridade exaustiva | Completar MQTT5 e validar firmware ESP32 como consumidor nos novos contratos |
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
| 6A | Semanas13–15 | P115–P123 aceitam pub/sub MQTT5 QoS0/1/2, unsub, motivos ACL e CONNECT informativo; codec/propriedades completos pendentes | C57–C64 selecionam3.1.1/5, exibem recusa, propriedades CONNECT e aguardam UNSUBACK/PUBCOMP | Negativos normativos e coexistência3.1.1; apenas subconjunto5 anunciado |
| 6B | Semanas16–18 | P127/P128: Clean Start e Session Expiry; P130: Message Expiry; P131: DISCONNECT expiry; P132: Will Delay e documento v8 | C66/C67: opções de sessão; C69: Message Expiry; C70: Will Delay; retomada QoS do próprio client pendente | Crash/restart, migração e relógio/expiração tratados sem perda silenciosa |
| 6C | Semanas19–21 | P134/P136 aceitos para Receive Maximum e Maximum Packet Size; P138/P139 aceitam alias de entrada/saída; P141/P142 aceitam metadados PUBLISH e documento v10; P144 anuncia quota inbound onde cabe; P146 trata quota QoS2 retomada | C72/C73 expõem limites de recebimento; C75 aceita alias recebido; C77/C78 publicam metadados; C80 os exibe em JSONL; C81 repete publicações em série; C83 usa alias compacto | Fluxo e tamanho validados em QoS0/1/2, retained e restart; Mosquitto 2.0.22 falha no alias abreviado de saída; aceite global da fase pendente |
| 6D | Semanas22–24 | P147/P148/P150/P153/P154 aceitos; shared durável no estado v13, admin A16 para distribuição pendente; AUTH pendente | C84/C85/C87/C89 aceitos; autenticação5 pendente | Matriz5 por cláusula, interop externa, recursos ausentes declarados; sem alegação integral prematura |
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
O parágrafo anterior sobre a fase2 é histórico. Após P123/C64, a próxima
entrega continua na fase6A: ampliar propriedades e demais reason codes MQTT5
no broker e no client.
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
