# Fase 6 de MQTT 5

Estado em 18 de outubro de 2026: **em validação, não concluída**.
O fechamento P227 confronta as entregas incrementais com os critérios
M01–M10 do [plano de paridade](plano-paridade-mosquitto.md).

| Parte | Critério de saída | Estado |
| --- | --- | --- |
| 6A | Contextos/propriedades, códigos de erro, limites, coexistência3.1.1 e duas implementações externas | Auditoria em andamento |
| 6B | Migração, expiração, Will Delay, takeover/restart/crash sem perda silenciosa | Auditoria em andamento |
| 6C | Negociação bilateral, backlog, QoS0/1/2, aliases/reset e propriedades duráveis | Auditoria em andamento |
| 6D | Opções/IDs de assinatura, shared/failure/fairness e decisão dos mecanismos AUTH | Auditoria em andamento |

Broker0.42.0, client0.36.0 e admin0.10.0 são os marcos publicados de entrada.
Uma funcionalidade implementada com testes parciais não representa aceite
global. Resultados desta campanha serão registrados com fonte e hashes, sem
promover testes históricos nem declarar produção ou MQTT5 integral.
