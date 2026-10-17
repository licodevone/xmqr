# P172 rev2 — DISCONNECT MQTT 5 com Will solicitado

Entrada: P171 valida as confirmações QoS2; DISCONNECT MQTT 5 ainda aceita apenas `0x00` e Session Expiry isolada. A [norma OASIS](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html), seções 3.14.2 e 3.14.4, define `0x04` como Disconnect with Will Message do client. Prompt commitado antes do código.

Objetivo: aceitar `0x04` com Session Expiry Interval opcional, Reason String única e User Property repetida, sem estender sessão originalmente zero. Na limpeza durável, usar a transição existente de Will (delay, ACL, expiry e restart) em vez do cancelamento de DISCONNECT normal. Aceitar `0x00` com as mesmas propriedades diagnósticas. Recusar códigos/propriedades fora do recorte, duplicatas, truncamento e extensões MQTT 3.1.1. Não registrar textos arbitrários nem alterar estado/versão.

Aceite: vetores de codec, TCP real com Will `0x04`, DISCONNECT `0x00` que cancela Will, sessão/restart e negativos; regressões de Will Delay, Session Expiry e MQTT 3.1.1; fmt, Rust, Clippy, build release, licença, distribuição e CI. Atualizar checklist parcial e registro; sem tag isolada. Outros DISCONNECT reason codes e aceites globais abertos.

Revisão 2: o TCP focal passou, mas a primeira execução da bateria completa parou em `cargo fmt --check` por quebra de linha do novo erro de propriedade. Corrigir a formatação e repetir a bateria integral antes de aceitar.
