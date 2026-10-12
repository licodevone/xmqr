# P71 rev1 — checklist do plano de execução

Data: 2026-10-12. Pedido: marcar visualmente entregas concluídas no plano.

Entrada: broker HEAD f231226, versão 0.11.2; client 0.7.1. Alterações locais
preexistentes no README, geradores do curso e arquivos não rastreados preservadas.

Objetivo: acompanhar o plano com caixas Markdown e texto riscado, diferenciando
entregas aceitas, fases parciais e pendências.

Escopo: docs/evolution-plan.md e prompts/registros/P71-checklist-plano-execucao.md.
Sem alterações funcionais, versões, instalação, commit, publicação ou migração.

Requisitos: marcar apenas entregas com evidências locais; fase 1 concluída em
P61/C39, fase 2 parcial em P62. Preservar checkpoints históricos identificando-os
como histórico. Atualizar o resumo e a próxima execução para o estado comprovado.
Incluir orientação para manter as marcações após cada aceite futuro.

Aceite: checklist por fase, itens concluídos com `- [x] ~~texto~~`, pendentes com
`- [ ] texto`, links para evidências e ausência de fase parcial marcada concluída.

Validação: conferir registros P61/C39/P62/P63/P64/C40, links locais, marcações e
git diff --check. Não executar testes funcionais para esta mudança documental.
