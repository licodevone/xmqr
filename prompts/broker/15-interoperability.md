> **Adaptação XMQR — 2026-10-07.** Referência transversal: tarefa proposta; verificar no código quais parcelas já existem e pedir apenas o incremento autorizado.
> Leia primeiro [o contrato comum](../contrato-base.md) e a matriz [de cobertura](../COBERTURA.md).
> Origem literal preservada: [arquivo original](../origem/broker/15-interoperability.md). Nenhum agente, skill ou MCP externo é requisito instalado.
> O contrato comum prevalece sobre instruções históricas de versão, ambiente e execução. Leitura não autoriza implementação nem execução automática.
# Prompt — interoperabilidade

Monte testes black-box com `mosquitto_pub/sub` e ao menos duas bibliotecas clientes independentes, cobrindo MQTT 3.1.1 e 5.0 quando suportadas. Inclua connect, auth, publish/subscribe, wildcards, QoS, retained, Will, sessões, reconnect e limites.

Execute o mesmo cenário contra este broker e um Mosquitto de versão fixada. Compare comportamento no wire e resultado do cliente, aceitando diferenças apenas quando permitidas e documentadas.

Capture versões e comandos exatos. Transforme divergências em casos pequenos com referência normativa; não “corrija” apenas para imitar comportamento não normativo do broker de referência.
