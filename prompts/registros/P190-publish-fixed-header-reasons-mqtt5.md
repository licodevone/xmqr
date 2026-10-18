# P190 — motivos MQTT 5 para flags PUBLISH inválidas

- Prompt: [P190 v1](../broker/190-publish-fixed-header-reasons-mqtt5.md), commitado e enviado antes do código (`b16527a`).
- Entrada: `0634195` limpo, broker 0.33.0 e estado durável v15. Pedido vigente: concluir o plano XMQR com prompt, testes, registro, commit/push e checklist honesto.
- Ambiente: Ubuntu 26.04 no WSL; testes TCP em broker open-lab loopback com estado temporário. Serviço e estado instalados não foram alterados.
- Implementação: erros tipados `PublishQosReserved`/`PublishDupQosZero` no codec. Após CONNACK MQTT 5, QoS reservado 3 retorna DISCONNECT `0x81` e DUP com QoS 0 retorna `0x82`, antes de roteamento. PUBLISH válido permanece; MQTT 3.1.1 fecha sem resposta MQTT 5. Sem migração v15, mudança de versão ou tag isolada.
- Testes direcionados PASS: unitário de seis cabeçalhos inválidos e válidos em QoS 0/1/2; build debug Linux; `verify_mqtt5_publish_fixed_header_reasons.py` verifica motivos, Will, ausência de fanout/retained, PUBLISH válido e MQTT 3.1.1. Regressões P178 e P189 PASS.
- Gates locais PASS no Ubuntu 26.04/WSL: `cargo fmt --all -- --check`, `cargo test --locked` (biblioteca: 210 PASS, 6 ignored; demais targets PASS), `cargo clippy --locked --all-targets -- -D warnings`, inventário de licenças, 6 testes de distribuição e `cargo build --locked --release --bins -j 1` (2m21s). O build foi serial para reduzir pressão de memória observada no P189; não houve falha nesta execução.
- CI do commit exato e commit de implementação: pendentes; preencher com evidência real. Fase 6A global continua aberta.
