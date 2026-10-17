# P170 rev1 — PUBREC negativo de assinante MQTT 5

Entrada: P169 conclui PUBACK negativo QoS1, mas P126 ainda recusa PUBREC negativo QoS2. O [MQTT 5 OASIS](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html) exige PUBREL apenas quando PUBREC tem motivo menor que `0x80`; motivo `0x80` ou maior libera o Packet Identifier. Este prompt precede o código.

Objetivo: aceitar PUBREC MQTT 5 válido do cliente com `0x00`, `0x80`, `0x83`, `0x87`, `0x90`, `0x91`, `0x97` ou `0x99`, Reason String única e User Property repetida. Recusar `0x10` exclusivo do servidor, códigos/propriedades inválidos, truncamento e duplicata. Em motivo negativo, concluir a tentativa QoS2 no estado durável, liberar quota/ID, não enviar PUBREL e manter a conexão; registrar só o código. PUBREC de sucesso, duplicatas e MQTT 3.1.1 permanecem como antes. Não prometer redistribuição de shared subscriptions nesta fatia.

Aceite: vetores de codec, transição do ator antes/depois do commit, TCP real com PUBREC negativo e ausência de PUBREL, entrega posterior na mesma conexão, restart sem replay e regressões QoS2/sessão/MQTT3.1.1. Rust/fmt/Clippy/build release/licenças/distribuição e CI exata. Documentar a parcela M01/M02/M05 e deixar PUBREL/PUBCOMP negativos e fases globais abertas. Sem migração/tag isolada.
