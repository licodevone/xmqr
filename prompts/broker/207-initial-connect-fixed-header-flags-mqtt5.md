# P207 — flags reservadas no CONNECT inicial MQTT 5

Entrada: broker 0.37.0 publicado e fase 6A global aberta. O primeiro quadro com tipo CONNECT e bits baixos não zero (`0x11`–`0x1f`) é rejeitado genericamente, mesmo quando o corpo identifica MQTT 5 e permite uma resposta limitada. Este prompt precede qualquer mudança no codec.

Objetivo: classificar os 15 cabeçalhos como Malformed Packet e, quando o corpo contém prefixo MQTT 5 e bloco de propriedades íntegro, responder CONNACK `0x81`, respeitando o Maximum Packet Size anunciado. Sem prefixo MQTT 5 verificável, fechar sem presumir versão; MQTT 3.1.1 continua sem resposta nova. A validação deve acontecer antes de criar sessão, autenticar ou aplicar Will. Segundo CONNECT após CONNACK conserva o motivo P194 `0x82`, mesmo com flags inválidas.

Aceite: unitários para os 15 cabeçalhos com corpos completos/incompletos e limite de resposta; fixture TCP real para `0x11`/`0x1f`, ausência de sessão/Will, fechamento e conexão saudável posterior. Regressão MQTT 3.1.1/P194/P203–P205. Executar fmt, suíte, Clippy, build, licenças e contratos de distribuição, mais CI da fonte exata. Registrar limites e checklist sem encerrar fase 6A ou criar release isolada.

Referência normativa: [OASIS MQTT 5, §§2.1.3, 3.2.2.2 e 4.13](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html): flags reservadas inválidas são Malformed Packet; CONNACK de erro para CONNECT é permitido, seguido de fechamento.
