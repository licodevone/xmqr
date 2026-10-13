# P88 v1.1 — referência ao terceiro projeto administrativo

Preparado2026-10-13 antes de editar documentos. Pedido atual autoriza criar
xmqr-admin no GitHub e seguir prompts, implementação, testes, commit/push,
tags de código e releases quando apropriado; agentes paralelos autorizados.
Entrada: brokerHEADc678f8dbc680c88c6c1e0514b22d470abb0de858/runtime0.11.5,
clientHEADd9d97d51b88832044c8d2de3786ce4262ee77ec1/runtime0.8.1 preservados.
Admin independente0.1.0 em aceite A01/A02/A03; publicação deve ser confirmada
antes de anunciar URL/release/digest concluídos, nunca presumida.

Escopo documental após aceite: README, docs/evolution-plan.md,
docs/plano-paridade-mosquitto.md, VERSIONING e prompts/registros/P88-admin.md.
Acrescentar xmqr-admin como terceiro projeto, CLI compatível e painel local
autenticado de leitura. mqtt-admin legado permanece no broker e no seu deb/
imagem0.11.5. Nova imagem xmqr-admin-ui0.1.0 e novo debxmqr-admin sem conflito.
Explicitar IDs do novo repositório A00..A03 versus linhasA01..A09 históricas
da matriz: o painel não implementa gestão de bundle/canal onlineA09/RBAC.
Não alterar fonte/manifest/lock/tagbroker nem client; fase3continua parcial.

Validação: formatos, links locais entre repositórios, URLs/commits verificados,
coerência de checklist/matriz e git diff --check. Documentação sozinha não
exige regressãoRust adicional nem bump/tag artificial. Commit/push documental
somente após estes checks; tags existentes imutáveis. Registrar limites e
publicação efetivamente realizada; agrupadorAGENTS terá registro A00 pósaceite
se precisar atualização, sem alegar que arquivo fora dos repos foi publicado.

Patches documentais iniciais não foram aplicados por contextos divergentes.
Gitdiff confirmou nenhum arquivo alterado; reaplicar com contextos completos
verificados e por repositório, sem substituição ampla.
