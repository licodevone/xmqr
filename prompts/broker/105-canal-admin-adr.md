# P105 rev1 — contrato do canal administrativo da fase 5

2026-10-15. Entrada broker `5c81c37`, release0.14.0; único writer de estado
é o ator. Reload SIGHUP existe, mas não tem identidade de operação, RBAC,
idempotência nem resposta estruturada. Admin independente 0.2.0 valida bundle
offline. Matriz A04 exige ADR antes de A09; A09 continua pendente.

Decidir um transporte administrativo local que possa aplicar candidato de
bundle e depois gerir sessões/retained, sem segundo writer de WAL. Documentar
autenticação, autorização, limites/admissão, semântica de resultados incertos,
idempotência, concorrência, auditoria, recuperação e plano de testes. Comparar
Unix socket, HTTPS e MQTT reservado para o escopo Linux/WSL. Não implementar
endpoint neste prompt, não publicar versão e não marcar A09/A05/A07 aceitos.

Aceite: ADR com decisão explícita, alternativas/riscos, contrato de request
v1 e condições de segurança verificáveis; matriz A04 pode passar a decisão,
mas fase 5 permanece aberta até integração online real.
