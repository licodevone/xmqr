# Estado de implementação MQTT 3.1.1

Esta matriz descreve a base XMQR 0.5 e o incremento local 0.6. Não é uma declaração
de conformidade completa. Os testes externos usam Mosquitto 2.0.18 em
`open-lab`; TLS/mTLS e ACL ainda precisam de uma matriz externa ampliada.

| Área OASIS MQTT 3.1.1 | Estado | Evidência | Pendência |
| --- | --- | --- | --- |
| §3.1 CONNECT e §3.2 CONNACK | perfis documentados implementados | codec, autenticação, sessão e conexões externas | recusa de Client ID vazio, ampliar negativos |
| §3.3 PUBLISH QoS 0/1/2 | implementado | codec, roteador e Mosquitto nos três QoS | falhas de rede externas ampliadas |
| §§3.4–3.7 ACKs de QoS | implementado | vetores conhecidos, recuperação e troca externa | ampliar retransmissões externas |
| §§3.8–3.9 SUBSCRIBE/SUBACK | nomes exatos e filtros | codec, ACL, sobreposição e Mosquitto | matriz TLS/mTLS e ACL externa |
| §§3.10–3.11 UNSUBSCRIBE/UNSUBACK | implementado | remoção literal, persistência e fixture independente | ampliar combinações externas |
| §§3.12–3.13 PINGREQ/PINGRESP | implementado | conexão, timeout e fixture independente | matriz específica de keep-alive |
| §3.14 DISCONNECT | implementado | encerramento de sessão | cancelamento duravel Will testado na 0.6 local |
| §3.1.2.4 Clean Session | implementado | remoção, reabertura e sessão após queda do processo | escala e falhas de energia |
| §3.3.1.3 retained | implementado | criação/exclusão, deduplicação, restore e Mosquitto | quotas sob carga |
| §3.3.5 QoS de filtros sobrepostos | uma entrega no maior QoS aplicável | teste do ator e Mosquitto | ampliar combinações QoS externas |
| §4.7 filtros +/# e níveis vazios | implementado | vetores, propriedades geradas, limites e Mosquitto | benchmark de capacidade e fuzzing |
| §4.7.2 tópicos $ | implementado | matcher, retained e Mosquitto | matriz TLS/ACL externa |
| §3.1.2.5–6 Last Will | implementado na 0.6 local | codec/ator/store, ACL e9 integracoes | ampliar TLS/mTLS externo |

## Rastreabilidade

- `src/mqtt/topic.rs`: MQTT-4.7.1-1/2/3, MQTT-4.7.2-1 e MQTT-4.7.3-4;
  vetores, referência independente e limite de trabalho do matcher.
- `src/mqtt/router.rs`: MQTT-3.3.5-1, retenção, sobreposição, UNSUBSCRIBE,
  quotas, reconexão e revalidação de autorização no restore.
- `src/auth/mod.rs`: filtro literal concedido, deny-by-default e tópico concreto.
- `scripts/verify_interop.py`: clientes Mosquitto e fixtures independentes com
  os requisitos identificados em cada cenário.
- [Roteiro e ambiente](../wildcard-subscriptions.md), incluindo limites e
  distinção entre queda de processo e perda real de energia.

## Como atualizar

Registre a cláusula ou requisito no teste, adicione vetores válidos e inválidos,
verifique resposta e encerramento, classifique a evidência e atualize a matriz
sem declarar cobertura além do demonstrado.

Fonte: [OASIS MQTT Version 3.1.1](https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/mqtt-v3.1.1.html).


## Limite local de tópico/filtro — P41

Broker e CLI compartilham 1024 bytes UTF-8. Isso é quota local, abaixo do teto
MQTT-4.7.3-3, preservando ausência de normalização (MQTT-4.7.3-4).
Em Windows/Rust 1.98.1 passaram testes novos de nomes/filtros ASCII/multibyte,
wire PUBLISH/SUBSCRIBE/UNSUBSCRIBE, CLI e ACL. O teste novo de
roteamento/retained/offline/restore não chegou às asserções porque Store exige
fsync Unix. Validação externa/Unix desta alteração permanece pendente;
não declarar conformidade integral ou recuperação aprovada.
Veja [registro P41](../../prompts/registros/P41-topicos-1024.md).


### Atualizacao P41 em Unix - 2026-10-07

Ubuntu-26.04/Rust 1.99, mesma copia: teste de roteamento/retained/offline/restore
com 1024 bytes UTF-8 PASS. Pub/sub com mqtt-client proprio QoS 0/1/2 e
retained apos reinicio PASS em open-lab. Nao comprova TLS/ACL externa nem
interop Mosquitto, nao executada. Clippy 1.99 bloqueado por lint preexistente
em store.rs:296; release 0.5 nao aprovada. Veja registro P41.


## Incremento 0.6 - Last Will

MQTT-3.1.2-8..17/-24, MQTT-3.1.3-1 e MQTT-3.14.4-3 fundamentam
codec, fechamento e transicao duravel. Veja [Last Will](../last-will.md) e
[registro P42](../../prompts/registros/P42-0.6.0.md) para resultados reais.

## P43 - monitoramento opcional, validado localmente

Observabilidade não altera o contrato MQTT, formato durável ou quotas.

| Área | Evidência atual | Pendência |
| --- | --- | --- |
| Configuração loopback/porta/booleano | seis recusas reais Windows/Unix PASS, endpoints Unix PASS | ampliar testes de carga |
| Labels finitos e gauge de conexões | unitários e contadores sob tráfego Unix PASS | ampliar carga/conexões |
| Readiness do ator/writer e teardown | asserções Unix PASS, incluindo ator/writer encerrados | não comprova espaço livre/energia |
| QoS/retained/offline/Will 1024 UTF-8 com métricas | seis integrações HTTP/MQTT PASS | Mosquitto/TLS externo NOT_RUN |
| Regressão Will com cliente separado | nove integrações Unix PASS, baseline independente26c1019 | alterações C26 não cobertas por esta baseline |

Broker/admin e cliente estão em projetos separados, ambos inicialmente 0.7.0
local. Limite 1024 UTF-8 é contrato comum com constantes locais, sem dependência
do cliente no crate broker. Gates Windows não demonstram durabilidade Unix.
Registro P43 contém o aceite local; publicação 0.7 aguarda o mantenedor.

## Checkpoint P43 validado - 2026-10-08

Mesmo repo via WSL/Rust1.99:72 testes e gates completos PASS,6 integrações
monitoring e9 Will PASS, incluindo1024UTF-8/retained/offline. Cliente independente
baseline commit26c1019 usado sem editar melhorias C26 paralelas. Bloqueios Unix
anteriores resolvidos. MIT/quotas/documento preservados. Publicação0.7 fica com
usuário; sem commit/push/tag aqui. P44 segurança dinâmica preparado apenas.
Mosquitto/TLS/mTLS externo NOT_RUN; sem conformidade integral ou produção.
