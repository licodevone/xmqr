# P238 v1.3 — ícones de tema e busca local do curso

Data:19/10/2026. Entrada broker52477f0, Git limpo; HTML local fora do Git,
SHA256b50b5dc9e5949d22e451a940d13f8ed36a41d0dbaf30ed4f007b46ff1ed01236.
Pedido: substituir texto do botão de tema por sol/lua e verificar a busca
“Buscar nos prompts e arquivos”, inclusive como arquivo local sem servidor.

Escopo: scripts/guide_theme.py, extensão de busca reproduzível se necessária,
scripts/update_code_guide.py, validação browser e registroP238. Aplicar ao
../docs/code-guide.html existente sem regenerar snapshots históricos.
Sem alteração dos softwaresMQTT, pacotes, versões ou releases por edição do curso.

Tema: ícones SVG inline sem texto visível; lua no claro para ativar escuro,
sol no escuro para ativar claro. Nome acessível/title em português, teclado,
preferência persistida, preferência do sistema e storage bloqueado preservados.
Controle compacto com alvo44px, sem recursos externos ou alteração da sidebar.

Busca: diagnosticar comportamento anterior em file:// antes de modificá-lo.
Pesquisar somente o conteúdo incorporado ao HTML, incluindo fontes/prompts
recolhidos; nunca prometer acesso ao disco ou aos prompts posteriores ausentes
do snapshot. Melhorar feedback com contagem/nenhum resultado e limpeza; usar
texto seguro, sem innerHTML de entrada. Busca sem diferenciar caixa/acentos,
com múltiplos termos, contexto de títulos e revelação dos detalhes relevantes.
Ocultar blocos vazios e restaurar conteúdo/abertura ao limpar, mantendo sidebar
coerente. Índice em memória e processamento local, sem fetch/servidor.

Aceite: prompt antes da implementação; registrar diagnóstico prévio, exemplos
reais positivos/negativos e inexistentes, nome de arquivo, acentos/caixa/termos,
consulta com caracteresHTML sem execução, limpar/Escape, detalhes inicialmente
fechados e restauração. Testar no navegador real via file://, sem requestsHTTP,
desktop/mobile, ícones/nome acessível/teclado/temas e regressões P236 relevantes.
Extensões idempotentes, preservar IDs e34checkboxes do aluno sem ticar;
capturas inspecionadas. Preservar FAIL e revisar prompt antes de correções.
Registro, documentação do alcance da busca e commit/push das fontes aceitas,
sem alegar publicação do HTML foraGit. Tags/releases só em marcos de produto.

Diagnóstico antes da correção: o HTML local mudou desdeP237, sem alterar as
fontesGit. Seu SHA real é3c3369f877ea26a82ef51473a238107482d41e55beb1c869861e82592eeb6248;
preservar essas alterações. O controle#collapse não existe mais, mas o script
chama addEventListener nele sem guarda. ErroJS impede registrar a busca:
seis consultas, inclusive inexistente, deixam179cartões sem filtrar.
Relatório dist/p238-search-before.json preservado. O teste antigo só conferia
um cartão não oculto e não demonstrava exclusão; não reaproveitar como aceite.

Revisãov1.1 antes do fix: tornar esse controle opcional no gerador e na
extensão aplicada ao HTML histórico, sem recriar botão removido. Verificar
ausência de errosJS e exclusão real/estado vazio, não apenas algum cartão
visível. Confirmar que extensões existentes não sobrescrevem edições locais;
manter conteúdo fora dos blocos alterados e os IDs/checklists existentes.

O bloco admin do HTML local também diverge da fonteP237; a navegação de folhas
é idêntica. Antes de implementar, acrescentar opção explícita
--appearance-search-only ao updater: aplicar somente tema/busca nesta edição,
preservando integralmente o bloco admin personalizado. Geração completa futura
continua compondo todas as extensões, incluindo a busca reproduzível.

Revisão estática do primeiro rascunho identificou escapes duplicados nas regex
do JavaScript raw e nos separadores de blocos. Corrigir para escapes próprios
do JavaScript/Python antes da aplicação no HTML do usuário; verificar sintaxe
JS, normalização de acentos/espaços e ausência de texto literal barra-n.
O HTML local ainda não foi modificado nesta etapa.
