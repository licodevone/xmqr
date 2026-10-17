# MQTT 5 — subconjunto das fases 6A–6D

P168 acrescenta Eclipse Paho Python 2.1.0 ao gate MQTT 5 com ID atribuído,
Session Present, QoS0/1/2, retained e fila offline. O gate Mosquitto existente
continua na CI; duas bibliotecas externas cobrem esses cenários selecionados.
Isto não encerra a matriz normativa de propriedades/reason codes nem 6A global.

P166, ainda na árvore de desenvolvimento, aceita Client Identifier vazio no
CONNECT MQTT 5, atribui ID exclusivo e o devolve em CONNACK `0x12`. O pacote
é recusado antes de registrar sessão se o limite anunciado não comportar a
propriedade obrigatória. MQTT 3.1.1 mantém a recusa. C97 é o par de CLI; C98
permite reutilizar o ID de 37 bytes e C99 criar uma sessão com expiração
configurada para posterior reconexão manual. O client não persiste estado QoS local;
esta parcela não encerra o aceite global da fase 6A.

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
P131 aceita Session Expiry Interval no DISCONNECT normal MQTT 5, aplicado no
mesmo commit do encerramento. O client independente ainda envia DISCONNECT sem
essa propriedade.
P132 aceita Will MQTT 5 com propriedade Will Delay Interval opcional. O Will
fica durável até publicação após o atraso ou término da sessão, o que ocorrer
primeiro; retomada Clean Start=0 antes do prazo e DISCONNECT normal cancelam.
C70 expõe `--will-delay-seconds` no client. Após P163/C94, a árvore de
desenvolvimento também aceita Payload Format Indicator, Content Type,
Response Topic, Correlation Data e User Property ordenada no Will, inclusive
com atraso, retained, fila offline e recuperação após reinício. P164/C95
acrescentam Message Expiry Interval do Will: o intervalo fica no Will pendente
e o prazo começa na publicação efetiva, não no CONNECT. O documento passa de
v14 para v15 na primeira gravação. Broker 0.29.0, client 0.26.0 e admin
independente 0.10.0 distribuem esse recorte. Broker 0.28.0 não abre v15;
broker 0.30.0 e client 0.27.0 distribuem também P166/C97–C99 sem nova migração;
admin 0.9.0 ainda consegue transportar backup bruto, sem homologação como par.
Se o processo cair com a conexão ainda ativa, o instante da queda não é
durável; por segurança contra perda silenciosa, a contagem começa na recuperação.
P123 acrescenta Request Problem
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
recebidos nesses pacotes ainda fecham a conexão neste subconjunto, exceto
PUBACK recebido após P169: códigos negativos válidos do client, Reason String
única e User Property repetida concluem a tentativa QoS1 sem fechar a conexão.
PUBREC/PUBREL/PUBCOMP negativos permanecem fora deste recorte.
P134 aplica Receive Maximum do CONNECT MQTT 5 (padrão 65535) aos PUBLISH QoS1/2
enviados pelo broker nesta conexão. A quota limita entregas vivas, retidas,
offline e replay; PUBACK/PUBCOMP liberam vagas. QoS0 e PUBREL não consomem
quota. O valor não é gravado na sessão e pode mudar na reconexão. C72 expõe
`mqtt-client sub --protocol-version 5 --receive-maximum 1..65535`.
P144 anuncia no CONNACK MQTT 5 o limite de recepção QoS1/2 do broker (1..32)
conforme a quota `MQTT_MAX_INFLIGHT`, quando os três bytes adicionais cabem.
Com Maximum Packet Size do client 5..7 ou 10..15, a propriedade é omitida para
preservar os fallbacks de CONNACK P136/P138; nesse caso o broker ainda recusa
excesso de estado sem commit parcial. P146 trata a retomada com quota inbound
QoS2 durável cheia: novo packet ID recebe PUBREC `0x97` sem commit nem entrega,
enquanto duplicata de packet ID anterior mantém PUBREC de sucesso; PUBREL da
transação antiga libera a vaga. Dentro da mesma conexão, exceder a quota
anunciada continua encerrando a conexão. A fase 6C global permanece aberta.
P136/C73 aceitam Maximum Packet Size em CONNECT e limitam todos os pacotes
enviados pelo broker ao client nessa conexão. O CONNACK omite a propriedade
informativa de tamanho se ela não couber. PUBLISH grande demais é descartado
e sua obrigação QoS é concluída no estado durável, inclusive em replay; um
pacote essencial grande demais encerra a conexão. O broker continua anunciando
seu teto de entrada de 65536 bytes quando o CONNACK completo cabe. P138,
distribuído a partir de 0.21.0, anuncia Topic Alias Maximum=16 quando há ao menos
13 bytes de limite de saída e aceita alias de entrada 1..16 por conexão. Um
PUBLISH com nome define/redefine o alias; nome vazio o usa. Alias inválido,
desconhecido, duplicado ou truncado fecha a conexão sem publicar. A tabela não
é durável nem reaproveitada em reconnect/takeover. P139 acrescenta alias de
saída quando o assinante anuncia Topic Alias Maximum positivo: até 16 tópicos
por conexão, primeira entrega com nome completo e alias, próximas com nome
vazio e alias. Se a forma inicial com alias exceder Maximum Packet Size, o
broker usa o nome completo sem alias quando couber. QoS0/1/2, retained e
reinício foram testados em TCP real. O client XMQR C75 recebe e exibe o tópico
resolvido. O Mosquitto 2.0.22 encerra a conexão ao receber a segunda forma
abreviada válida, inclusive em fixture independente; esta direção externa
não está homologada. P141, aceito em `main` após 0.21.0, aceita Payload Format
Indicator `0x01` (0/1) e Content Type `0x03` (texto MQTT de até 256 bytes) em
PUBLISH MQTT 5. Ambas são preservadas em QoS0/1/2, retained, offline e após
restart, com documento durável v9 na próxima gravação. Em assinantes MQTT 3.1.1,
as propriedades são omitidas. O broker não verifica se o payload anunciado como
UTF-8 realmente tem essa codificação; o MQTT 5 permite ao receptor optar por
não fazer essa validação. Client C77 valida payload UTF-8 antes da conexão quando
o indicador é 1. P142/C78, distribuídos em 0.22.0/0.20.0, acrescentam
Response Topic `0x08`, Correlation Data `0x09` binária e User Property `0x26`
repetível em ordem no PUBLISH. O broker persiste em documento v10 e omite as
propriedades em assinantes 3.1.1. O client aceita os argumentos de publicação;
C80 passou a exibi-las em `sub --output jsonl` na árvore de desenvolvimento,
após a release 0.20.0. Outras propriedades seguem pendentes; não se declara
conformidade MQTT 5 integral.

P147/C84 aceitam Retain Handling 0/1/2 por filtro SUBSCRIBE MQTT 5. Zero
preserva o envio anterior, um só envia retained para filtro que ainda não
existia na sessão e dois não envia retained no SUBSCRIBE. A existência da
assinatura sobrevive ao restart sem novo campo durável. P148/C85 acrescentam
No Local e Retain As Published por filtro, com filtros sobrepostos e sessão
retomada. O broker grava essas opções em documento v11; versões anteriores
continuam legíveis com opções desativadas por padrão. P150 acrescenta
Subscription Identifier por filtro no estado v12 e nas entregas MQTT 5,
inclusive após restart. P153 admite compartilhamento apenas entre sessões
MQTT 5 ativas e temporárias (Session Expiry=0): um destinatário por grupo/filtro,
sem retained inicial e com cópia normal independente. P154 acrescenta
associação de sessão persistente no documento v13, seleção de membro offline
persistente quando não há membro ativo e replay QoS2 à sessão escolhida após
restart. O contador de escolha é transitório; a associação é durável. QoS0 sem
membro ativo pode ser descartado. Uma entrega QoS1 atribuída e não confirmada
aguarda reconexão da mesma sessão; quando a sessão termina, ela não é
redistribuída neste recorte. AUTH continua fora da fase 6D.

P156, ainda na árvore de desenvolvimento, guarda o grupo e Retain original de
cópias compartilhadas QoS1 em documento v14. Após término definitivo da sessão
escolhida, tenta outro membro elegível, aplicando a ACL, QoS, RAP, Subscription
Identifier e quotas do destinatário. Sem membro elegível/capacidade, descarta
a obrigação; QoS2 continua vinculado à sessão escolhida. Fonte v14 ainda não
foi distribuída nem validada pelo admin independente 0.8.0.

O broker recusa propriedades de CONNECT e Will fora do subconjunto
P132 com `CONNACK` 5 `0x83` antes de criar sessão. Pacotes fora deste
subconjunto encerram a conexão. Ainda não há
demais propriedades de publicação, fluxo de envio completo do client ou AUTH.
Portanto, a fase 6A e o suporte MQTT 5 completo
permanecem pendentes. P128 migra o documento durável de v5 para v6 na próxima
gravação; brokers anteriores não podem reabrir estado v6. Um rollback exige
backup privado anterior à migração. P130 migra o documento de v6 para v7;
P132 migra de v7 para v8. P141, distribuído em 0.22.0, migra de v8
para v9 na próxima gravação; P142 migra de v9 para v10; P148 migra de v10
para v11; P150 migra de v11 para v12, P154 de v12 para v13 e P156 da árvore de
desenvolvimento de v13 para v14. O admin independente 0.8.0 lê v13, mas não v14;
0.7.0 lê v12, mas não abre v13; 0.5.0 não abre v11 e 0.6.0 não abre v12. Preserve backup privado
v12 antes da primeira gravação v13 para rollback a broker 0.25.0; v11 é
necessário para voltar a broker 0.24.0, ou v10 para
rollback anterior a v11. P141 não reabre v10
sem backup privado v9 anterior; 0.21.0 não reabre v9/v10 sem backup privado v8.
A versão 0.18.0 não pode reabrir v7/v8 sem backup anterior.

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
[C69](../../../xmqr-client/prompts/registros/C69-message-expiry-mqtt5.md) e
[P131](../../prompts/registros/P131-disconnect-session-expiry-mqtt5.md),
[P132](../../prompts/registros/P132-will-delay-mqtt5.md) e
[C70](../../../xmqr-client/prompts/registros/C70-will-delay-mqtt5.md),
[P134](../../prompts/registros/P134-receive-maximum-mqtt5.md) e
[C72](../../../xmqr-client/prompts/registros/C72-receive-maximum-mqtt5.md),
[P136](../../prompts/registros/P136-maximum-packet-size-mqtt5.md) e
[C73](../../../xmqr-client/prompts/registros/C73-maximum-packet-size-mqtt5.md),
[P138](../../prompts/registros/P138-topic-alias-entrada-mqtt5.md),
[P139](../../prompts/registros/P139-topic-alias-saida-mqtt5.md) e
[C75](../../../xmqr-client/prompts/registros/C75-topic-alias-maximum-mqtt5.md),
[P141](../../prompts/registros/P141-publish-payload-format-content-type-mqtt5.md) e
[C77](../../../xmqr-client/prompts/registros/C77-publish-payload-format-content-type-mqtt5.md),
[P142](../../prompts/registros/P142-publish-request-properties-mqtt5.md) e
[C78](../../../xmqr-client/prompts/registros/C78-publish-request-properties-mqtt5.md) e
[C80](../../../xmqr-client/prompts/registros/C80-subscriber-publish-metadata-mqtt5.md) e
[P144](../../prompts/registros/P144-connack-receive-maximum-mqtt5.md).
[P146](../../prompts/registros/P146-qos2-resume-quota-mqtt5.md).
[P147](../../prompts/registros/P147-retain-handling-mqtt5.md) e
[C84](../../../xmqr-client/prompts/registros/C84-retain-handling-mqtt5.md).

Fonte normativa: [OASIS MQTT 5](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html).
