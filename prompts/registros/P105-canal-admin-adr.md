# P105 — ADR do canal administrativo

- Prompt: [P105](../broker/105-canal-admin-adr.md).
- Decisão: [ADR 0001](../../docs/adr/0001-admin-channel.md), Unix domain
  socket privado, peer UID + tokens por papel, requests v1 limitados, ator
  como único writer, idempotência e auditoria desde a primeira mutação.
- Alternativas registradas: HTTPS remoto, MQTT reservado e SIGHUP existente.
- Escopo: decisão documental A04. Não existe ainda canal A09 implementado;
  A05/A07/aceite global da fase 5 continuam pendentes.
