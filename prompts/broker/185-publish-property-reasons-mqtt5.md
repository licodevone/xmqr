# P185 — DISCONNECT contextual para propriedades PUBLISH MQTT 5

Entrada: P181/P183/P184 classificam propriedades de assinatura e CONNECT/Will, mas PUBLISH ainda mistura identificador fora de contexto, duplicata de propriedade única e Payload Format Indicator fora de 0/1 num fechamento silencioso. Este prompt precede qualquer código P185.

Objetivo: após CONNACK MQTT 5, PUBLISH com identificador de propriedade fora do contexto deve receber DISCONNECT `0x81`; duplicata de Message Expiry, Topic Alias, Payload Format Indicator, Content Type, Response Topic ou Correlation Data, e PFI >1 devem receber `0x82`. Preservar `0x94` para Topic Alias zero, excedente ou desconhecido, as propriedades User Property repetíveis válidas, ACKs e roteamento normais, MQTT 3.1.1 e os limites do DISCONNECT negociados. Não classificar truncamento, UTF-8 inválido, topic name inválido, quotas ou limites locais como `0x81`/`0x82` nesta fatia. Sem entrega/commit do PUBLISH rejeitado; Will aplicável segue a desconexão de erro.

Aceite: testes unitários para cada classe e valor, TCP QoS0/1 com ausência de publicação e Will, regressão P141/P142/P176/P181/P183/P184, MQTT 3.1.1, fmt/test/Clippy/build/licenças/distribuição e CI. Atualizar matriz, conformance, checklist e registro com aceite parcial 6A/6C, sem migração ou tag isolada.
