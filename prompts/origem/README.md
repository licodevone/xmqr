# Catálogo de prompts

> **Comece por [00-sequencia-mestra.md](00-sequencia-mestra.md).** A ordem numérica dentro de uma pasta não representa, sozinha, a ordem de construção de todo o sistema.

## Escopo ativo

Neste momento, a sequência ativa cobre preparação reproduzível, broker MQTT, clientes, firmwares ESP-IDF e integração auxiliar com Google Sheets. Não criar ainda gateway MQTT/API, controle remoto real pela web/mobile ou posicionamento como solução industrial/edge.

As pastas de banco, backend e API permanecem preservadas como planejamento futuro. Web e mobile podem avançar somente como protótipos com dados simulados até autorização explícita da plataforma integrada.

Os arquivos estão separados por etapa:

- [Setup](setup/) — preparação reproduzível de outro computador. Sempre começa aqui.
- [Broker](broker/) — construção do servidor MQTT. Comece por [contexto do projeto](broker/00-project-context.md) e depois use o [orquestrador](broker/01-master-orchestrator.md).
- [Clients](clients/) — planejamento, implementação e teste dos clientes Rust `pub/sub`. Comece pelo [escopo editável](clients/19-client-pubsub-scope.md).
- [Web](web/) — protótipos em Next.js/React durante a fase ativa; integração real é futura.
- [Mobile](mobile/) — protótipos React Native durante a fase ativa; integração real é futura.
- [Database](database/) — **fase futura**, PostgreSQL e Prisma ORM.
- [Backend](backend/) — **fase futura**, incluindo gateway MQTT/API e Better Auth.
- [API](api/) — **fase futura**, OpenAPI, Swagger e Scalar.

## Broker

| Ordem | Prompt | Resultado principal |
|---:|---|---|
| 00 | [Contexto do projeto](broker/00-project-context.md) | Contexto editável do produto |
| 01 | [Orquestrador](broker/01-master-orchestrator.md) | Próxima fatia e coordenação |
| 02 | [Escopo e ADRs](broker/02-scope-and-adrs.md) | Escopo, riscos e ADRs |
| 03 | [Workspace Rust](broker/03-rust-workspace-bootstrap.md) | Workspace compilável |
| 04 | [Codec wire](broker/04-wire-codec.md) | Codec incremental seguro |
| 05 | [Conexão MQTT](broker/05-connection-state-machine.md) | Ciclo de conexão MQTT |
| 06 | [Assinaturas e roteamento](broker/06-subscriptions-and-routing.md) | Índice e fan-out |
| 07 | [QoS](broker/07-qos-delivery.md) | QoS 0/1/2 e inflight |
| 08 | [Sessões e persistência](broker/08-sessions-retained-will-persistence.md) | Estado durável e recuperação |
| 09 | [MQTT 5](broker/09-mqtt5-features.md) | Extensões MQTT 5.0 |
| 10 | [Segurança](broker/10-security.md) | TLS, authn, ACL e quotas |
| 11 | [Operação](broker/11-configuration-observability-admin.md) | Operação do broker |
| 12 | [Conformidade](broker/12-conformance-test-suite.md) | Matriz normativa |
| 13 | [Fuzzing](broker/13-fuzzing-and-property-tests.md) | Robustez do parser e estados |
| 14 | [Desempenho](broker/14-performance-and-capacity.md) | Baseline e capacidade |
| 15 | [Interoperabilidade](broker/15-interoperability.md) | Compatibilidade com clientes reais |
| 16 | [Produção](broker/16-production-readiness.md) | Gate de release |
| 17 | [Documentação](broker/17-documentation-and-examples.md) | Documentação utilizável |
| 18 | [Iteração](broker/18-feature-iteration.md) | Template para qualquer nova feature |
| 22 | [MVP pub/sub](broker/22-mqtt311-qos0-pubsub-mvp.md) | Primeira fatia MQTT 3.1.1 funcional |
| 23 | [Autenticação e ACL](broker/23-certificate-identity-and-acl.md) | mTLS + usuário/senha + ACL por tópico |
| 24 | [Gate de interoperabilidade](broker/24-pubsub-interoperability-gate.md) | Prova cruzada com clientes reais |
| 25 | [Contrato durável MQTT](broker/25-durable-mqtt-state-contract.md) | Modelo, atomicidade, ACK e migração |
| 26 | [QoS 1](broker/26-qos1-vertical-slice.md) | Entrega QoS 1 e PUBACK |
| 27 | [Sessões persistentes](broker/27-persistent-sessions.md) | CleanSession 0/1 e recuperação |
| 28 | [QoS 2](broker/28-qos2-state-machine.md) | Fluxo durável em quatro etapas |
| 29 | [Mensagens retidas](broker/29-retained-messages.md) | Estado retained por tópico |
| 30 | [Gate QoS/sessão/retained](broker/30-qos-session-retained-gate.md) | Conformidade e crash tests |
| 31 | [Reproduzir e validar 0.2.0](broker/31-reproduzir-validar-v020.md) | Prova da versão atual em outro computador |
| 32 | [Last Will](broker/32-last-will.md) | Will MQTT 3.1.1 com testes normativos |
| 33 | [Wildcards](broker/33-wildcard-subscriptions.md) | Filtros `+` e `#` com limites e ACL |

## Clients

| Ordem | Prompt | Resultado principal |
|---:|---|---|
| 19 | [Escopo histórico QoS 0](clients/19-client-pubsub-scope.md) | Primeira fatia do cliente, preservada para estudo |
| 20 | [Implementação](clients/20-client-pubsub-implementation.md) | Implementação incremental da CLI `pub`/`sub` |
| 21 | [Testes](clients/21-client-pubsub-tests.md) | Testes de segurança, conformidade e interoperabilidade |
| 22 | [Cliente avançado](clients/22-qos-retained-sessions.md) | QoS 1/2, retained e sessões persistentes |
| 23 | [Gate do cliente 0.2.0](clients/23-interoperabilidade-v020.md) | Evidência cruzada contra brokers independentes |

## Web — protótipo agora; integração futura

| Ordem | Prompt | Resultado principal |
|---:|---|---|
| 00 | [Contexto do produto](web/00-contexto-produto.md) | Escopo, personas, limites e evidências |
| 01 | [Contrato e gateway](web/01-contrato-api-gateway.md) | API segura entre MQTT e interfaces |
| 02 | [Bootstrap e design system](web/02-bootstrap-next-shadcn-tailwind.md) | Next.js + shadcn/ui + Tailwind utilizável |
| 03 | [Autenticação e autorização](web/03-autenticacao-autorizacao.md) | Sessão web, papéis e isolamento |
| 04 | [Dashboard em tempo real](web/04-dashboard-tempo-real.md) | Estado atual, qualidade e conexão |
| 05 | [Histórico e alertas](web/05-historico-alertas.md) | Gráficos, filtros e incidentes |
| 06 | [Controle remoto](web/06-controle-remoto.md) | Comando auditável e confirmação do dispositivo |
| 07 | [Qualidade e release](web/07-qualidade-release.md) | Testes, acessibilidade, segurança e deploy |

## Mobile — protótipo agora; integração futura

| Ordem | Prompt | Resultado principal |
|---:|---|---|
| 00 | [Contexto do produto](mobile/00-contexto-produto.md) | Escopo móvel e limites de segurança |
| 01 | [Contrato e arquitetura](mobile/01-contrato-arquitetura.md) | API compartilhada e estratégia offline |
| 02 | [Bootstrap e design system](mobile/02-bootstrap-expo-nativewind.md) | React Native + Expo Router + NativeWind |
| 03 | [Autenticação segura](mobile/03-autenticacao-segura.md) | Tokens protegidos, sessão e RBAC |
| 04 | [Dashboard offline-first](mobile/04-dashboard-offline.md) | Telemetria, cache e reconexão |
| 05 | [Alertas e notificações](mobile/05-alertas-notificacoes.md) | Inbox, deep links e push seguro |
| 06 | [Controle remoto](mobile/06-controle-remoto.md) | Confirmação explícita e resultado auditável |
| 07 | [Qualidade e publicação](mobile/07-qualidade-publicacao.md) | Testes, builds e checklist de loja |

## Database — fase futura, não executar agora

| Ordem | Prompt | Resultado principal |
|---:|---|---|
| 00 | [Modelo PostgreSQL + Prisma](database/00-modelo-postgresql-prisma.md) | Entidades, relações, constraints e ownership |
| 01 | [Migrations e retenção](database/01-migrations-retencao-indices.md) | Evolução segura, índices, partições e backup |
| 02 | [Ingestão e outbox](database/02-ingestao-idempotencia-outbox.md) | Telemetria idempotente e eventos confiáveis |

## Backend — fase futura, não executar agora

| Ordem | Prompt | Resultado principal |
|---:|---|---|
| 00 | [Arquitetura do gateway](backend/00-arquitetura-gateway.md) | Fronteiras MQTT, API e workers |
| 01 | [Better Auth + Prisma](backend/01-better-auth-prisma.md) | Sessões, organizações, papéis e segurança |
| 02 | [Telemetria em tempo real](backend/02-telemetria-tempo-real.md) | Ingestão, consultas, SSE/WebSocket e stale |
| 03 | [Comandos e auditoria](backend/03-comandos-auditoria.md) | Controle idempotente e resultado correlacionado |

## API — fase futura, não executar agora

| Ordem | Prompt | Resultado principal |
|---:|---|---|
| 00 | [Contrato OpenAPI](api/00-contrato-openapi.md) | OpenAPI versionado, validado e testado |
| 01 | [Swagger UI e Scalar](api/01-swagger-scalar.md) | Duas visualizações seguras do mesmo contrato |

Cada prompt exige evidências antes de avançar. Em outro computador, não use arquivos isolados: clone o repositório e siga a sequência mestre.

O broker está na versão 0.5.0, com QoS 0/1/2, retained, sessões persistentes,
modos didáticos de segurança e filtros `+`/`#` implementados sob limites
documentados. Os prompts `22`–`31` são históricos e o `33` descreve a fatia de
coringas já aplicada; a próxima fatia do núcleo é o Will do prompt `32`.
Nenhum prompt ou teste local implica conformidade MQTT completa ou prontidão
de produção.
