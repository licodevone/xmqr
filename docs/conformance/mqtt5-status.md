# MQTT 5 — publicação e assinatura iniciais da fase 6A

P115 aceita `CONNECT` MQTT 5 com Clean Start=1, Session Expiry ausente ou zero,
Receive Maximum válido opcional, sem Will e sem outras propriedades. Autenticação, ACL, limites e transporte
existentes continuam aplicados. O `CONNACK` de sucesso anuncia Maximum QoS=1 e
Maximum Packet Size=65536. `PUBLISH` sem propriedades em QoS 0/1, retained,
`PUBACK`, `PINGREQ` e `DISCONNECT` simples funcionam; uma publicação MQTT 5
chega a assinantes MQTT 3.1.1. P116 aceita SUBSCRIBE MQTT 5 com propriedades
vazias, opções padrão e QoS0/1, responde SUBACK com reason code por filtro e
envia PUBLISH MQTT 5 para mensagens vivas/retained. PUBACK de entrega QoS1 é
processado. C57/C58 disponibilizam `pub` e `sub --protocol-version 5`, mantendo
o padrão 3.1.1.

P119 acrescenta PUBACK MQTT 5 com reason code `0x87` e propriedades vazias
quando uma publicação QoS 1 é recusada pela ACL. A mensagem não entra no
roteador nem é confirmada como aceita; a conexão continua apta a uma publicação
permitida. A recusa QoS 0 continua encerrando a conexão neste subconjunto.
C60 faz o client mostrar os códigos de recusa de PUBACK/SUBACK.

O broker recusa Clean Start=0, Will e propriedades de CONNECT fora de Session
Expiry=0/Receive Maximum válido com `CONNACK` 5 `0x83` antes de criar sessão. Pacotes fora deste
subconjunto encerram a conexão. Ainda não há UNSUBSCRIBE MQTT 5, QoS 2,
propriedades de publicação, sessão persistente/expiração, Will Delay, flow
control, Topic Alias ou AUTH. Portanto, a fase 6A e o suporte MQTT 5 completo
permanecem pendentes. O formato durável v5 não muda.

Historicamente, P114 recusava todo `CONNECT` 5 com `CONNACK 0x84`; esse contrato
foi substituído por P115. Níveis desconhecidos continuam com recusa 3.1.1
`20 02 00 01`. Evidências: [P114](../../prompts/registros/P114-recusa-connect-mqtt5.md),
[P115](../../prompts/registros/P115-publicacao-mqtt5-inicial.md) e
[C57](../../../xmqr-client/prompts/registros/C57-publicacao-mqtt5-inicial.md),
[P116](../../prompts/registros/P116-assinatura-mqtt5-inicial.md) e
[C58](../../../xmqr-client/prompts/registros/C58-assinatura-mqtt5-inicial.md),
[P119](../../prompts/registros/P119-puback-mqtt5-acl.md) e
[C60](../../../xmqr-client/prompts/registros/C60-diagnostico-reason-code-mqtt5.md).

Fonte normativa: [OASIS MQTT 5](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html).
