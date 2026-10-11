# P53 rev1 — inventário e cronograma

Entrada: main 7da894a, árvore limpa, P52 implementado e não lançado.
Objetivo: organizar lacunas do broker e sequência estimada até MQTT5.
Escopo: docs/ROADMAP.md, docs/evolution-plan.md, README.md e registro P53.
Sem código, mudança de versão, instalação ou release. Preservar histórico.
Aceite: distinguir implementado, não lançado, ausente e validação pendente;
cronograma relativo com dependências, critérios de saída e folga, sem promessa
de capacidade, conformidade ou prazo. Prompts individuais antes de cada feature,
revisões antes de correções. MQTT5 dividido em entregas com regressão3.1.1.
Validação: fontes oficiais Mosquitto/OASIS, evidências locais, links e diff check.
Commit/push autorizados pela conversa. Tags/releases não cabem em planejamento.

## rev2 — direcionamento do usuário

Usar Mosquitto como referência de paridade funcional e incluir dependências
entre broker e client. Planejar trabalho dos dois, preservando repositórios e
versões independentes; não implementar recursos nem editar o client nesta etapa.
