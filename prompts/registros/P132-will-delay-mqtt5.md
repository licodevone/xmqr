# P132 — Will Delay Interval MQTT 5

- [Prompt P132](../broker/132-will-delay-mqtt5.md) criado antes do código; base P131 `4bcb991` com [CI PASS](https://github.com/licodevone/xmqr/actions/runs/38991391289).
- CONNECT MQTT 5 aceita Will e Will Delay opcional; propriedades duplicadas, truncadas ou fora do subconjunto são recusadas. O Will é agendado no estado durável após desconexão anormal e publicado quando o atraso ou a sessão vencer, o que ocorrer primeiro.
- Reconexão Clean Start=0 antes do prazo cancela o Will; Clean Start=1 publica o Will anterior. DISCONNECT normal cancela. Shutdown, reload de segurança e recuperação preservam ou iniciam o prazo. Documento v8 lê v1–v7; versões anteriores não reabrem v8 sem backup anterior.
- Testes locais Ubuntu26/WSL: codec, ator, falha de WAL e migração v7→v8; `scripts/verify_mqtt5_will_delay.py` com restart, crash, client C70 e Mosquitto; regressões MQTT 5 anteriores; fmt/test/Clippy/build/licenças PASS. [CI do código `e5ab738`](https://github.com/licodevone/xmqr/actions/runs/38992064864) PASS. Correção posterior de falha de WAL aguardará a CI do respectivo commit.
- C70: [registro do client](../../../xmqr-client/prompts/registros/C70-will-delay-mqtt5.md) e [CI PASS](https://github.com/licodevone/xmqr-client/actions/runs/38991792436).
- Fase 6B permanece aberta até a retomada durável do QoS do próprio client e a revisão do contrato completo.
