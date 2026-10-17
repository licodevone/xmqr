# P180 — User Property em SUBSCRIBE/UNSUBSCRIBE MQTT 5

[Prompt P180](../broker/180-subscription-user-properties-mqtt5.md) commitado antes da implementação. Fonte `7ff3ae2a8ab0e48299b0e638471c650d9ebcedc9` em `main`; [CI completa PASS](https://github.com/licodevone/xmqr/actions/runs/39028079979), incluindo pacote Ubuntu 26.04 e verificador TCP P180.

O broker aceita pares User Property `0x26` repetidos em SUBSCRIBE e UNSUBSCRIBE MQTT 5, combinados com Subscription Identifier no primeiro pacote. Limites: 16 pares, 2048 bytes codificados por contexto e 256 bytes UTF-8 por campo. Truncamento, UTF-8 inválido, excesso, propriedade de contexto errado e uso em MQTT 3.1.1 são recusados antes de alterar a assinatura. Os pares não mudam o roteamento nem o documento durável.

Gates locais PASS: `cargo fmt --check`, 201 testes Rust (6 ignorados preexistentes), Clippy `-D warnings`, build release, inventário de licenças, seis contratos de distribuição e integração TCP `P180_SUBSCRIPTION_USER_PROPERTIES_PASS`. Regressões P150/C87 e P148/C85 PASS. A integração cruzada C102 com o broker real também passou em MQTT 5 sub / MQTT 3.1.1 pub / UNSUBACK. Aceite limitado a esse recorte; matriz normativa MQTT 5, fases 6A/6D e releases futuras permanecem abertas. Sem tag isolada.
