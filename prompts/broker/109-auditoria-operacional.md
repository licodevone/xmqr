# P109 rev1 — consulta limitada da auditoria administrativa

2026-10-15. Entrada broker `9b4b9fe`/admin `3253c72`, documento MQTT v4,
recibos de reload, retained_delete e session_disconnect no mesmo commit.
A07 local aceito; A05/A09/B13/A08 e fase 5 global ainda abertos.

Adicionar `audit_list` somente para operator, com cursor por índice estável
da tabela append-only e limite 1..16. Retornar timestamp, request_id, UID,
operação, resultado, hash do alvo e gerações, sem token, payload, senha,
certificado nem tópico completo. Ator lê estado em memória; CLI independente
mostra JSON e cursor seguinte, sem abrir WAL. ID individual `receipt` continua.

Expor contadores operacionais de cardinalidade fixa para tentativas,
commits/replays/recusas administrativas e ocupação da tabela, no monitor
loopback existente. Recusa por quota é segura: manter recibos sem evicção;
documentar retenção bounded e necessidade de arquivamento/rotação antes do
esgotamento. Não limpar recibos online, pois isso permitiria replay.

Arquivos: router, admin_channel, monitoring, CLI, docs, testes, registros.
Negativos: viewer, cursor/limite inválido, resposta/página limitada, restart,
falha WAL e dados sensíveis ausentes. Gates Rust, integração com processos
isolados e revisão do monitor. A05 só será fechado se houver política de
retenção/rotação com idempotência preservada; inventário sozinho é parcial.
