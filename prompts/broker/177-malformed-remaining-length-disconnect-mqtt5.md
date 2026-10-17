# P177 — DISCONNECT `0x81` para Remaining Length malformado MQTT 5

Entrada: P175 diferencia pacote acima do teto (`0x95`) e P176 diferencia Topic Alias inválido (`0x94`). O parser ainda encerra silenciosamente quando os quatro bytes de Remaining Length indicam continuação, uma codificação proibida no cabeçalho MQTT.

Objetivo: criar erro tipado somente para esse cabeçalho malformado e, após CONNACK MQTT 5, enviar DISCONNECT `0x81` dentro do Maximum Packet Size negociado antes de fechar. Não classificar como malformado um cabeçalho apenas parcial, EOF, timeout, falha de I/O, pacote excessivo ou alias inválido. MQTT 3.1.1 continua encerrando sem DISCONNECT MQTT 5. Nenhum estado durável muda.

Aceite: vetor unitário de quatro bytes com continuação e de cabeçalho parcial; TCP real com bytes `e0 02 81 00`, fechamento e ausência de entrega; regressão de P175/P176, MQTT 3.1.1 e Will; gates Rust/fmt/Clippy/build, licença, distribuição e CI. Registrar escopo parcial no plano; não declarar matriz de todos os erros malformados completa. Sem tag isolada.
