# P232 — concluir auditoria MQTT 5, sem confundir relatório com conformidade

ID/versão: P232 v1.8. Data: 2026-10-18.

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

Primeiro probe `p232-client-wire-1.json`: 3PASS/7FAIL, mas controle sub válido
falhou por erro do harness: SUBACK concedeu QoS2 ao pedido QoS0. Os dois
negativos de string não comprovam rejeição do conteúdo nessa execução.
Preservar relatório, corrigir SUBACK para QoS efetivamente solicitado e repetir
em novo relatório antes de usar esses resultados como evidência do client.
Segunda execução: controles pub/sub e rejeição UTF-8 malformado PASS; sete
desvios do client confirmados no recorte. Acrescentar probe de retransmissão
QoS2 com mesmo PID antes de PUBREL e comparar mensagens JSONL efetivamente
exibidas. Repetir controles e negativos em relatórios exclusivos; não corrigir
o runtime para transformar a auditoria em aprovação. Rerodar também os gates
broker VBI/alias existentes no ELF publicado confirmado, com estado nativo.
Validador inicial: 9 contratos sintéticos PASS, mas ledger real FAIL em
MQTT-3.3.1-3/client por applicability/status N/A incompatíveis. Revisar o
julgamento da linha e outros pares equivalentes, sem afrouxar a validação;
preservar resultado inicial e repetir. Novo probe QoS2 observou duas saídas
para a mesma transação antes de PUBREL; registrar como desvio, não corrigir
o produto nesta auditoria.
Revisão independente Astra exige duas correções de julgamento: ausência de
0x8E no takeover não prova violação de MUST (fechamento obrigatório passou);
manter observação/diagnóstico sem desvio obrigatório. Perigos genéricos de
reconexão rumqttc (DUP, alias, pending quota/controle) sem caminho atingível
demonstrado no binário CLI são EVIDENCE_GAP/dependency-only, não DEVIATION do
produto. Reconciliar linhas e achados sem apagar a análise da dependência.
Revisão Luna recomenda observar JSONL nos probes de tópico e explicitar que
validador de accounting não autentica evidências externas. Fortalecer contratos
de tipos/chaves e saída, preservar relatórios antigos e repetir em novo arquivo.
Outra correção Astra: MQTT-4.13.1-2 não existe na fonte; citar §4.13.1 sem ID
no parágrafo do Client. Pacote malformado enviado pelo servidor falso não
prova emissão inválida pelo client. Em §4.13 a resposta do Client é SHOULD,
não o MUST de fechamento do Server. Separar achados de validação recomendada
dos desvios obrigatórios de capacidades/QoS2; não somar oito probes FAIL como
oito violações MUST. Linhas de formato do emissor sem comprovação de emissão
inválida devem manter evidência insuficiente ou suporte estático justificado,
com os probes de recepção explicitamente em categoria separada.
Revisão final Astra: parecer delimitado coerente, sem bloqueio material.
Corrigir comentário "Legitimate duplicate": o vetor é duplicata sintética
para exercer a obrigação do receptor4.3.3-10, não licença para retransmissão
arbitrária do emissor na mesma conexão. Repetir relatório exclusivo6 para
fixar o hash do harness final; nenhuma mudança de oráculo ou runtime.
Gate staged final detectou linha em branco extra no EOF do ledger de
publicações (antes não rastreado no diff de worktree). Normalizar apenas EOF,
atualizar hash desse ledger e repetir staged diff --check; conteúdo semântico
e resultados de protocolo permanecem, falha de whitespace registrada.
Completar a prova de3.2.2-4 com nova invocação comum sem outbox/manifesto local,
Clean Start=false e CONNACK Session Present=1. Observar se a CLI encerra ou
publica; controle canônico permanece. Relatório exclusivo5, sem substituir
as execuções1–4. Classificar os probes em controle, MUST do Client ou
recomendação de recepção, sem afirmar que todo FAIL corresponde a MUST.

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
