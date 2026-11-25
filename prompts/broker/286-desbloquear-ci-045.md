# P286 v1.0 — Desbloquear o aceite do Broker 0.45.0

Entrada: P284 0a9838f. O DEB passou. No Windows, o job 45705127930
parou nos testes do mqtt-admin legado que exigem gravação atômica Unix.
Alinhar a seleção dos testes à plataforma que implementa a operação,
preservando todos no Ubuntu. Parear a CI com o Client corrigido por C160.
Aceite: testes Ubuntu e Windows, SCM, MSI, upgrade e rollback induzido.
Sem alteração de versão, estado persistente ou protocolo.
