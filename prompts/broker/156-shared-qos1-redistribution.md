# P156 rev1 — redistribuição QoS1 de grupo após término de sessão

Entrada: broker 0.26.0/P154 mantém associação compartilhada durável em v13 e entrega QoS2 vinculada à sessão escolhida. Uma mensagem QoS1 atribuída a membro que termina sua sessão permanece sem redistribuição, embora MQTT 5 §4.8.2 recomende oferecer mensagens não reconhecidas a outro membro do grupo.

Objetivo: registrar a origem de grupo nas obrigações QoS1 compartilhadas e, no término definitivo da sessão escolhida, redistribuir cada obrigação ainda não reconhecida a outro membro elegível do mesmo `$share/grupo/filtro`, respeitando ACL atual, QoS, identificador de assinatura, limite de filas e preferência por membro ativo. Evitar duplicação após PUBACK; preservar a vinculação QoS2 e entregas normais. Limpar obrigações quando nenhum membro elegível existir, com diagnóstico/documentação explícitos. Migração durável e admin independente devem ser tratados antes de nova distribuição.

Aceite: teste de ator e TCP com dois membros, sessão temporária/persistente, encerramento explícito/expiração, PUBACK concorrente, restart e falha de commit; regressões P154 QoS2, retidos, ACL, 3.1.1, fmt/Clippy/test/build/CI. Registrar lacunas honestamente. Não publicar nova tag até a compatibilidade do admin, pacote/rollback e checksums passarem.

Fonte normativa: [OASIS MQTT 5 §4.8.2](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html).
