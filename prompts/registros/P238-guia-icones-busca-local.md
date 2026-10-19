# P238 — ícones e busca local do curso

Executado em19/10/2026 sob [P238v1.3](../broker/238-guia-icones-busca-local.md),
criado antes da implementação. Entrada Git52477f0 limpa. O HTML local foraGit
tinha edições posteriores ao checkpointP237, SHA256
`3c3369f877ea26a82ef51473a238107482d41e55beb1c869861e82592eeb6248`.

## Diagnóstico anterior

[Probe file://](../../docs/evidence/p238/search-before.json) comprovou busca
inoperante: seis consultas, inclusive termo inexistente, mantinham179cartões
sem filtrar. ErroJS: addEventListener em null porque o controle#collapse
não existia mais. O erro interrompia o script antes de registrar a busca.
O teste anterior só verificava algum cartão não oculto, sem demonstrar exclusão;
o novo aceite exige subconjunto real, estado vazio e zero errosJS.

O bloco admin também divergia da fonte atual. Não foi regenerado nem sobrescrito.
P238v1.2 definiu --appearance-search-only para atualizar exclusivamente tema e
busca. O controle removido não foi recriado; virou opcional no gerador e no HTML.

## Alterações

- Botão44×44 com SVG inline: lua no claro para ativar escuro e sol no escuro
  para ativar claro. Sem texto visível; aria-label/title em português, teclado,
  preferência persistida/sistema e storage indisponível continuam funcionando.
- Busca local com índice em memória, sem HTTP/fetch ou servidor. Ignora caixa
  e acentos, combina termos e considera títulos e conteúdo incorporado, inclusive
  fontes/prompts recolhidos. Não lê arquivos do disco ou prompts ausentes do HTML.
- Contagem, aviso de nenhum resultado, limpeza por botão/Escape, ocultação dos
  blocos/sidebar sem correspondência e revelação de detalhes relevantes. Limpar
  restaura conteúdo e aberturas anteriores. Consulta entra somente como texto.
- Extensão reproduzível no gerador/updater, com composição completa e parcial
  idempotentes. Não regenerou o snapshot do curso nesta execução.

## Validação

Preview passou antes de tocar no HTML. Depois da aplicação no arquivo real:
[browserP238](../../docs/evidence/p238/browser.json)10/10PASS emfile://;
[regressãoP236](../../docs/evidence/p238/regression.json)11/11PASS;
5unitários/estrutura207folhas e19paisPASS. PythonAST e NodeJSsyntaxPASS.
Busca inexistente oculta todos os cartões; configuration.rs gera subconjunto,
acentos/caixa e termos combinados funcionam; load_with revela fonte fechada;
Argon2id é encontrado e consultaHTML não executa nem faz requisição. Zero
errosJS/requestsHTTP, desktop/mobile sem overflow. Três capturasP238 inspecionadas.
As34caixas do aluno continuam desmarcadas.

[Preservação](../../docs/evidence/p238/preservation.json): fora dos blocos de
tema/busca e das duas mudanças esperadas no script legado, conteúdo idêntico,
incluindo bloco admin personalizado. Arquivo#collapse continua ausente.
SHA256finalHTML`dc001926d6a52ee5f1eb2e25a9310a3956499560a0632a8b5038b8626aa8cdb4`.

Revisão estáticav1.3 corrigiu escapes duplicados no primeiro rascunho antes da
aplicação. Dois probes auxiliares falharam por quoting/encoding padrãoWindows
antes de modificar qualquer arquivo; repetidos com argumento literal eUTF8.
Essas falhas não são declaradas como PASS de produto. Diffcheck finalPASS.

Fontes, prompt e evidências serão commitados/enviados ao repositório; o HTML
local está fora das raízesGit, com fontes reproduzíveis publicadas. Sem alterar
versõesMQTT, Docker, pacotes ou tags/releases de software por edição do guia.
