# P98 rev1 — B12: decisão de reload geral da configuração

2026-10-15. Entrada: P97/C48 B10 implementados e validados localmente;
`v0.12.0` publicada, 0.13.0 em preparação. Pedido do mantenedor: concluir a
fase 4, com prompt antes de cada funcionalidade.

Objetivo: registrar a fronteira operacional de reload sem sugerir que o TOML
geral já seja recarregável. Classificar cada campo entre atualização quente e
restart-only e estabelecer transação sem estado parcialmente publicado.

Escopo: ADR de configuração, plano/checklist e registro. Nenhuma mudança de
runtime nesta decisão. Preservar SIGHUP do bundle de segurança, contratos de
estado, QoS, quotas e modos seguros existentes. B11 definirá o mecanismo de
rotação TLS por operação separada, com validação completa antes da troca.

Aceite: classificação explícita de bind, perfil, TLS, auth, monitor e quotas;
condições de rollback e conexões ativas; documentação sem alegar reload geral.
Validação: conferir referências e diff; testes funcionais não são exigidos para
esta decisão documental. Implementação futura de reload geral terá prompt novo,
teste de concorrência/negativos e evidência antes de marcar como entregue.
