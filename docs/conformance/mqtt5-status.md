# MQTT 5 — subconjunto da fase 6A

P115 iniciou `CONNECT` MQTT 5 com Clean Start=1 e Session Expiry ausente ou zero.
P127 acrescenta Clean Start=0/1 independente de Session Expiry=0/infinita (`0xFFFFFFFF`).
O broker informa Session Present conforme o estado durável, conserva assinaturas
e QoS offline após reinício para expiração infinita e remove a sessão ao encerrar
a conexão com expiração zero. P128 aceita intervalos finitos 1..4294967294,
grava o prazo após desconexão e remove sessões vencidas no ator e na recuperação.
P130 acrescenta `Message Expiry Interval` (0x02) em PUBLISH MQTT 5: o broker
grava deadline absoluto em documento v7, remove cópias retidas/offline vencidas
antes da entrega e encaminha o prazo restante em PUBLISH MQTT 5. QoS2 recebido
é avaliado no PUBREL; uma entrega QoS já iniciada conserva seu handshake.
O client C69 envia `--message-expiry-seconds` em `pub --protocol-version 5`.
Se o processo cair com a conexão ainda ativa, o instante da queda não é
durável; por segurança contra perda silenciosa, a contagem começa na recuperação.
Receive Maximum válido opcional, sem Will. P123 acrescenta Request Problem
Information, Request Response Information, Topic Alias Maximum e User Property
no CONNECT. O broker valida valores e pares, mas não ecoa nem armazena essas
propriedades e não envia aliases ou informações opcionais de resposta.
Autenticação, ACL, limites e transporte
existentes continuam aplicados. Após P122, o `CONNACK` de sucesso omite Maximum QoS,
indicando o padrão 2, e anuncia Maximum Packet Size=65536. `PUBLISH` em QoS 0/1/2, com propriedades vazias ou Message Expiry, retained,
`PUBACK`, `PINGREQ` e `DISCONNECT` simples funcionam; uma publicação MQTT 5
chega a assinantes MQTT 3.1.1. P116 aceita SUBSCRIBE MQTT 5 com propriedades
vazias, opções padrão e QoS0/1/2, responde SUBACK com reason code por filtro e
envia PUBLISH MQTT 5 para mensagens vivas/retained. PUBACK de entrega QoS1 é
processado. C57/C58 disponibilizam `pub` e `sub --protocol-version 5`, mantendo
o padrão 3.1.1.

P119 acrescenta PUBACK MQTT 5 com reason code `0x87` e propriedades vazias
quando uma publicação QoS 1 é recusada pela ACL. A mensagem não entra no
roteador nem é confirmada como aceita; a conexão continua apta a uma publicação
permitida. A recusa QoS 0 continua encerrando a conexão neste subconjunto.
C60 faz o client mostrar os códigos de recusa de PUBACK/SUBACK.
P120 usa SUBACK `0x87` por filtro negado pela ACL em MQTT 5, sem commit se
todos forem negados; MQTT 3.1.1 preserva SUBACK `0x80`. C61 exibe motivo e
código de CONNACK recusado, por exemplo senha incorreta `0x86`.
P121 aceita UNSUBSCRIBE MQTT 5 com propriedades vazias e responde UNSUBACK
com motivo por filtro na ordem recebida: `0x00` removido ou `0x11` inexistente.
Remoções são confirmadas após commit; cancelamento sem alteração não grava.
C62 aguarda UNSUBACK para cada filtro antes do DISCONNECT após `sub --count`.
P122/C63 acrescentam o ciclo QoS2 PUBREC/PUBREL/PUBCOMP em publicação e
assinatura MQTT 5. Uma recusa de ACL de publicação QoS2 retorna PUBREC `0x87`
sem commit; o client aguarda PUBCOMP antes de relatar sucesso e exibe recusa
PUBREC/PUBCOMP com código. O estado QoS2 existente continua durável.
P126 aceita as três formas de sucesso dos ACKs MQTT 5 recebidos (ID apenas,
motivo `0x00`, motivo `0x00` com comprimento de propriedades zero) e as formas
equivalentes de DISCONNECT normal. Motivos de falha e propriedades não vazias
recebidos nesses pacotes ainda fecham a conexão neste subconjunto.
Receive Maximum pode constar no CONNECT, mas o controle completo de fluxo de
entrega ainda depende da fase 6C; não se declara conformidade MQTT 5 integral.

O broker recusa Will e propriedades de CONNECT fora do subconjunto
P127 com `CONNACK` 5 `0x83` antes de criar sessão. Pacotes fora deste
subconjunto encerram a conexão. Ainda não há
outras propriedades de publicação, Will Delay, flow
control, Topic Alias ou AUTH. Portanto, a fase 6A e o suporte MQTT 5 completo
permanecem pendentes. P128 migra o documento durável de v5 para v6 na próxima
gravação; brokers anteriores não podem reabrir estado v6. Um rollback exige
backup privado anterior à migração. P130 migra o documento de v6 para v7;
v0.18.0 não pode reabrir estado v7 sem backup anterior.

Historicamente, P114 recusava todo `CONNECT` 5 com `CONNACK 0x84`; esse contrato
foi substituído por P115. Níveis desconhecidos continuam com recusa 3.1.1
`20 02 00 01`. Evidências: [P114](../../prompts/registros/P114-recusa-connect-mqtt5.md),
[P115](../../prompts/registros/P115-publicacao-mqtt5-inicial.md) e
[C57](../../../xmqr-client/prompts/registros/C57-publicacao-mqtt5-inicial.md),
[P116](../../prompts/registros/P116-assinatura-mqtt5-inicial.md) e
[C58](../../../xmqr-client/prompts/registros/C58-assinatura-mqtt5-inicial.md),
[P119](../../prompts/registros/P119-puback-mqtt5-acl.md) e
[C60](../../../xmqr-client/prompts/registros/C60-diagnostico-reason-code-mqtt5.md),
[P120](../../prompts/registros/P120-suback-mqtt5-acl.md) e
[C61](../../../xmqr-client/prompts/registros/C61-connack-mqtt5-reason.md),
[P121](../../prompts/registros/P121-unsubscribe-mqtt5.md) e
[C62](../../../xmqr-client/prompts/registros/C62-unsubscribe-mqtt5.md),
[P122](../../prompts/registros/P122-qos2-mqtt5.md) e
[C63](../../../xmqr-client/prompts/registros/C63-qos2-mqtt5.md),
[P123](../../prompts/registros/P123-connect-properties-mqtt5.md) e
[C64](../../../xmqr-client/prompts/registros/C64-connect-properties-mqtt5.md),
[P126](../../prompts/registros/P126-ack-disconnect-mqtt5.md),
[P127](../../prompts/registros/P127-sessao-mqtt5-zero-infinita.md) e
[C66](../../../xmqr-client/prompts/registros/C66-sessao-mqtt5-zero-infinita.md),
[P128](../../prompts/registros/P128-expiracao-finita-sessao-mqtt5.md) e
[C67](../../../xmqr-client/prompts/registros/C67-expiracao-finita-sessao-mqtt5.md),
[P130](../../prompts/registros/P130-message-expiry-mqtt5.md) e
[C69](../../../xmqr-client/prompts/registros/C69-message-expiry-mqtt5.md).

Fonte normativa: [OASIS MQTT 5](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html).
