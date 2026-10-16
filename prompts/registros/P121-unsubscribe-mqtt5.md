# P121 — UNSUBSCRIBE/UNSUBACK MQTT 5

- Prompt [P121 rev1–2](../broker/121-unsubscribe-mqtt5.md) criado antes da funcionalidade. Entrada `f74741d`, versão 0.16.0 preservada.
- Codec lê Property Length zero no UNSUBSCRIBE 5 e rejeita propriedades não suportadas; UNSUBACK 5 contém razão por filtro. Roteador preserva ordem, distingue removido `0x00` e inexistente `0x11`, evita commit sem alteração e confirma remoção só após commit. MQTT 3.1.1 mantém wire anterior.
- Ubuntu26/WSL: vetores positivos/negativos e teste wire de SUBSCRIBE→UNSUBSCRIBE→UNSUBACK→PUBLISH sem nova entrega PASS. `cargo fmt --all -- --check`, `cargo test --locked`, `cargo clippy --locked --all-targets -- -D warnings`, `cargo build --locked --bins` PASS. Primeiro vetor FAIL por bloqueio inicial de `0xa2` na lista MQTT 5; rev2 corrigiu e repetiu.
- Integração real com client C62 via `scripts/verify_mqtt5_acl_reason.py` PASS, incluindo assinatura, entrega, UNSUBACK e encerramento.
- [CI do commit funcional `4f55f97`](https://github.com/licodevone/xmqr/actions/runs/38972742149) PASS, inclusive Rust/interop e pacote Ubuntu26. Sem tag/release isolada; fase 6A permanece aberta.
