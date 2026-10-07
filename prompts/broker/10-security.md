> **Adaptação XMQR — 2026-10-07.** Referência transversal: tarefa proposta; verificar no código quais parcelas já existem e pedir apenas o incremento autorizado.
> Leia primeiro [o contrato comum](../contrato-base.md) e a matriz [de cobertura](../COBERTURA.md).
> Origem literal preservada: [arquivo original](../origem/broker/10-security.md). Nenhum agente, skill ou MCP externo é requisito instalado.
> O contrato comum prevalece sobre instruções históricas de versão, ambiente e execução. Leitura não autoriza implementação nem execução automática.
# Prompt — segurança

Crie threat model cobrindo listeners, parser, autenticação, ACL, armazenamento, administração e observabilidade. Liste ativos, atacantes, trust boundaries, abusos e controles.

Implemente TLS configurável com defaults seguros, proteção de chaves e rotação; autenticação sem enumeração; ACL deny-by-default por connect/publish/subscribe; quotas e rate limits; limites de pacotes, tópicos, filas, inflight e fan-out. Isole a interface administrativa.

Teste slowloris, Remaining Length hostil, strings inválidas, filtros patológicos, reconnect storm, retained flood, credenciais erradas, ACL wildcard e vazamento em logs. Faça auditabilidade sem registrar segredo ou payload por padrão.
