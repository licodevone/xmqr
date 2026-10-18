# P230 — reconciliar plano da bridge após C139

Entrada: plano após P229; fonte client C139 `9b9bc8b`, prompt C139 publicado antes da implementação, ensaios locais XMQR↔XMQR e XMQR↔Mosquitto PASS. CI exata do client ainda em andamento.

Objetivo: após CI exata PASS, registrar C139 como fatia concluída da fase 8, com link de evidência, sem declarar T02/fase 8 fechada. Atualizar pendências para remover somente QoS 2 da origem MQTT 5, distinguindo a fonte nova da release client 0.41.0/bridge 0.3.0, que permanece sem C139. Manter transação entre brokers, propagação de propriedades, mapeamento múltiplo, ciclos externos e distribuição C139 como limites. Se a CI falhar, deixar item pendente e registrar a falha antes de corrigir.

Aceite: checklist e tabela Bridge coerentes, links para registro e CI, diff documental e push. Não criar tag/release de broker por alteração documental.
