# P164 — Message Expiry do Will MQTT 5 aceito parcialmente

O [prompt P164](../broker/164-will-message-expiry-mqtt5.md) foi commitado antes da funcionalidade `ee9d41c18ca583e6c34962feab8ceb417a43d968`. [CI do commit: PASS](https://github.com/licodevone/xmqr/actions/runs/39019851179), inclusive pacote Ubuntu 26.04. Localmente, 192 testes de biblioteca passaram, 6 foram ignorados, demais alvos passaram, além de fmt, Clippy, build release, inventário de licenças e 6 contratos de distribuição.

O broker aceita a propriedade Will Message Expiry Interval `0x02` uma vez no CONNECT MQTT 5, inclusive zero, e recusa duplicata, truncamento e propriedades inválidas. O intervalo permanece no Will pendente do documento v15 e vira deadline absoluto somente quando o Will é efetivamente publicado. `scripts/verify_mqtt5_will_expiry.py` passou em TCP real com C95 para Will Delay maior que o intervalo, reinício, fila offline, retained e zero; regressões P163 e C70 passaram. A primeira gravação migra v14 para v15; broker 0.28.0 rejeita v15. A19 validou backup/verify/restore offline com o admin independente.

Não houve tag isolada: P164 integra a release 0.29.0. Conformidade MQTT 5 integral e fases 6A/6B globais permanecem abertas.
