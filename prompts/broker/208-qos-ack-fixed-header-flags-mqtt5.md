# P208 — flags reservadas em PUBACK/PUBREC/PUBCOMP MQTT 5

Entrada: broker 0.37.0 publicado, P207 aceito em `main`, fase 6A ainda aberta. Os cabeçalhos inválidos `0x41`–`0x4f`, `0x51`–`0x5f` e `0x71`–`0x7f` caem em erro genérico após CONNACK, sem DISCONNECT MQTT 5. Este prompt precede o código P208.

Objetivo: classificar os 45 cabeçalhos como Malformed Packet e responder DISCONNECT `0x81` antes de interpretar o corpo, sem consumir identificador QoS ou alterar estado. Preservar `0x40`, `0x50`, `0x70` válidos e a regra P200 de PUBREL (`0x62`); no MQTT 3.1.1, manter fechamento sem DISCONNECT MQTT 5. Não alterar estado durável v15, client ou admin independente.

Aceite: unitários para os 45 valores, corpos vazios/inválidos e cabeçalhos válidos; fixture TCP com limites de cada tipo, DISCONNECT, fechamento, Will, MQTT 3.1.1 e conexão saudável posterior. Regressões P200/P205/P207, fmt, suíte, Clippy, build, licenças, contratos de distribuição e CI da fonte exata. Registrar checklist parcial; sem tag/release isolada nem alegar conclusão da fase 6A.

Referência: [OASIS MQTT 5, §2.1.3 e §4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html).
