> **Adaptação XMQR — 2026-10-07.** Referência transversal: tarefa proposta; verificar no código quais parcelas já existem e pedir apenas o incremento autorizado.
> Leia primeiro [o contrato comum](../contrato-base.md) e a matriz [de cobertura](../COBERTURA.md).
> Origem literal preservada: [arquivo original](../origem/broker/16-production-readiness.md). Nenhum agente, skill ou MCP externo é requisito instalado.
> O contrato comum prevalece sobre instruções históricas de versão, ambiente e execução. Leitura não autoriza implementação nem execução automática.
# Prompt — prontidão de produção

Avalie o candidato a release com evidência. Gates: escopo e limitações publicados; conformidade; fuzzing sem crash conhecido; threat model e achados críticos resolvidos; baseline de desempenho; limites seguros; recuperação e backup/restore; upgrade/rollback; graceful shutdown; métricas/alertas; runbooks e documentação.

Simule restart durante tráfego, disco cheio/lento, persistência corrompida, certificado expirado, dependência de autenticação indisponível, consumidor lento e tempestade de reconexões.

Entregue decisão GO/NO-GO, bloqueadores, riscos aceitos com responsável/prazo e procedimento de rollback ensaiado. Ausência de evidência conta como não aprovado.
