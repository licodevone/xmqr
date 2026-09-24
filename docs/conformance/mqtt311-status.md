# Estado de implementação MQTT 3.1.1

Esta matriz descreve evidências internas da série XMQR `0.4.x`. Ela não é uma
declaração de conformidade completa. “Implementado” significa que existe código
e teste local; “interoperabilidade pendente” significa que ainda falta evidência
automatizada com implementações independentes.

| Área OASIS MQTT 3.1.1 | Estado em 0.4.x | Evidência local | Pendência |
| --- | --- | --- | --- |
| §3.1 `CONNECT` | implementado para os perfis XMQR | testes de codec, autenticação e conexão | ampliar vetores externos |
| §3.2 `CONNACK` | implementado | testes de autenticação aceita/recusada | interoperabilidade |
| §3.3 `PUBLISH` QoS 0/1/2 | implementado | codec, roteador e testes de sessão | matriz externa completa |
| §§3.4–3.7 ACKs de QoS | implementado | vetores conhecidos e recuperação QoS 1/2 | falhas de rede externas |
| §§3.8–3.9 `SUBSCRIBE`/`SUBACK` | tópicos exatos | codec, ACL e roteador | `+` e `#` entram em 0.5 |
| §§3.10–3.11 `UNSUBSCRIBE`/`UNSUBACK` | implementado | codec, sessão e persistência | interoperabilidade |
| §§3.12–3.13 `PINGREQ`/`PINGRESP` | implementado | máquina de conexão e timeout | matriz específica |
| §3.14 `DISCONNECT` | implementado | encerramento de sessão | casos externos |
| §3.1.2.4 `Clean Session` | implementado | reabertura e remoção de sessão | escala e falhas |
| §3.3.1.3 mensagens retidas | implementado | criação, entrega, exclusão e reabertura | interoperabilidade |
| §3.1.2.5–6 Last Will | não implementado | rejeição explícita no codec | implementação futura |
| §4.7 filtros `+` e `#` | não publicado em 0.4 | — | série 0.5 |

## Como atualizar

Toda mudança de comportamento MQTT deve:

1. registrar a seção ou requisito normativo relevante no teste;
2. adicionar vetores válidos e inválidos;
3. verificar a resposta e o encerramento previstos pela versão negociada;
4. indicar se a evidência é unitária, integração ou interoperabilidade;
5. atualizar esta matriz sem declarar cobertura mais ampla que a evidência.

Fonte normativa: [OASIS MQTT Version 3.1.1](https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/mqtt-v3.1.1.html).
