# P134 — Receive Maximum MQTT 5

- [Prompt P134](../broker/134-receive-maximum-mqtt5.md) criado antes da implementação. Base `6417e1b`, broker 0.19.0; o trabalho não altera a versão nem o formato durável v8.
- O parser CONNECT preserva Receive Maximum `0x21`, assume 65535 quando ausente e recusa zero, duplicata e comprimento inválido. A quota por conexão limita PUBLISH QoS1/2 de assinaturas vivas, retained, fila offline e replay; ACK final libera vaga. QoS0 e PUBREL seguem livres. Um novo CONNECT pode reduzir a quota sem alterar o estado durável.
- O limite global de inflight continua aplicável. Não há ampliação de quota do broker nem alteração do comportamento MQTT 3.1.1.
- Ubuntu 26.04/WSL: `cargo fmt --all --check`, `cargo test --locked --quiet`, `cargo clippy --locked --all-targets -- -D warnings`, `cargo build --locked --release --quiet` PASS; `python3 scripts/verify_mqtt5_receive_maximum.py` PASS com broker TCP real, cliente C72, Mosquitto 2.0.22, QoS0 e replay após restart. Teste de retained acrescentado para a mesma quota.
- Commit `0e563cc` publicado; [CI de `main` PASS](https://github.com/licodevone/xmqr/actions/runs/38995053140). [CI C72 PASS](https://github.com/licodevone/xmqr-client/actions/runs/38995048475). P134/C72 aceitos no recorte descrito. Fase 6C continua aberta para Maximum Packet Size, Topic Alias e demais propriedades.
