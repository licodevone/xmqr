# Evolucao incremental autorizada

Base v0.5.0 confirmada local/remota em 2026-10-07, commit59c9e70.
Retained ja implementado; Last Will ainda rejeitado no codigo dessa tag.

| Versao alvo | Fatia | Dependencias |
| --- | --- | --- |
| 0.6.0 | Retained revisado, Last Will duravel | codec/ACL/ator/persistencia |
| 0.7.0 | metricas, health e readiness | observar estado de armazenamento |
| 0.8.0 | reload atomico de usuarios/ACL | revisao de sessoes e Will |
| 0.9.0 | backup/restore verificavel | documento versionado, parada segura |
| 0.10.0 | quotas/rate limits por identidade | policy reload e observabilidade |
| 0.11.0 | MQTT sobre WebSocket | limites/transporte/ACL existentes |

0.x.1, 0.x.2 etc corrigem defeitos; 0.6.54 e valido se houver 54 patches,
nao e salto automatico para uma funcionalidade. Cada marco requer prompt antes
de editar e gates reais; proximos marcos sao objetivos, nao recursos existentes.
Metadados locais podem evoluir; nenhuma tag/release sera criada/publicada neste
trabalho. MQTT5 e producao permanecem fora do escopo. MIT preservada.
