# Fase 2 — aceite separado por componente

Atualizado2026-10-13, P80/C43. Broker/admin0.11.4 candidato,
clientruntime0.8.1. **Software validado; fase2 global PARTIAL/BLOCKED por E01.**
Não avançar fase3 ou riscar ESP32 sem evidência física.

| Responsável | Entrega | Estado |
| --- | --- | --- |
| Broker | P62baseline e P72QoS/fan-out/mTLS | PASS histórico |
| Broker | Admissão1/8/32/64, N+1 e vaga reutilizada | PASS P80,24cenários |
| Broker | Handshake silencioso e liberação | PASS P80,6cenários |
| Broker | FilaN/N+1 QoS1/2, restart/drain, outros peers | PASS P80,24cenários |
| Broker | Não leitorQoS0 TCP/mTLS e vaga reutilizada | PASS P80,6cenários |
| Broker | ShutdownTLS limitado e regressões de ator/transporte | PASS,111testesRust e fmt/Clippy/build/inventário |
| Broker | Avaliação de quotas por identidade | Decisão ADR0006; isolamento multitenant não implementado |
| Client/broker | Mosquitto2.0.22 externo mTLS/bytes/QoS/retained/Will/sessão/negativos | PASS C43,59cenários |
| Client | Regressões de runtime | PASS54testesRust; sem mudança de CLI/versão |
| Todos/software | Método, RAM/CPU/p50/p95/p99, limitações | P80 e JSON sanitizado |
| ESP32 DevKitV1 | Wi-Fi/SNTP/mTLS/pubsub/reconexão em placa | BLOCKED: porta inacessível; NOT_RUN físico |

[CapacidadeP80](performance-pressure.md) · [Dados](results/p80-pressure-2026-10-13.json) ·
[ADR](architecture/adr-0006-identity-quotas.md) · [ChecklistE01](esp32-phase2-checklist.md) ·
[ClientC43](https://github.com/licodevone/xmqr-client/blob/main/docs/phase2-acceptance.md).

Os relatórios versionados foram gerados antes do commit, com HEAD de entrada,
hashes do harness/binários e imagesIDs. Não são prova de commit futuro.
Artefatos de correção0.11.4 exigem clone limpo, repetição dos gates pertinentes,
.debUbuntu26amd64/lifecycle e imagens broker/adminBookwormamd64, checksums,
tag e digests nos anexos. Este registro anterior ao commit não alega publicação.

SomenteE01real + software aceito permitem ACCEPTEDfase2. Uma release de correção
pode ser aceita antes da placa, sem representar encerramento da fase ou produção.
