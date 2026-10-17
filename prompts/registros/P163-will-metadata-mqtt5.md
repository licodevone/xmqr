# P163 — aceite parcial de Will metadata MQTT 5

Prompt `75b5f9f` precedeu a funcionalidade `a5862551cba454882a8410ec22b7ecf6dda34d06`. CI desse commit: [PASS](https://github.com/licodevone/xmqr/actions/runs/39019171756), incluindo Rust e pacote Ubuntu 26.04. Fmt, 191 testes de biblioteca aprovados/6 ignorados, demais alvos, Clippy, build release, inventário de licenças e 6 contratos de distribuição passaram localmente.

O CONNECT aceita PFI, Content Type, Response Topic, Correlation Data e User Property ordenada no Will, junto com Will Delay. Vetores de codec cobrem ordem arbitrária, duplicata escalar, PFI inválido, tópico inválido, truncamento, propriedade não suportada e quotas. Ensaio TCP real `scripts/verify_mqtt5_will_metadata.py` PASS com client C94, Will imediato, atrasado após restart, fila offline e retained, preservando bytes e ordem dos pares. `scripts/verify_mqtt5_will_delay.py` permanece PASS, inclusive Mosquitto. O documento durável segue v14 e admin independente 0.9.0 permanece compatível.

Message Expiry do Will não pertence a P163 e está em P164/C95; MQTT 5 integral, interop externa ampla e fases 6A/6B globais continuam abertas. Não há tag/release isolada. Broker publicado 0.28.0 não contém P163.
