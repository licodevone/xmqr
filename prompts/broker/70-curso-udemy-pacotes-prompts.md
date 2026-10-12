# P70 rev1 — curso Udemy e pacotes cumulativos por prompt

Entrada f231226; client8bb7aaf. HTML compartilhado ../docs/code-guide.html.
Pedido: retirar analogias/escola, campos Prompt para iniciar uma aula e
Preparação das aulas pelo professor; organizar seções/aulas; instruções
concretas e bibliotecas para iniciantes; explicar estados dos prompts e termos
contexto/fronteiras/runtime; fornecer ZIPs cumulativos e autoria por prompt.

Preparado antes de editar. P68 de configuraçãoIA permanece preparado.
Escopo documental/geradores/material ZIP local, sem alterar runtime original.
Preservar anexos Docker e o HTML no agregador. Não publicar curso na Udemy.

Auditar Git/registros para relacionar prompts e código sem inventar entregas.
P00..P18 incluem contexto/planos, não versões implementadas progressivas.
P01 orquestrador não contém código gerado: explicar claramente. História
anterior à importação não permite reconstruir todos os snapshots por ID.
Pacote por prompt existente: contrato, explicação, evidência, diff e snapshot
cumulativo quando comprovável; planos sem snapshot próprio preservam último
snapshot comprovado e identificam material herdado. Antes da primeira base
comprovada, entregar documentos sem inventar código. Lacunas de ID declaradas.
Snapshot completo do commit inclui código anterior+mudança do marco. Fonte
original intacta dentro doZIP; cópia didática comentada indica linhas geradas
ou alteradas por ID comprovado, sem confundir autoria anterior à importação.
Comentários por prompt somente nas cópias, nunca mudar runtime pela legenda.

Gerar índiceJSON/HTML eSHA-256, ZIPs broker/client separados em ../docs/curso-udemy,
catálogo noHTML com links locais e detalhes das mudanças. Não versionar binários
ZIP fora do broker. Versionar geradores/conteúdo/mapeamento e registrar evidências.
Verificar paths/zip-slip, integridade, snapshots, ausência de chave privada/estado/
credencial; recusar conteúdo privado e registrar exclusões. Não afirmar testes
históricos como recém-executados nem autoria exclusiva baseada em arquivo lido.
Mapas inferidos recebem status explícito, não equivalência ao promptexecutado.

Validar HTML/sidebar/links, estrutura de seções+aulas e remoção dos campos;
exemplos didáticos proporcionais; descrições/diffs e arquivos ZIP reais. Revisar
prompt antes de corrigir falha. Commit/push autorizados, sem tag/release documental.

## Rev2 — duas aulas iniciais e seções por código acrescentado

Usuário reduz aulas iniciais1–4 para no máximo2, ampliando detalhamento.
Agrupar entrada/impressão emuma aula evariável/decisão na segunda, com todos
os checkpoints mantidos. Cada novo token/comando/biblioteca precisa explicação
antes de ser usado; incluir objetivo, sintaxe, parâmetros, resultado, erro e
ligação com o trecho anterior. Estruturar seções reais no corpo/na sidebar,
com aulas internas para cada evolução comprovável, detalhando arquivos e diff.
Planejamento sem código é aula de decisão/contrato, não aula de implementação.

## Rev3 — geração de leitura histórica

Primeira geração dos ZIPs chegou aos marcos com código, mas o leitor de notas
reutilizado referenciou pending ausente do contexto isolado. Corrigir somente
esse contexto, mantendo fontes originais intactas e verificação de cadaZIP.
Repetir geração antes de reivindicar todos os pacotes prontos. As primeiras
aulas originais foram condensadas noHTML por módulo de revisão; a verificação
deve examinar oHTML final, não confundir conteúdo substituído com aulas exibidas.

## Rev4 — tipo do estado do leitor

A segunda tentativa demonstrou que pending é lista mutável no leitor, não
valor opcional. Inicializar como lista vazia conforme o anotador original e
verificar geração completa. A correção não altera código histórico de execução.

## Rev5 — leitura eficiente dos snapshots

Geração por muitos processos git show é lenta para a quantidade de snapshots.
Ler cada árvore por git archive em memória, sem extrair caminhos no filesystem,
mantendo checagem de caminhos, conteúdo e exclusões. Interromper geração anterior
se necessário e regerar os mesmos destinos; não apagar anexos preexistentes.

## Rev6 — novo prompt encontrado durante a geração

Outra alteração local acrescentou P71 e modificou evolution-plan.md durante
esta entrega. Preservar ambos, sem editar/commitar esse trabalho. O catálogo
passou de90 para91 prompts/ZIPs; P71 entra somente como documento com código
herdado, sem execução declarada. Verificador falhou na contagem90 fixa;
substituir por contagem dos arquivos atuais e repetir integridade, sem reduzir
as verificações de fontes/ZIP/snapshots nem executar P71.
