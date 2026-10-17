# P150 — Subscription Identifier MQTT 5 no broker

- [Prompt P150](../broker/150-subscription-identifier-mqtt5.md) criado e commitado antes da funcionalidade. Fonte base: broker `v0.24.0`/estado v11.
- Codec decodifica um ID 1..268435455 no SUBSCRIBE, recusa zero/duplicata e propriedade 0x0B em PUBLISH de entrada. Roteador associa ID por filtro aceito, remove em unsubscribe/revogação, inclui todos os IDs das assinaturas elegíveis no PUBLISH; retained, fila offline e retransmissões mantêm IDs. Documento durável v12 lê v1..v11; admin 0.6.0 ainda não lê v12.
- TCP descartável [P150/C87](../../scripts/verify_mqtt5_subscription_identifier.py) PASS: QoS0/1/2, filtros sobrepostos com `[17,17]`, substituição sem ID e nova assinatura, unsubscribe, restart, offline, retained, client C87 JSONL, propriedades malformadas. Regressões P148 e P147 PASS. 171 testes de biblioteca passaram (6 ignorados), demais alvos passaram; fmt, Clippy, build release, inventário de licenças e seis contratos de distribuição PASS.
- Commit exato, CI e aceite de P150: pendentes. Sem release da fonte de desenvolvimento; rollback de v12 exige backup privado v11 anterior.
