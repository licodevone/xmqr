# P68 rev1 — IA aplicada à criação e depuração no curso

Entrada broker58b6cd6/0.11.2; client8bb7aaf/0.7.1. Data2026-10-12.
Prompt primeiro. Usuário quer entender todos os passos do uso de IA: agentes,
skills, commands, MCPs e introdução explicada de bibliotecas/comandos novos.

Documentação apenas: módulo didático guide_ai_workflow.py, integração no curso,
sidebar, README, agent-workflow com checkpoint atual e registro. Preservar
arquivos Docker existentes e configurações globais/projeto. Não instalar,
conectar MCP, delegar, criar skill ativa nem integrar IA ao runtime do broker.

Explicar conceitos e fronteiras: prompt/modelo/agente/subagente/AGENTS/skill/
tool/terminal/slash command/MCP/plugin/SDK; contexto, permissões e evidências.
Usar arquivos reais como exemplos, sem considerar agente TOML processo ativo.
Apresentar descoberta/uso, modelos didáticos de AGENTS/skill/agente e seus
tokens sem sobrescrever os existentes. Comandos CLI conferidos por --help;
slash commands/documentação oficial verificados na fonte atual. Explicar
Windows versus WSL e não afirmar configuração compartilhada entre instalações.

Construção: contrato primeiro, implementação digitada, cartão obrigatório de
cada biblioteca/comando novo, revisão e gates pertinentes. Depuração: bug
reproduzível, hipótese/evidência, correção mínima, regressão, atualizar prompt.
Incluir exercício isolado E0382 e correção de ownership, sem atribuí-lo ao
runtime atual. Templates de aula/feature/bug e divisão de papéis verificável.
Fontes OpenAI Docs abertas; distinguir comportamento documentado, inspecionado
e execução comprovada. Aceite: fontes12492 iguais, âncoras/sidebar sincronizadas,
novos capítulos, exemplos Rust/TOML verificáveis, HTML/JS desktop/mobile.
Se surgir erro, revisar prompt antes de corrigir. Commit/push autorizado;
sem tag/release por documentos. Sem gates de runtime por alteração didática.

## Rev2 — destino compartilhado informado pelo usuário

HTML movido pelo usuário para ../docs/code-guide.html, raiz agregadora
rapidez-broker-client. Essa pasta agrupa dois repositóriosGit e não possui.git.
Honrar destino, não recriar HTML em xmqr/docs. Conferir se o conteúdo movido
é idêntico à base antes de atualizar; preservar eventual edição divergente.
Atualizar gerador/notas/referências e registrar remoção noGit do broker.
Explicar que HTML agregado é local; o Git do broker guarda geradores/conteúdo,
mas não publica automaticamente o arquivo fora da sua raiz. Não iniciar
Git no agregador nem mover o documento de volta sem pedido.

## Rev3 — abrir todos e pergunta de WebSocket

Usuário solicita link para abrir todos os tópicos na sidebar e no corpo.
Adicionar ação nos dois lugares, sincronizar aria-expanded e manter âncoras
funcionando sem nova infraestrutura. Testar ambos incluindo capítulosIA.
Pergunta seWebSocket está implementado exige apenas verificação/resposta,
não autorização para implementar transporte: conferir código/manifest/plano.
