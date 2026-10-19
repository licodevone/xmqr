# P233 v1.0 — acompanhar correções após a auditoria P232

Data: 2026-10-19. Entrada: broker `ebe54a5`, 0.43.0 publicado; auditoria
P232 encerrada com achados históricos. Client 0.42.0/bridge 0.4.0 publicados
por C143, fonte `e0e553c`, cinco MUST corrigidos. C144 incorporado em `25c2e8a`
com CI `39194165930` PASS, quatro recomendações recebidas corrigidas nos casos
testados. C146 prepara 0.42.1 da fonte `db844a0`; publicação ainda pendente.

Objetivo: atualizar o plano com os marcos efetivamente publicados e criar um
acompanhamento separado da auditoria histórica. Não reescrever os ledgers ou
relatórios de P232 nem transformá-los em PASS retroativo. Diferenciar evidência
do ELF publicado, CI de fonte exata, inspeção e pendências. C144 não fecha
automaticamente as 18 lacunas de evidência do client ou as duas do broker.

Escopo: docs/evolution-plan.md, docs/conformance/mqtt5-audit-follow-up.md,
link de acompanhamento no status atual, registro P233. Após verificar C146,
identificar fonte/tag/pacote/imagem e retirar distribuição C139 das pendências,
pois já integra 0.42.0. Preservar fases 6/7 aceitas em seus contratos e fase 8
aberta. Priorizar probes independentes de WS/texto no client e ownership/quotas
QoS 2 no broker, com prompts funcionais próprios antes de eventuais alterações.

Aceite: links/formatos/diff coerentes, fontes e hashes consultados em registros
e GitHub, sem declarar certificação ou produção. Atualização apenas documental;
nenhum teste de protocolo repetido só para editar texto, nenhuma versão/tag do
broker e nenhum estado/serviço do operador alterado. Commit/push autorizados.
