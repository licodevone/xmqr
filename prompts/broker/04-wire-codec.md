> **Adaptação XMQR — 2026-10-07.** Referência transversal: tarefa proposta; verificar no código quais parcelas já existem e pedir apenas o incremento autorizado.
> Leia primeiro [o contrato comum](../contrato-base.md) e a matriz [de cobertura](../COBERTURA.md).
> Origem literal preservada: [arquivo original](../origem/broker/04-wire-codec.md). Nenhum agente, skill ou MCP externo é requisito instalado.
> O contrato comum prevalece sobre instruções históricas de versão, ambiente e execução. Leitura não autoriza implementação nem execução automática.
# Prompt — codec MQTT incremental

Projete e implemente um codec incremental para MQTT 3.1.1 antes das extensões 5.0. O decoder deve aceitar frames fragmentados e múltiplos frames por buffer sem ler além do pacote declarado.

Cubra fixed header, flags reservadas, Remaining Length variável com limite de quatro bytes, strings UTF-8 MQTT, binary data, packet identifier e limites configuráveis antes de alocação. Modele pacotes como tipos válidos; diferencie erro incompleto, malformado e protocolo inválido.

Implemente por pacote em fatias: CONNECT/CONNACK/PINGREQ/PINGRESP/DISCONNECT, depois PUBLISH e acknowledgements, então subscribe/unsubscribe. Para cada pacote, adicione vetores binários conhecidos, round-trip, fragmentação, concatenação, limites e bytes proibidos com cláusulas normativas.
