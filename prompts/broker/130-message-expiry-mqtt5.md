# P130 rev1 — Message Expiry Interval MQTT 5

Entrada: `main` após P129, broker0.18.0 publicado. P128 armazena Session Expiry, mas recusa propriedades PUBLISH; mensagens retidas/offline não expiram.

Objetivo: receber `Message Expiry Interval` (0x02) em PUBLISH MQTT 5, guardar deadline durável, eliminar cópias retidas/offline vencidas antes de iniciar entrega e encaminhar a propriedade com tempo restante a assinantes MQTT 5. Preservar o comportamento 3.1.1 e o subconjunto MQTT 5 existente. Fonte: [OASIS MQTT 5 §3.3.2.3.3](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html).

Escopo: apenas esta propriedade PUBLISH; rejeitar duplicata, truncamento e propriedades fora do subconjunto. Revisar formato durável para v7 com migração v1–v6. Persistir instante absoluto de expiração e intervalo original para cálculo do valor encaminhado. Para QoS2, verificar prazo ao receber PUBREL. Não descartar publicação cujo envio já começou durante handshake QoS. Recusar falhas de relógio/overflow sem confirmar a mensagem. Evitar entrega da cópia vencida inclusive após reinício. Documentar rollback para estado v7.

Aceite: codec e roteador com testes positivos/negativos, retained/offline antes e depois do prazo, reinício/migração, QoS0/1/2, interop Mosquitto e client C69, fmt/test/Clippy/build, CI verde; atualizar plano apenas depois dos gates.
