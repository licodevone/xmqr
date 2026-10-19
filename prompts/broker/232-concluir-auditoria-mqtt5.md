# P232 — concluir auditoria MQTT 5, sem confundir relatório com conformidade

ID/versão: P232 v1.0. Data: 2026-10-18.

## Pedido, entrada e escopo

Mantenedor: prosseguir até finalizar a auditoria, com gestão de modelos e
commit/push, tags/releases quando justificados. Broker limpo em
`4bfac0722074c7a1f704f335d2d1b558e68e3d6b` (0.43.0); CI geral P231 agora SUCCESS.
Client em `e03c5a46cfb33666896eb710892cf46e3c40ee38`, com cache preexistente
não rastreado `vendor/rumqttc-0.25.1/target/` preservado. Admin em
`0796d3b4d93ae6815fe2458132f1f8bf0c5c48e4`. Não editar esses pares nesta auditoria.
O catálogo P231 tem 252 IDs literais e anomalias conhecidas, não 252 MUST.

Concluir o relatório de auditoria significa examinar o escopo inteiro,
classificar evidência/desvios/limites e emitir parecer, que pode ser negativo
ou condicionado. Não significa corrigir todos os desvios ou certificar o produto.
Não ocultar revisão faltante como NOT_APPLICABLE ou uma porcentagem de aprovação.

## Entregáveis e papéis

- Ledger por requisito numerado, cobrindo todos os IDs do catálogo, com
  resumo autoral curto, força normativa, aplicabilidade broker/client,
  código/testes e situação de evidência. Texto principal OASIS prevalece sobre
  resumo não normativo. Aliases/IDs malformados explicitamente reconciliados.
- Revisão adicional por seção das regras não numeradas (propriedades/contextos,
  UTF-8/binário, formatos, razões, erros e AUTH), sem alegar que IDs bastam.
- Relatório final, achados priorizados e relação clara entre revisão estática,
  testes executados nesta tarefa e evidência histórica de fonte exata.
- Validador/testes da integridade do ledger; CI offline correspondente.
- Probes direcionados novos, se a revisão encontrar candidato concreto,
  em script `scripts/verify_p232_*.py`, com vetores independentes e relatório
  fora do Git. Nenhuma correção Rust na auditoria; preparar prompt distinto
  se futuramente executar correções sob a autorização de evolução.

Arquivos permitidos: este prompt/registro P232; `docs/conformance/mqtt5-audit-*`,
atualização do guia/status P231; scripts `*p232*`/`*mqtt5_audit*` e CI offline.
Artefatos locais e fontes oficiais integrais somente fora do Git. Não alterar
inventário P231 para inventar PASS; ledger semântico é documento separado.

Gestão: Sol/high nas revisões semânticas independentes e rastreamento de código;
Luna/high em mapeamentos/checagens mecânicas; revisão final independente mais
forte quando houver julgamento transversal difícil. Registrar modelos reais.
Cada agente escreve somente seu ledger, sem Git/publicação/builds concorrentes.

## Contrato do ledger

JSON por partição: `schema_version=1`, `part`, `broker_commit`, `client_commit`,
`requirements` (lista), `unnumbered` (lista), `findings` (lista).
Cada requisito: `id`, `summary` (paráfrase própria), `strength`
(`MUST`, `MUST_NOT`, `SHOULD`, `MAY`, `MIXED`), `broker`, `client`.
Por papel: `applicability` (`APPLICABLE`, `CONDITIONAL`, `NOT_APPLICABLE`),
`status` (`SUPPORTED_BY_INSPECTION`, `EVIDENCE_GAP`, `DEVIATION`,
`NOT_APPLICABLE`), `rationale`, `code` (caminhos relativos, prefixo ../xmqr-client
para o par), `tests` (caminhos existentes ou vazio), `evidence` (referências
históricas explícitas ou vazio). SUPPORTED_BY_INSPECTION não é PASS dinâmico.
Regras não numeradas: `section`, `review`, `code`, `tests`, `limitations`.
Achados: `id` próprio, `severity`, `summary`, `clauses`, `code`, `status`,
`next_action`; static/probe/histórico sempre discriminados no texto.

## Validação e conclusão honesta

Ler norma oficial e código, não só documentação ou nomes de testes. Para cada
ID, dar aplicabilidade justificada ou desvio/evidência insuficiente explícitos.
Fechar a classificação de toda a matriz; não fechar conformidade quando houver
DEVIATION/EVIDENCE_GAP. Obrigações não numeradas revisadas por seção, limites
de exaustividade declarados. Identificar dependência de rumqttc e defaults.

Validar schema, tipos/chaves únicas, cobertura sem duplicação/perda, hashes de
fonte/evidências, caminhos e julgamentos. Rodar testes offline e comparar os
binários/fontes usados. Reutilizar a CI integrada 39164217059 apenas nas fontes
db472bc/501cde2/4483; não atribuí-la ao client atual sem comparar diferenças.
Testes novos reais com estado/porta privados, deadlines, cleanup, sem instalação
ou serviços operacionais. Prerequisito ausente é BLOCKED, nunca PASS.
Falha exige registro e revisão deste prompt antes de correção do harness.

Relatório pode concluir "conformidade não demonstrada" com ações priorizadas;
isso é conclusão de auditoria, não bloqueio artificial nem falsa aprovação.
Confirmar com revisão independente que conclusão não oculta trabalho não feito.
Se materialmente faltar revisão, manter auditoria aberta e continuar trabalhando.

## Publicação e segurança

Seguir skills de testes e revisão de segurança do XMQR, MIT e licenças de
terceiros. Não ler C:/x81, senhas, certificados privados ou estado do operador.
Não publicar vulnerabilidade não corrigida conforme SECURITY.md; manter
evidência sensível em artefato privado e informar mantenedor sem PoC pública.
Após aceite publicar commit/push próprio. Sem bump/tag/release/deb/Docker para
auditoria sem mudança runtime; manter versões/tags/latest existentes intactos.
