# P131 — Session Expiry no DISCONNECT MQTT 5

- [Prompt P131](../broker/131-disconnect-session-expiry-mqtt5.md) criado antes do código. Base P130 `eac9cfa`, [CI](https://github.com/licodevone/xmqr/actions/runs/38991018736) PASS.
- DISCONNECT normal aceita Session Expiry Interval 0x11: zero encerra a sessão, prazo finito grava deadline e infinito a preserva. CONNECT com expiry zero não pode mudar para valor positivo. Propriedade duplicada/desconhecida/truncada e motivo fora do subconjunto são recusados.
- A mudança e o encerramento ocorrem em uma transição durável; falha do WAL deixa a sessão anterior intacta. Guarda de cancelamento continua encerrando sem override. O client independente ainda não expõe envio dessa propriedade; a integração usa frames MQTT 5 reais.
- Validação local Ubuntu26/WSL: codec, ator, injeção de falha no WAL, TCP real com reinício e negativo zero→positivo, fmt/Clippy/build PASS. Script `scripts/verify_mqtt5_disconnect_expiry.py`. [CI do commit `4bcb991`](https://github.com/licodevone/xmqr/actions/runs/38991391289) PASS.
- Will Delay foi entregue em P132; as demais partes da fase 6B seguem pendentes.
