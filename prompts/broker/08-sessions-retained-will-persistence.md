> **Adaptação XMQR — 2026-10-07.** Referência transversal: tarefa proposta; verificar no código quais parcelas já existem e pedir apenas o incremento autorizado.
> Leia primeiro [o contrato comum](../contrato-base.md) e a matriz [de cobertura](../COBERTURA.md).
> Origem literal preservada: [arquivo original](../origem/broker/08-sessions-retained-will-persistence.md). Nenhum agente, skill ou MCP externo é requisito instalado.
> O contrato comum prevalece sobre instruções históricas de versão, ambiente e execução. Leitura não autoriza implementação nem execução automática.
# Prompt — sessões, retained, Will e persistência

Defina agregado de sessão, ownership por client ID, epoch da conexão e conteúdo persistido. Modele clean session/start, expiry, assinaturas, fila offline, inflight nos dois sentidos e takeover.

Defina retained separadamente de mensagens normais: substituir, remover com payload vazio, expirar e entregar durante SUBSCRIBE. Modele Will, cancelamento em desconexão normal e atraso MQTT 5 quando aplicável.

Para persistência, declare atomicidade, fsync/durabilidade, recuperação, corrupção, compactação, migração e quotas. Construa testes de crash em pontos de commit e prove que a recuperação não confirma dados inexistentes nem perde estado já confirmado segundo a configuração.
