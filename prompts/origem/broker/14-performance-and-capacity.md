# Prompt — desempenho e capacidade

Defina hipóteses mensuráveis e baseline. Cenários mínimos: conexões ociosas, connect storm, QoS 0 throughput, QoS 1 latência, fan-out, wildcard matching, retained bootstrap, persistência sob carga e consumidores lentos.

Registre hardware, SO, toolchain, build, configuração, clientes, payload, QoS, tópicos, fan-out, duração e warm-up. Meça throughput, p50/p95/p99/p99.9, CPU, RSS, alocações, filas, erros e tempo de shutdown/recuperação.

Faça profiling antes de otimizar. Toda otimização deve preservar a matriz de conformidade e mostrar comparação repetível com intervalo/variabilidade, não apenas o melhor número.

