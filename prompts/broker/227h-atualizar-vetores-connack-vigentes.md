# P227H v1.1 — fixtures vigentes após shared subscriptions e alias

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

## Revisão1.1 antes de corrigir outros vetores históricos

CampanhaDall4:68fixtures,6FAIL, fontes/binariesunchangedtrue,224,067s.
P144/P146 confirmados acima; P146 isolado deuKeyError42 emhelperlinha48.
Após correção das fronteiras/0x2a, ambos repetidos noELFD+client109ecPASS.

Outros dois FAILs foram reproduzidos isoladamente: shared_live linha117
ainda esperaSUBACK0x9e para associação persistente, substituído porP154
comQoS1; topic_alias linha71 ainda espera0x94 para alias não mapeado,
corrigidoP227Dpara0x82. Atualizar somente esses dois vetores aos contratos
vigentes; conservar EOF/reset/nenhumaentrega e demais controles, sem retirar
casos. Persistência shared tem também fixtureP154 própria que passou.

VBI/aliasReason falharam antes de imprimir cenários na campanha, semJSON
próprio; ambas repetições isoladas completasPASS. Causa dessas duas falhas
não foi comprovada. Acrescentar metadados diagnósticos sanitizados ao
executor e repetir, não atribuir arbitrariamente a protocolo/carga/timeout.
