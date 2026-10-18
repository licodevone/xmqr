# P200 — flags reservadas de SUBSCRIBE, UNSUBSCRIBE e PUBREL MQTT 5

Estado de entrada: broker 0.35.0/P199 em `main`, estado durável v15; client 0.28.0/C105 em validação de CI. O leitor aceita somente cabeçalhos `0x82`, `0xA2` e `0x62`, mas outras flags para esses três tipos caem no erro genérico sem motivo MQTT 5. O aceite 6A/M01 ainda está aberto.

Objetivo observável: após CONNACK MQTT 5, identificar qualquer nibble reservado diferente de `0x2` nos cabeçalhos SUBSCRIBE, UNSUBSCRIBE e PUBREL, responder DISCONNECT `0x81` quando couber no Maximum Packet Size e fechar a conexão antes de interpretar o corpo ou alterar assinaturas/estado QoS. Cabeçalhos válidos mantêm o fluxo. MQTT 3.1.1 conserva seu comportamento de fechamento sem motivo MQTT 5.

Fonte normativa: [OASIS MQTT 5.0](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html), MQTT-3.8.1-1, MQTT-3.10.1-1 e MQTT-3.6.1-1 exigem nibble `0x2` e classificam outra combinação como Malformed Packet; §4.13.1 permite DISCONNECT com `0x81` antes de fechar. Não generalizar esta fatia para outros tipos de pacote ou transformar erros semânticos em erros de framing.

Escopo: classificador de cabeçalho no codec, mapeamento do erro no loop da conexão, testes unitários, fixture TCP independente, CI, registro e checklist. Testar pelo menos os nibbles 0, 1, 3 e 15 para os três tipos, inclusive corpo que seria válido sob `0x2`; provar que não há aplicação parcial do SUBSCRIBE/UNSUBSCRIBE nem transição indevida de QoS 2. Limite de pacote menor que quatro bytes deve impedir DISCONNECT sem manter a conexão. Preservar MQTT 3.1.1, limites, sessão e Will.

Aceite: fmt, suíte Rust completa, Clippy `-D warnings`, build release e inventário, fixture TCP com broker real, CI da fonte exata. Registrar falhas e não marcar P200 até todos os gates. Fase 6A global e M01/M02 permanecem abertas; sem tag/release isolada.
