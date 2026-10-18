# P191 v1 — prioridades após as fases 6–9

Estado de entrada: `main` limpo em `1264615`, broker 0.33.0 publicado e P183–P190 aceitos apenas na árvore. O mantenedor pediu seguir a prioridade recomendada e incluir ao final do plano capacidades observadas em outros brokers.

Objetivo: acrescentar ao final de `docs/evolution-plan.md` um backlog ordenado depois das fases 6–9: (1) limites por dispositivo/usuário e diagnóstico operacional, (2) regras de integração e validação de dados, (3) cluster nativo. Distinguir o que o Mosquitto já oferece (bridge, WebSocket, plugins, segurança dinâmica) de diferenças como cluster unificado e mecanismos de regras/validação de EMQX e HiveMQ.

Escopo: documentação do plano e registro P191. Não alterar código, pacote, versão, cronograma já aceito nem marcar fase como concluída. Os itens futuros devem ter critérios verificáveis, dependências e riscos; não prometer compatibilidade, escala ou disponibilidade ainda não testadas.

Fontes: [Mosquitto configuração](https://mosquitto.org/man/mosquitto-conf-5.html), [segurança dinâmica](https://mosquitto.org/documentation/dynamic-security/), [EMQX cluster](https://docs.emqx.com/en/emqx/latest/develop/cluster/introduction.html), [regras](https://docs.emqx.com/en/emqx/latest/develop/data-integration/rules.html), [observabilidade](https://docs.emqx.com/en/emqx/latest/guides/observability/overview.html) e [HiveMQ Data Hub](https://docs.hivemq.com/hivemq/latest/data-hub/validation.html). Fontes oficiais consultadas em 2026-10-18; ofertas e licenças podem mudar.

Aceite: seção final com checklist desmarcado, sequência de implementação e critérios de teste honestos; links diretos verificáveis, `git diff --check` e revisão de coerência com as fases 6–9. Sem testes funcionais, tag ou release para esta mudança textual. Fazer commit/push após revisão.
