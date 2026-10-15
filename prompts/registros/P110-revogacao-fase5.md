# P110 — prova cruzada A02/A03

- Prompt: [P110 rev1](../broker/110-revogacao-fase5.md).
- Ambiente: Ubuntu 26.04/WSL, broker/admin em processos isolados e arquivos privados temporários; nenhuma instância do operador.
- A02: CLI admin criou role `sender`, group `devices`, vinculou usuário e removeu ACL direta; reload online aplicou bundle. Cliente MQTT real publicou retained em tópico autorizado por grupo; publicação em tópico não concedido não apareceu no estado.
- A03: cliente persistente deixou PUBLISH QoS2 após PUBREC e Will configurado. CLI desabilitou o usuário e aplicou reload com geração/hash/ID. Conexão fechou; nova autenticação foi recusada antes e depois do restart. Sessão continuou com inbound QoS2=1; recibo de reload permaneceu `committed`.
- Gates: `python3 scripts/verify_channel_cli.py --broker ../xmqr/target/debug/mqtt-broker --admin target/release/xmqr-admin` retornou `CHANNEL_CLI_PASS`. Gates Rust, Clippy e licença dos incrementos P108/A08 anteriores PASS. Fixture contém credencial pública de teste e não foi gravada em log/repo de estado.
- Aceite: A02/A03 no recorte dinâmico local acl-lab PASS. Não equivale a nova campanha mTLS/ESP32 ou homologação de produção. A05/A08/A09/B13 e fase 5 global permanecem abertos.
