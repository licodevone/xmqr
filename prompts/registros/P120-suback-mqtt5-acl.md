# P120 — SUBACK MQTT 5 com motivo de ACL

- Prompt [P120 rev1–2](../broker/120-suback-mqtt5-acl.md) criado antes da funcionalidade; entrada `99d8a18`, versão preservada em 0.16.0.
- Broker: traduz recusa ACL interna `0x80` para SUBACK MQTT 5 `0x87` por filtro; MQTT 3.1.1 continua `0x80`. Assinatura totalmente recusada não faz commit. ACL, limites, estado persistido e publicação permitida preservados.
- Ubuntu26/WSL: teste wire de recusa SUBACK MQTT 5/3.1.1, ausência de commit, PUBACK e publicação subsequente PASS. `cargo fmt --all -- --check`, `cargo clippy --locked --all-targets -- -D warnings`, `cargo build --locked --bins` PASS. `cargo test --locked` teve uma primeira execução FAIL em `persistence::tests::actor_acks_after_commit` (`AlreadyOpen`); teste isolado e repetição completa PASS. Causa intermitente ainda aberta conforme P118.
- Integração real `xmqr-client/scripts/verify_mqtt5_acl_reason.py` PASS: PUBACK/SUBACK negados `0x87`, CONNACK por senha incorreta `0x86`, publicação autorizada.
- CI remoto: pendente até o push. Sem tag/release isolada nesta fatia; a fase 6A continua aberta.
