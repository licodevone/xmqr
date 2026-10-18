# Fase 6 de MQTT 5

Estado em 18 de outubro de 2026: **em validação, não concluída**.
O fechamento P227 confronta as entregas incrementais com os critérios
M01–M10 do [plano de paridade](plano-paridade-mosquitto.md).

| Parte | Critério de saída | Estado |
| --- | --- | --- |
| 6A | Contextos/propriedades, códigos de erro, limites, coexistência3.1.1 e duas implementações externas | Matriz pronta;32fixturesPASS no candidatoD; repetir no conjunto final |
| 6B | Migração, expiração, Will Delay, takeover/restart/crash sem perda silenciosa | C129 corrigido; clock/estado16 e compatibilidadeadmin ainda em validação |
| 6C | Negociação bilateral, backlog, QoS0/1/2, aliases/reset e propriedades duráveis | Controle comquota0 e PahoaliasesPASS noD; vetores históricos atualizados; aceite final pendente |
| 6D | Opções/IDs de assinatura, shared/failure/fairness e decisão dos mecanismos AUTH | Fairness/Will3PASS, PahoAUTHinicialPASS, decisãoPLAIN explícita; repetir integração final |

Broker0.42.0, client0.36.0 e admin0.10.0 são os marcos publicados de entrada.
Uma funcionalidade implementada com testes parciais não representa aceite
global. Resultados desta campanha serão registrados com fonte e hashes, sem
promover testes históricos nem declarar produção ou MQTT5 integral.

Evidências atuais e FAILs preservados no [registroP227](../prompts/registros/P227-fechamento-integrado-fase6.md).
A [matriz por contexto](conformance/mqtt5-property-matrix.md) identifica
propriedades/limites/testes; a [decisãoAUTH](architecture/adr-0007-mqtt5-auth-scope.md)
não promete mecanismos ausentes. C129 final tem181testesRust/21TCP/6compat e
migração real de draftv1, sem garantia de transação entre stdout e aplicação.

O candidatoP227E introduz estado16 e requer pin/admin compatível. Não publicar
esse conjunto como concluído usando o admin010/v15 ou apenas os testesD.
ClientC1310.38.0 foi [publicado](https://github.com/licodevone/xmqr-client/releases/tag/v0.38.0)
da fontefca6fc82117b7ee2b770dc2e4ce673b53764b211 após CI39138244703PASS,
ciclo de pacote e seis anexos remotos conferidos. DockerHub numerado:
lepinheiro100/xmqr-client:0.38.0, digest
`sha256:b025a82ab4172f82223e8b01b125570996f374a27ee524a04cc62eac81a148f9`.
Broker16/admin compatível ainda não têm marco final aceito por este documento;
a distribuição independente do client não encerra o conjunto6A–6D.
