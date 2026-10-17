# P146 — quota QoS2 persistente após retomada MQTT 5

Entrada: P144 anuncia Receive Maximum inbound conforme `MQTT_MAX_INFLIGHT`, mas uma sessão retomada pode já ocupar toda a quota durável com QoS2 aguardando PUBREL. A quota de envio MQTT 5 reinicia por conexão; um novo PUBLISH válido para a conexão não deve comprometer o estado anterior. Este prompt precede qualquer código P146.

Objetivo: quando um PUBLISH QoS2 novo chega a uma sessão com `inbound_qos2` no limite, responder PUBREC MQTT 5 `0x97` (Quota exceeded), sem gravar nem entregar a mensagem, preservando conexão e transação antiga. Retransmissão com packet ID já aceito continua recebendo PUBREC de sucesso. Após PUBREL da pendência, aceitar um novo QoS2. O comportamento MQTT 3.1.1 para excesso permanece como antes; nenhuma migração do documento durável v10.

Aceite: teste de ator cobre limite1, duplicata, rejeição sem commit, PUBREL e recuperação; TCP real cobre persistência/restart, CONNACK Session Present e Receive Maximum, PUBREC 0x97, nenhuma entrega da rejeitada, aceitação após liberar a pendência; regressão P144 de violação na mesma conexão continua fechando a conexão. Fmt, testes, Clippy, build, licenças e CI. Atualizar checklist somente após CI; sem tag/release isolada nem ensaio ESP32.

Fonte normativa: OASIS MQTT 5 §3.5.2 (PUBREC `0x97` Quota exceeded) e §4.9 (send quota por conexão), https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html.
