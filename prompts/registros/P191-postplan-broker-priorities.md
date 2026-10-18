# P191 — prioridades adicionais do plano

- [Prompt P191](../broker/191-postplan-broker-priorities.md) commitado e enviado antes da edição (`5009089`). Entrada limpa em `1264615`.
- Foi acrescentada ao final de `docs/evolution-plan.md` a sequência 10–12: limites por identidade e diagnóstico, regras/integrações e, depois, cluster nativo. Cada item permanece `[ ]`, com dependências e critérios de validação. Fases 6–9 não foram marcadas como concluídas.
- Fontes oficiais consultadas em 2026-10-18: Mosquitto (configuração e segurança dinâmica), EMQX (cluster, regras e observabilidade) e HiveMQ (validação por esquema), vinculadas diretamente no plano. Foi explicitado que Mosquitto já oferece bridge, WebSocket, plugins e segurança dinâmica, e que funções de terceiros podem depender de licença.
- Verificação: `git diff --check` e revisão manual de escopo/links PASS. Mudança apenas documental; testes funcionais NOT_APPLICABLE. Nenhuma tag/release criada para P191.
