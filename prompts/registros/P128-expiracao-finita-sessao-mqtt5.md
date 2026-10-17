# P128 — expiração finita de sessão MQTT 5

- Prompt P128 rev1 criado antes do código; base P127 `5f56065`, CI P127 posteriormente PASS.
- CONNECT aceita Session Expiry 1..4294967294 segundos. O ator grava deadline após desconexão, remove sessões vencidas em transição durável, verifica o prazo antes de cada comando e recupera documentos v1–v5 no formato v6. O broker preserva sessões infinitas e MQTT 3.1.1.
- Crash com conexão finita ainda ativa: o instante exato da queda não é durável; na recuperação a contagem começa naquele momento para evitar descarte silencioso. Para sessões já desconectadas, o prazo gravado permanece absoluto e é aplicado na recuperação. Rollback de um estado v6 exige backup privado anterior; binários v0.17.0 não leem v6.
- Validação local Ubuntu26/WSL: fmt, suíte completa, Clippy, build, teste de ator para retomada/vencimento, migração v1–v5, integração TCP de expiração finita e regressão cruzada MQTT5/3.1.1 PASS. Script `scripts/verify_mqtt5_sessions.py`. [CI do commit `564e373`](https://github.com/licodevone/xmqr/actions/runs/38989862684) PASS.
- Message Expiry, Will Delay, expiração alterada por DISCONNECT e demais itens 6B continuam pendentes; não declarar a fase concluída.
