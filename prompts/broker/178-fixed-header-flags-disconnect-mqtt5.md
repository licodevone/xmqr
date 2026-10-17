# P178 — DISCONNECT `0x82` para flags fixas inválidas MQTT 5

Entrada: P175–P177 distinguem tamanho excessivo, Topic Alias inválido e Remaining Length malformado. Um pacote PINGREQ ou DISCONNECT com bits reservados no primeiro byte ainda fecha a conexão sem diagnóstico.

Objetivo: após CONNACK MQTT 5, classificar somente flags fixas inválidas de PINGREQ e DISCONNECT como erro de protocolo, enviar DISCONNECT `0x82` respeitando Maximum Packet Size e fechar sem alterar estado. Não mascarar falhas de transporte, timeout ou os motivos `0x81`, `0x94`, `0x95`. O mesmo pacote em MQTT 3.1.1 apenas fecha.

Aceite: vetores unitários para `c1 00` e `e1 00`; TCP real com `e0 02 82 00`, fechamento e Will, sem resposta PINGRESP; regressão de P175–P177, Rust/fmt/Clippy/build/licença/distribuição/CI. Registrar como parte da matriz de erros ainda incompleta; sem migração nem tag isolada.
