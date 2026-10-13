# ADR0006 — quotas por identidade

Data2026-10-13, P80/B05. Decisão: manter quotas atuais; rate limit/fairness
por identidade adiado com risco explícito. Não significa recurso implementado.

P80 exercita admissãoN1/8/32/64, filas4/8 e32/64, auth saturada e não leitores.
Um assinante semACK pode lotar fila e recusar publicador daquele tópico;
outros tópicos progridem. HashesArgon2 limitados4 recusam bursts.
Não foi medido isolamento multitenant com identidades competindo.

Não aumentar tetos/defaults nem introduzir prioridade/descarteQoS>0 implícito.
O patchshutdown resolve vaga presa, não starvation nem fairness.
Risco remanescente: uma identidade pode consumir quotas globais e afetar outra.
Isso impede promessa multitenant/produção; a campanha é de laboratório.

Antes de B05runtime, definir principal estável, cobrança por tentativa/auth/
publicação/bytes/fan-out, janela monotônica, budget compartilhado, exceções
admin/Will, retry e responsabilidadeQoS2. Prevenir spoofing porClientID,
testarN/N+1, reload/ACL/restart e medir competição de identidades distintas.
Revisitar na fase3 antes de ampliar promessas operacionais.
