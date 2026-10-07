> **Adaptação XMQR — 2026-10-07.** Referência transversal: tarefa proposta; verificar no código quais parcelas já existem e pedir apenas o incremento autorizado.
> Leia primeiro [o contrato comum](../contrato-base.md) e a matriz [de cobertura](../COBERTURA.md).
> Origem literal preservada: [arquivo original](../origem/broker/11-configuration-observability-admin.md). Nenhum agente, skill ou MCP externo é requisito instalado.
> O contrato comum prevalece sobre instruções históricas de versão, ambiente e execução. Leitura não autoriza implementação nem execução automática.
# Prompt — configuração, observabilidade e administração

Defina esquema de configuração versionado com defaults explícitos, validação cruzada, precedência arquivo/ambiente/CLI e mensagens com caminho do campo. Classifique campos como estáticos ou recarregáveis; reload deve ser atômico ou rejeitado.

Adicione logs estruturados correlacionados por connection/client/session sem expor dados sensíveis; métricas de conexões, pacotes, bytes, razões de desconexão, sessões, filas, inflight, persistência e latência, evitando labels de alta cardinalidade; traces somente onde agregam diagnóstico.

Crie health, readiness e administração em listener separado ou local. Inclua graceful shutdown, drenagem, dump de configuração efetiva redigida e diagnóstico de capacidade.
