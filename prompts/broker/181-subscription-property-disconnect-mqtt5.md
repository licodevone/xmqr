# P181 — diagnóstico de propriedade inválida de assinatura MQTT 5

Entrada: P180 aceita User Property contextual em SUBSCRIBE/UNSUBSCRIBE. A propriedade com identificador não permitido ainda fecha silenciosamente após CONNACK. OASIS MQTT 5 §2.2.2 classifica identificador impróprio para o tipo do pacote como Malformed Packet (`0x81`); §3.8.2.1.2 classifica Subscription Identifier duplicado como Protocol Error (`0x82`). Este prompt precede o código.

Objetivo: distinguir somente esses dois erros de propriedade já reconhecíveis após CONNACK MQTT 5 e responder com DISCONNECT `0x81` ou `0x82`, respeitando Maximum Packet Size negociado, antes de fechar. Nenhum SUBACK/UNSUBACK nem alteração de assinatura pode ocorrer. Preservar os diagnósticos `0x94`/`0x95` e os demais erros de P175–P178; MQTT 3.1.1 continua apenas fechando. Não classificar genericamente falhas de I/O, timeout, UTF-8, truncamento ou quotas neste recorte.

Aceite: unitários do codec com tipos distintos e negativos de ambos os pacotes; TCP real com `e0 02 81 00`/`e0 02 82 00`, fechamento e Will, ausência de alteração após reconexão durável, MQTT 3.1.1 e regressões P175–P180. Fmt/testes/Clippy/build/licença/distribuição e CI. Documentar como parcial 6A; sem migração nem tag isolada.
