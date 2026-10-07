> **Adaptação XMQR — 2026-10-07.** Referência transversal: tarefa proposta; verificar no código quais parcelas já existem e pedir apenas o incremento autorizado.
> Leia primeiro [o contrato comum](../contrato-base.md) e a matriz [de cobertura](../COBERTURA.md).
> Origem literal preservada: [arquivo original](../origem/broker/14-performance-and-capacity.md). Nenhum agente, skill ou MCP externo é requisito instalado.
> O contrato comum prevalece sobre instruções históricas de versão, ambiente e execução. Leitura não autoriza implementação nem execução automática.
# Prompt — desempenho e capacidade

Defina hipóteses mensuráveis e baseline. Cenários mínimos: conexões ociosas, connect storm, QoS 0 throughput, QoS 1 latência, fan-out, wildcard matching, retained bootstrap, persistência sob carga e consumidores lentos.

Registre hardware, SO, toolchain, build, configuração, clientes, payload, QoS, tópicos, fan-out, duração e warm-up. Meça throughput, p50/p95/p99/p99.9, CPU, RSS, alocações, filas, erros e tempo de shutdown/recuperação.

Faça profiling antes de otimizar. Toda otimização deve preservar a matriz de conformidade e mostrar comparação repetível com intervalo/variabilidade, não apenas o melhor número.
