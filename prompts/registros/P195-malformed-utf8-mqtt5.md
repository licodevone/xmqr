# P195 — UTF-8 malformado após CONNACK MQTT 5

- [Prompt P195](../broker/195-malformed-utf8-mqtt5.md) commitado e enviado antes do código (`275735e`); revisão 2 da falha de compilação `d7c3558`. Entrada limpa em `6a55edc`, broker/admin legado 0.34.0 e estado v15.
- Implementação na árvore: `Cursor::text` retorna erro tipado `MalformedUtf8` para codificação inválida e escalares já recusados; os parsers propagam o tipo. Após CONNACK MQTT 5 o broker tenta DISCONNECT `0x81` dentro do limite de saída, fecha e preserva o fluxo de Will. Truncamento, tópico/ACL e erros anteriores ao CONNACK não foram reclassificados.
- Primeira compilação do teste direcionado FAIL com `E0308`: dois retornos de limites locais em `parse_subscription_user_property` continuavam `&'static str` após a mudança para erro boxed. Corrigidos com `.into()` sem alterar limites; testes não iniciaram na primeira tentativa.
- Repetição direcionada PASS no Ubuntu 26.04/WSL: unitário por contexto (PUBLISH, SUBSCRIBE, UNSUBSCRIBE, AUTH, DISCONNECT e ACKs), UTF-8 inválido/NUL versus truncamento; build debug; script TCP `P195_UTF8_PASS` com motivo, fechamento, Will, ausência de fanout/retained, PUBLISH válido e MQTT 3.1.1.
- Gates completos, regressões, CI do commit exato e checklist: pendentes. Fase 6A global aberta; sem migração, tag ou release isolada.
