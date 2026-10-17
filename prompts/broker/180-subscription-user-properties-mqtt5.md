# P180 — User Property em SUBSCRIBE e UNSUBSCRIBE MQTT 5

Entrada: P150 aceita Subscription Identifier em SUBSCRIBE; SUBSCRIBE/UNSUBSCRIBE ainda recusam qualquer User Property. Pela [norma OASIS MQTT 5](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html), a propriedade `0x26` pode se repetir nesses dois contextos. Este prompt precede o código.

Objetivo: aceitar pares UTF-8 válidos de User Property repetidos em SUBSCRIBE e UNSUBSCRIBE, inclusive junto do Subscription Identifier no primeiro, sem persistir metadados sem efeito sobre o roteamento. Aplicar limite explícito de 16 pares/2048 bytes e 256 bytes por campo, rejeitar truncamento, UTF-8 inválido, propriedade fora de contexto e excesso antes de qualquer alteração de assinatura. Preservar MQTT 3.1.1 e a semântica de SUBACK/UNSUBACK já aceita. Sem migração.

Aceite: vetores unitários de sucesso, repetição, combinação e negativos; TCP real com assinatura, publicação, remoção e ausência de alteração após propriedade inválida; regressão de opções/identificadores de assinatura, Rust/fmt/Clippy/build/licença/distribuição e CI. Atualizar conformance, paridade, checklist e registro como recorte parcial 6A/6D. Não declarar matriz MQTT 5 completa nem criar tag isolada.
