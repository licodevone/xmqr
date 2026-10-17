# P130 — Message Expiry Interval MQTT 5

- [Prompt P130](../broker/130-message-expiry-mqtt5.md) criado antes do código. Base P129 `b895942`, release broker0.18.0 intacta.
- `PUBLISH` MQTT 5 aceita exclusivamente a propriedade Message Expiry (0x02) neste recorte; duplicata, truncamento e propriedades restantes são recusados. Deadlines absolutos no documento durável v7 preservam cópias retidas e offline durante reinício. O ator remove cópias vencidas antes de novos comandos e no tick; mensagens já iniciadas em QoS mantêm handshake. QoS2 aplica o prazo no PUBREL.
- Saída MQTT 5 inclui prazo restante; saída MQTT 3.1.1 mantém wire anterior. Valor 0 expira imediatamente e substitui eventual retained anterior. Migração de v1–v6 coberta. Rollback de estado v7 a broker0.18.0 exige backup privado v6 anterior.
- Validação local Ubuntu26/WSL: fmt, suíte completa, Clippy, build, vetores de codec, expiração retida/offline após reinício, integração TCP real client C69/Mosquitto QoS2, regressões de Session Expiry e interop 3.1.1 PASS. Script `scripts/verify_mqtt5_message_expiry.py`. [CI do commit `eac9cfa`](https://github.com/licodevone/xmqr/actions/runs/38991018736) PASS.
- Will Delay, DISCONNECT Session Expiry, outras propriedades PUBLISH e fases 6A/6C/6D continuam pendentes.
