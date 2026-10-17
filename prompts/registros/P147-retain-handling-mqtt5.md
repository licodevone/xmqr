# P147 — Retain Handling MQTT 5 no broker

- [Prompt P147](../broker/147-retain-handling-mqtt5.md) criado antes do código. Fase 6D global aberta.
- Implementação: opções 0/1/2 por filtro no SUBSCRIBE MQTT 5. Modo 1 compara a assinatura com o estado da sessão antes de atualizá-la; modo 2 não envia retained no SUBSCRIBE. ACL, deduplicação e QoS preservados. Codec rejeita valor 3, No Local/Retain As Published e bits reservados; MQTT 3.1.1 inalterado. Documento durável v10 sem migração.
- Gates locais: 167 testes principais PASS/6 ignorados, demais testes Rust PASS, fmt, Clippy `-D warnings`, build release e licenças PASS. [TCP real P147/C84](../../scripts/verify_mqtt5_retain_handling.py) PASS com modos 0/1/2, sessão persistente/restart, client XMQR e Mosquitto 2.0.22 descartável (`sha256:199ea8ef2e35ec2b1b37e59cfd1dbae538ed4dfa4a2251a121a52215a6248a21`). Regressões P144/P146 e C80/C83 PASS. Sem ensaio ESP32.
- Fonte, CI e aceite pendentes; sem release isolada nem aceite global da fase 6D.
