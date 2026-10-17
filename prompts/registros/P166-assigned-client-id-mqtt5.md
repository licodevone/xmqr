# P166 — Client Identifier atribuído no MQTT 5 aceito parcialmente

O [prompt P166](../broker/166-assigned-client-id-mqtt5.md) foi commitado antes da funcionalidade (`e79818d`). Fonte exata `a9c8e67ce10bff1e725d97481494b7a34e8138e6`: 196 testes de biblioteca PASS/6 ignorados, demais alvos, fmt, Clippy, build release, inventário de licenças e 6 contratos de distribuição PASS localmente; [CI PASS](https://github.com/licodevone/xmqr/actions/runs/39021849361), incluindo pacote Ubuntu 26.04.

O CONNECT MQTT 5 com Client Identifier vazio recebe um ID aleatório exclusivo de 37 bytes (`xmqr-` mais 32 caracteres hexadecimais). O ator reserva o ID sem tomar uma sessão existente e o CONNACK inclui a propriedade obrigatória `0x12`. O broker recusa antes do commit quando Maximum Packet Size não comporta os 47 bytes do CONNACK, ou quando a autenticação falha. MQTT 3.1.1 mantém a recusa de ID vazio. O ensaio `scripts/verify_mqtt5_assigned_client_id.py` com C97 passou com dois IDs simultâneos distintos, pub/sub real e retomada de sessão durável.

Sem tag/release isolada. A fase 6A global e interop externa ampliada continuam abertas.
