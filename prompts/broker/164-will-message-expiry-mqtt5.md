# P164 rev1 — Message Expiry Interval no Will MQTT 5

Entrada: P163/C94 preservam metadados selecionados do Will no estado v14, mas rejeitam a propriedade Will `0x02`. Este prompt precede o código.

Objetivo: aceitar Message Expiry Interval `0x02` no Will Properties exatamente uma vez, com valor `u32` e combinação com Will Delay. Persistir o *intervalo* no Will pendente; iniciar o deadline absoluto somente quando o Will é efetivamente publicado, inclusive após delay, expiração de sessão, encerramento administrativo e recuperação de crash. O deadline resultante passa pelo mesmo contrato de PUBLISH/retained/offline/ACK do P130. Intervalo zero não gera entrega ou retained. Conservar MQTT 3.1.1 e Wills sem a propriedade.

Estado: documento v15 com campo opcional/default no Will pendente, leitura migratória v1–v14 e recusa explícita por versões antigas após gravação. Admin independente deve atualizar o pin e comprovar compatibilidade antes da release. Não computar deadline no CONNECT ou na perda de conexão; não alterar `expiry_at_unix_ms` de Wills legados.

Aceite: codec válido/duplicado/truncado, tempo controlado de delay versus expiry, retained/offline/restart/crash e cancelamento; client C95 e Mosquitto quando suportado, compatibilidade 3.1.1, migração/restauração, fmt/Rust/Clippy/release/licenças/distribuição/CI do commit exato. Registrar 6B parcial e preparar marco de release só após admin compatível.

Fonte: [MQTT 5 §3.1.3.2.4 e §3.3.2.3.3](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html).
