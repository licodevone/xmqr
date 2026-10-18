# P204 — bits reservados do cabeçalho AUTH MQTT 5

Entrada: broker 0.36.0 publicado; P203 aceito em `main`; fase 6A global aberta. Após CONNACK, AUTH com cabeçalho `0xf1`–`0xff` é recusado genericamente sem motivo MQTT 5. Este prompt precede o código P204.

Objetivo: classificar os quatro bits reservados não zero de AUTH como Malformed Packet e enviar DISCONNECT MQTT 5 `0x81`, quando o limite de saída permite, antes de ler o corpo ou aplicar autenticação/estado. `0xf0` legítimo, MQTT 3.1.1 e demais cabeçalhos preservados.

Base: [OASIS MQTT 5.0 MQTT-3.15.1-1 e §4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html) exige bits 3–0 zero e fechamento para outros valores; `0x81` é a classificação adotada para pacote malformado.

Aceite: unitários para todos os 15 valores inválidos, corpo vazio e malformado; TCP real para limites e Will, fechamento, MQTT 3.1.1 e conexão válida posterior; regressão P203/P201. Fmt, suíte, Clippy, build release, licenças, distribuição, CI da fonte exata. Registrar limites; sem tag/release isolada.

Revisão 2 antes da correção: a primeira implementação compartilhou `FixedHeaderFlagsInvalid` com P178. Unitários e build passaram, mas o ensaio TCP falhou para `0xf1`: o roteador emitiu `0x82`, pois esse marcador histórico representa erro de protocolo de PINGREQ/DISCONNECT. Separar AUTH em marcador malformado próprio e mapear a `0x81`, preservando o motivo P178. Repetir os gates que dependem do binário corrigido; a falha inicial não é aceite.
