> **Adaptação XMQR — 2026-10-07.** Referência transversal: tarefa proposta; verificar no código quais parcelas já existem e pedir apenas o incremento autorizado.
> Leia primeiro [o contrato comum](../contrato-base.md) e a matriz [de cobertura](../COBERTURA.md).
> Origem literal preservada: [arquivo original](../origem/broker/06-subscriptions-and-routing.md). Nenhum agente, skill ou MCP externo é requisito instalado.
> O contrato comum prevalece sobre instruções históricas de versão, ambiente e execução. Leitura não autoriza implementação nem execução automática.
# Prompt — assinaturas, matching e roteamento

Implemente validação de topic names e filters, incluindo `+`, `#`, níveis vazios, limite UTF-8 e regra de tópicos iniciados por `$`. Não normalize strings durante matching ou autorização.

Escolha o índice com base em operações e cardinalidades do contexto. Defina atomicidade de SUBSCRIBE/UNSUBSCRIBE, deduplicação quando múltiplas assinaturas da mesma sessão casam, QoS efetivo e fan-out com backpressure.

Comece por tópicos exatos e QoS 0; adicione wildcards somente com testes de propriedades e vetores de borda. Meça custo de inserção, remoção e match para árvores largas e profundas.
