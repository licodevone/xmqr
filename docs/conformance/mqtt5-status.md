# MQTT 5 — subconjunto inicial da fase 6A

P115 aceita `CONNECT` MQTT 5 com Clean Start=1, Session Expiry ausente ou zero,
Receive Maximum válido opcional, sem Will e sem outras propriedades. Autenticação, ACL, limites e transporte
existentes continuam aplicados. O `CONNACK` de sucesso anuncia Maximum QoS=1 e
Maximum Packet Size=65536. `PUBLISH` sem propriedades em QoS 0/1, retained,
`PUBACK`, `PINGREQ` e `DISCONNECT` simples funcionam; uma publicação MQTT 5
chega a assinantes MQTT 3.1.1. A opção `--protocol-version 5` do client C57
usa apenas `pub` QoS 0/1 e mantém o default 3.1.1.

O broker recusa Clean Start=0, Will e propriedades de CONNECT fora de Session
Expiry=0/Receive Maximum válido com `CONNACK` 5 `0x83` antes de criar sessão. Pacotes fora deste
subconjunto encerram a conexão. Ainda não há assinatura MQTT 5, QoS 2,
propriedades de publicação, sessão persistente/expiração, Will Delay, flow
control, Topic Alias ou AUTH. Portanto, a fase 6A e o suporte MQTT 5 completo
permanecem pendentes. O formato durável v5 não muda.

Historicamente, P114 recusava todo `CONNECT` 5 com `CONNACK 0x84`; esse contrato
foi substituído por P115. Níveis desconhecidos continuam com recusa 3.1.1
`20 02 00 01`. Evidências: [P114](../../prompts/registros/P114-recusa-connect-mqtt5.md),
[P115](../../prompts/registros/P115-publicacao-mqtt5-inicial.md) e
[C57](../../../xmqr-client/prompts/registros/C57-publicacao-mqtt5-inicial.md).

Fonte normativa: [OASIS MQTT 5](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html).
