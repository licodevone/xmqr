# P203 — tipo de controle reservado zero no MQTT 5

Entrada: broker/admin legado 0.36.0 publicado; fase 6A global aberta. O decoder após CONNACK rejeita bytes iniciais `0x00`–`0x0f` pelo erro genérico sem motivo MQTT 5. Este prompt precede o código P203.

Objetivo observável: identificar o tipo de controle zero reservado logo após ler o cabeçalho de um pacote completo, antes de interpretar o corpo, e enviar DISCONNECT MQTT 5 `0x81` (Malformed Packet) quando o limite de saída permite. Fechar a conexão sem criar publicação, assinatura, retained ou nova sessão. Preservar MQTT 3.1.1 e o comportamento dos demais tipos. Cabeçalhos reservados de outros tipos e a matriz normativa integral continuam fora do recorte.

Base: [OASIS MQTT 5.0 §2.1.2 e §4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html). A numeração de tipos reserva zero; o broker deve fechar ao receber pacote malformado, emitindo motivo quando cabível. Validar o motivo escolhido contra o texto normativo antes do aceite.

Aceite: unitários de codec para `0x00` e `0x0f` com corpo vazio e não vazio; regressão 3.1.1 e P201; fixture TCP real com DISCONNECT `0x81`, fechamento, Will/estado preservados e conexão normal posterior. Executar fmt, suíte, Clippy, build release, licenças, distribuição, CI da fonte exata. Registrar falhas e limites; sem tag/release isolada.
