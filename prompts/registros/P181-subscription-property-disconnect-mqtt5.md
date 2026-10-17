# P181 — DISCONNECT para propriedade inválida de assinatura MQTT 5

O [prompt P181](../broker/181-subscription-property-disconnect-mqtt5.md) foi commitado antes do código (`1384c80`). Fonte exata `8fcf66ff09f277e7db1697ca722d787d93dec37b` em `main`; [CI PASS](https://github.com/licodevone/xmqr/actions/runs/39028972267) nos jobs Rust e pacote Ubuntu 26.04, incluindo verificador TCP P181.

Após CONNACK MQTT 5, SUBSCRIBE/UNSUBSCRIBE com identificador de propriedade impróprio recebe DISCONNECT `0x81` (Malformed Packet, OASIS §2.2.2); SUBSCRIBE com Subscription Identifier duplicado recebe `0x82` (Protocol Error, §3.8.2.1.2). O broker fecha a conexão, sem SUBACK/UNSUBACK ou alteração de assinatura. O Will aplicável é publicado. A comparação MQTT 3.1.1 apenas fecha. Não se generaliza essa classificação para truncamento, UTF-8, quotas, I/O ou timeout.

Gates locais PASS: 202 testes de biblioteca/6 ignorados, demais alvos, fmt, Clippy `-D warnings`, build release, inventário de licenças, seis contratos de distribuição, regressões TCP P175–P180 e `P181_SUBSCRIPTION_PROPERTY_DISCONNECT_PASS`. O teste P180 confirmou assinatura durável inalterada após recusa e reconexão. Estado v15 sem migração. Sem tag isolada; fase 6A e matriz normativa completa ainda abertas.
