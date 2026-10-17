# P183 — identificador de propriedade inválido no CONNECT/Will MQTT 5

O [prompt P183](../broker/183-connect-property-context-reason-mqtt5.md) foi commitado antes da fonte (`812394f`). A fonte `54d62092145442d63b2f4f2f4f8afbcdea5adbcc` foi enviada a `main` e a [CI passou](https://github.com/licodevone/xmqr/actions/runs/39029954527) nos jobs Rust e pacote Ubuntu 26.04, incluindo o verificador TCP P183.

CONNECT e Will com identificador de propriedade fora do contexto recebem CONNACK MQTT 5 `0x81` antes de criar sessão ou agendar Will. O limite Maximum Packet Size é observado: cinco bytes permitem o CONNACK mínimo e quatro bytes levam a fechamento sem resposta. A validação separa este caso de AUTH (`0x86`/`0x8C`); truncamento, UTF-8 inválido e outros erros semânticos não foram classificados por P183.

Gate local PASS: 202 testes de biblioteca/6 ignorados, demais alvos, fmt, Clippy `-D warnings`, build release, inventário de licenças, seis contratos de distribuição, P183 TCP e regressões P180/P181/Will. Estado v15 sem migração. Sem tag isolada; matriz normativa e fase 6A abertas.
