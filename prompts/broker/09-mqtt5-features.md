> **Adaptação XMQR — 2026-10-07.** Futuro: MQTT 5.0 não implementado nem autorizado por esta organização documental.
> Leia primeiro [o contrato comum](../contrato-base.md) e a matriz [de cobertura](../COBERTURA.md).
> Origem literal preservada: [arquivo original](../origem/broker/09-mqtt5-features.md). Nenhum agente, skill ou MCP externo é requisito instalado.
> O contrato comum prevalece sobre instruções históricas de versão, ambiente e execução. Leitura não autoriza implementação nem execução automática.
# Prompt — MQTT 5.0

Adicione MQTT 5.0 como extensão explícita do núcleo comprovado, sem misturar regras de versões. Comece por reason codes e properties no codec; valide multiplicidade, contexto permitido, tamanho e forwarding.

Priorize Maximum Packet Size, Receive Maximum, Topic Alias, Message Expiry, Session Expiry, Request/Response Information e Subscription Options conforme o contexto. Em seguida avalie shared subscriptions, subscription identifiers e enhanced authentication.

Para cada feature, documente downgrade/isolamento de conexões 3.1.1, impacto em estado/persistência, reason codes e testes normativos. Rejeite propriedades duplicadas ou proibidas exatamente como a especificação determina.
