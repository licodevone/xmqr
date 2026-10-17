# P187 — motivos contextuais de propriedades em ACKs QoS MQTT 5

Entrada: P181/P183–P186 classificam propriedades de SUBSCRIBE, CONNECT/Will, PUBLISH, AUTH e DISCONNECT. PUBACK/PUBREC/PUBREL/PUBCOMP ainda misturam propriedade fora de contexto e Reason String duplicada num fechamento silencioso. Este prompt precede o código P187.

Objetivo: após CONNACK MQTT 5, ACK de QoS do client com identificador de propriedade fora de contexto recebe DISCONNECT `0x81`; Reason String duplicada recebe `0x82`. User Property repetível, motivos de sucesso/erro já admitidos, conclusão QoS2 e ausência de replay indevido devem permanecer. MQTT 3.1.1 segue sem DISCONNECT MQTT 5. Truncamento, UTF-8 inválido, Packet Identifier zero, Reason Code inválido, quotas e limites locais não recebem essa classificação nesta fatia. Will segue a desconexão de erro; limite de pacote de saída respeitado.

Aceite: tabela unitária PUBACK/PUBREC/PUBREL/PUBCOMP com positivos/negativos por classe; TCP de quatro tipos, Will, MQTT 3.1.1 e ausência de alteração de estado por pacote rejeitado; regressões P169–P171/P175/P181/P183–P186, fmt/test/Clippy/build/licenças/distribuição e CI. Atualizar conformance, matriz, checklist e registro como parcial 6A/6C, sem migração nem tag isolada.
