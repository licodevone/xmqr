# P227H v1.0 — fixtures CONNACK após anúncio de shared subscriptions

Preparado2026-10-18 antes de mudar testes. A campanha integradaD preserva
FAIL de verify_mqtt5_connack_receive_maximum.py e resumed_qos2_quota.py.
Diagnóstico isolado do primeiro: AssertionError emconnectlinha42, antes
da medição de fluxo. P144 esperava sucesso comMPS5, anterior ao anúncio
obrigatório de SharedSubscriptionAvailable1 adotadoP153. Helper também
não conhece propriedade0x2a, embora o broker a envie desdeP153.

Corrigir somente scripts/verify_mqtt5_connack_receive_maximum.py e seus
vetores estritos: MPS5/6→CONNACK0x95/EOF sem sessão; sucesso a partir7,
anúncio0x2a1, limites de frame e negociação das propriedades opcionais
nas fronteiras7/10/12/15/18 e vizinhos. Parser continua recusando propriedades
inesperadas, duplicatas/truncamento. Não pular negativos nem aceitar qualquer
CONNACK. P146 usa esse helper e deve repetir integralmente sem mudar seu
contrato de quota,recusa0x97,retomada/transações. Verificar outros importadores.

Sem alteração de runtime, quotas, versões ou estado15/16. Repetir os dois
harnesses contra o mesmoELFDdca22b26...f57 com clientcongelado109ec973...
e depois no conjunto final. GuardarFAILs e resultados sanitizados, nunca
assertion/logs privados completos. Fonte OASIS MQTT5§3.2.2.3.13 e§3.1.2.11.4;
decisão do anúncio é existenteP153, não redefinir contrato para esconder bug.
