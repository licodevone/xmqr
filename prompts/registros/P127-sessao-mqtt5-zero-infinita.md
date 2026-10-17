# P127 — sessão MQTT 5 com expiração zero/infinita

- Prompt P127 rev1 criado antes da implementação; base `main` pós-P126, versão publicada v0.17.0.
- Broker separa Clean Start da retenção após desconexão, aceita Session Expiry ausente/zero/infinita e responde Session Present real. O estado existente mantém formato v5 e a ACL continua vinculada ao principal.
- Codec: propriedades duplicadas/truncadas e intervalo finito recusados antes do registro; Will e demais propriedades fora do subconjunto continuam recusados.
- Validação local Ubuntu26/WSL: `cargo fmt --all -- --check`, `cargo test --locked`, `cargo clippy --locked --all-targets -- -D warnings` e `cargo build --locked` PASS. Testes de ator/codec e integração TCP real com reinício, duas publicações QoS1 offline (client XMQR e Mosquitto 2.0.22), retomada e limpeza por expiração zero PASS. Script: `scripts/verify_mqtt5_sessions.py`. Regressão cruzada `scripts/verify_mqtt5_cross.py` PASS.
- CI do commit: pendente. Intervalos finitos, Will Delay, expiração de mensagem, flow control e demais requisitos 6A–6D permanecem abertos. Sem versão/tag/release nesta fatia.
