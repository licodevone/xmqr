# P205 — correção normativa das flags fixas de DISCONNECT/PINGREQ MQTT 5

Entrada: P178 registrou DISCONNECT `0x82` para cabeçalhos PINGREQ/DISCONNECT com flags não zero. P204 adotou marcador separado para AUTH e evidenciou que a classificação compartilhada não representa a regra específica de DISCONNECT. Este prompt precede qualquer correção P205.

Objetivo: corrigir a resposta MQTT 5 para `0x81` (Malformed Packet) em DISCONNECT `0xe1`–`0xef`, exigida por [MQTT-3.14.1-1](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html). Revisar PINGREQ `0xc1`–`0xcf` à luz do cabeçalho fixo e classificar os bits reservados não zero também como `0x81`. Receber o pacote completo e rejeitar antes do corpo; não alterar estado ou Will além da política de fechamento. MQTT 3.1.1 mantém fechamento anterior. `0xc0` e `0xe0` válidos permanecem.

Aceite: teste unitário para os 15 valores de cada tipo, TCP real com `0x81`, fechamento, Will e conexão normal posterior, regressões P203/P204. Atualizar o registro histórico P178 com correção explícita, sem apagar sua evidência; revisar checklist para distinguir o comportamento antigo do atual. Gates fmt, suíte, Clippy, build release, licenças, distribuição e CI da fonte exata. Sem tag/release isolada.
