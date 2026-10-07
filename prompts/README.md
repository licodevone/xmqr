# Prompts do XMQR

Comece pelo [contrato-base](contrato-base.md), [sequência](00-sequencia-mestra.md)
e [matriz de cobertura](COBERTURA.md). Alterações futuras: preparar primeiro um
ou mais prompts, depois executar apenas o pedido autorizado.

Importados somente broker/ e clients/ do consumidor mqtt-broker, com originais
preservados em origem/. Os catálogos gerais de origem foram arquivados como
contexto, sem importar setup, firmware, banco, gateway, API, web/mobile ou Sheets.
Não há prova de execução histórica desses prompts nos commits XMQR.

Os prompts históricos são referências; cópias de trabalho foram adaptadas ao
estado atual, com notas de status. P34–P40 e C24 cobrem lacunas documentais ou
correções propostas. Last Will e MQTT 5 não foram implementados por esta tarefa.
Leia [relatório](RELATORIO.md), [origem](origem/README-preservacao.md),
[registro modelo](registros/TEMPLATE.md) e o [prompt desta tarefa](00-organizar-atualizar-prompts.md).

## Broker
- [00-project-context](broker/00-project-context.md)
- [01-master-orchestrator](broker/01-master-orchestrator.md)
- [02-scope-and-adrs](broker/02-scope-and-adrs.md)
- [03-rust-workspace-bootstrap](broker/03-rust-workspace-bootstrap.md)
- [04-wire-codec](broker/04-wire-codec.md)
- [05-connection-state-machine](broker/05-connection-state-machine.md)
- [06-subscriptions-and-routing](broker/06-subscriptions-and-routing.md)
- [07-qos-delivery](broker/07-qos-delivery.md)
- [08-sessions-retained-will-persistence](broker/08-sessions-retained-will-persistence.md)
- [09-mqtt5-features](broker/09-mqtt5-features.md)
- [10-security](broker/10-security.md)
- [11-configuration-observability-admin](broker/11-configuration-observability-admin.md)
- [12-conformance-test-suite](broker/12-conformance-test-suite.md)
- [13-fuzzing-and-property-tests](broker/13-fuzzing-and-property-tests.md)
- [14-performance-and-capacity](broker/14-performance-and-capacity.md)
- [15-interoperability](broker/15-interoperability.md)
- [16-production-readiness](broker/16-production-readiness.md)
- [17-documentation-and-examples](broker/17-documentation-and-examples.md)
- [18-feature-iteration](broker/18-feature-iteration.md)
- [22-mqtt311-qos0-pubsub-mvp](broker/22-mqtt311-qos0-pubsub-mvp.md)
- [23-certificate-identity-and-acl](broker/23-certificate-identity-and-acl.md)
- [24-pubsub-interoperability-gate](broker/24-pubsub-interoperability-gate.md)
- [25-durable-mqtt-state-contract](broker/25-durable-mqtt-state-contract.md)
- [26-qos1-vertical-slice](broker/26-qos1-vertical-slice.md)
- [27-persistent-sessions](broker/27-persistent-sessions.md)
- [28-qos2-state-machine](broker/28-qos2-state-machine.md)
- [29-retained-messages](broker/29-retained-messages.md)
- [30-qos-session-retained-gate](broker/30-qos-session-retained-gate.md)
- [31-reproduzir-validar-v020](broker/31-reproduzir-validar-v020.md)
- [32-last-will](broker/32-last-will.md)
- [33-wildcard-subscriptions](broker/33-wildcard-subscriptions.md)
- [34-perfis-laboratorio-e-isolamento](broker/34-perfis-laboratorio-e-isolamento.md)
- [35-administracao-usuarios-atomica](broker/35-administracao-usuarios-atomica.md)
- [36-validar-snapshot-atual](broker/36-validar-snapshot-atual.md)
- [37-contrato-limites-topicos-cliente](broker/37-contrato-limites-topicos-cliente.md)
- [38-client-id-e-deadlines](broker/38-client-id-e-deadlines.md)
- [39-persistencia-recuperacao-e-resiliencia](broker/39-persistencia-recuperacao-e-resiliencia.md)
- [40-licencas-ci-versionamento-e-sincronizacao](broker/40-licencas-ci-versionamento-e-sincronizacao.md)

## Cliente Rust

- [19-client-pubsub-scope](clients/19-client-pubsub-scope.md)
- [20-client-pubsub-implementation](clients/20-client-pubsub-implementation.md)
- [21-client-pubsub-tests](clients/21-client-pubsub-tests.md)
- [22-qos-retained-sessions](clients/22-qos-retained-sessions.md)
- [23-interoperabilidade-v020](clients/23-interoperabilidade-v020.md)
- [24-cli-atual-e-credenciais](clients/24-cli-atual-e-credenciais.md)

## Instruções, skills e agentes do XMQR

Leia [AGENTS.md](../AGENTS.md) e [uso da configuração local](../docs/agent-workflow.md).
O [prompt P-DOC-02](01-configurar-agentes-skills.md) registra a preparação desta
configuração. Skills em .agents/skills e papéis TOML em .codex/agents pertencem
ao XMQR; os materiais originais permanecem intactos. Clientes continuam no índice.


P41: [limite compartilhado de 1024 bytes](broker/41-topicos-filtros-1024.md)
e [registro de execução](registros/P41-topicos-1024.md). P37 preserva a análise
anterior; a decisão autorizada foi ampliar somente tópico/filtro.
