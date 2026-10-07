> **Adaptação XMQR — 2026-10-07.** Referência transversal: tarefa proposta; verificar no código quais parcelas já existem e pedir apenas o incremento autorizado.
> Leia primeiro [o contrato comum](../contrato-base.md) e a matriz [de cobertura](../COBERTURA.md).
> Origem literal preservada: [arquivo original](../origem/broker/12-conformance-test-suite.md). Nenhum agente, skill ou MCP externo é requisito instalado.
> O contrato comum prevalece sobre instruções históricas de versão, ambiente e execução. Leitura não autoriza implementação nem execução automática.
# Prompt — suíte de conformidade

Crie uma matriz rastreável por MQTT 3.1.1 e 5.0. Para cada cláusula de servidor no escopo, registre identificador, comportamento, teste, fixture, resultado e issue associada.

Estruture suites por codec, conexão, publish, subscribe, QoS, sessão, retained, Will, segurança e MQTT 5 properties/reason codes. Use testes black-box no socket além de testes internos.

O relatório deve distinguir PASS, FAIL, NOT_IMPLEMENTED, NOT_APPLICABLE e BLOCKED. Um conjunto vazio ou ignorado não pode resultar em PASS. Publique resumo reproduzível por versão e configuração.
