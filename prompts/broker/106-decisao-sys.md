# P106 rev1 — decisão sobre tópicos $SYS

2026-10-15. Entrada: monitor HTTP opcional do broker 0.14.0, métricas finitas
e probe real do ator/writer; não há publicação gerada pelo broker em `$SYS`.
Matriz B14 exige decisão, não necessariamente novo protocolo na fase 5.

Comparar publicar métricas via MQTT `$SYS` com manter o monitor autenticado
por confinamento loopback. Registrar contrato atual, riscos de ACL, retenção,
cardinalidade, frequência e custo, além de critério para reconsiderar. Não
alterar roteamento MQTT, listener ou formato de estado. Atualizar plano sem
confundir decisão com implementação B13/A09.
