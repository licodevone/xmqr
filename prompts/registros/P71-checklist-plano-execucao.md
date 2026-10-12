# P71 — checklist do plano de execução

Data: 2026-10-12, Windows/PowerShell. Prompt:
[P71 rev1](../broker/71-checklist-plano-execucao.md), criado antes da edição.

Pedido autorizado: marcar entregas concluídas no plano com checklist e riscado.
Entrada: broker HEAD f231226 (0.11.2), client 0.7.1; trabalho local preexistente
preservado. Arquivo alterado: docs/evolution-plan.md.

Checklist: 9 itens concluídos com caixa marcada e texto riscado, 20 pendentes.
Fase 1 aceita conforme P61/C39; fase 2 parcial conforme baseline P62.
Entregas operacionais P63/P64/C40 identificadas sem encerrar a fase 5.
Resumo de versões, tabela e próxima entrega atualizados; histórico preservado
com aviso explícito. Orientação incluída para atualizar marcações após aceite.

Validação real:

- PASS: git diff --check, saída 0.
- PASS: todos os links locais do plano resolvidos pelo filesystem.
- PASS: contagem e inspeção do diff; itens marcados usam riscado Markdown.
- NOT_RUN: testes funcionais e consulta de publicação remota, desnecessários
  para esta mudança documental. Evidências de execução são as dos registros
  anteriores; esta tarefa não executou novamente os testes desses marcos.

Compatibilidade/migração: sem alteração de runtime, estado, versões ou pacotes.
Sem commit, push ou release nesta tarefa. Próxima entrega continua sendo
ampliar capacidade/QoS/fan-out/TLS sob prompt próprio.
