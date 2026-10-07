# P-DOC-02 — Registro da configuração documental

- Pedido: configurar agentes/skills e alinhar instruções no XMQR.
- Estado de entrada: prompts/ existente e não rastreado; diff rastreado vazio.
  Nenhum AGENTS.md, .agents ou .codex existia no alvo na inspeção inicial.
- Prompt preparado antes das alterações: ../01-configurar-agentes-skills.md.
- Criados: AGENTS.md, três SKILL.md, quatro agentes TOML, docs/agent-workflow.md,
  prompt e este registro. Atualizados: contrato, orquestrador, índice e sequência.
- Formatos conferidos na documentação oficial; Codex CLI local 0.160.1 identificado.
- Comandos de Rust e interop conferidos em CONTRIBUTING, CI e scripts; não executados.
- Python existente possui tomllib. quick_validate.py requer PyYAML ausente;
  validação alternativa verifica o subconjunto YAML efetivamente usado (nome e
  description com string JSON, sintaxe compatível YAML), nomes, estrutura e links.
  Nenhuma dependência instalada para obter o validador.
- Resultado objetivo: ../VALIDACAO-CONFIGURACAO.json.
- Originais e prompts de clientes preservados; nenhuma mudança funcional ou commit.
- Carregamento efetivo de agentes/skills nesta sessão não testado: cwd temporário
  fora do repositório. Iniciar nova sessão no XMQR; reiniciar se skills não aparecerem.


Retomada: initialize/skills-list no app-server confirmou as três skills locais
enabled=true, sem erro do projeto. Agentes TOML permanecem validados estaticamente,
sem spawn/modelo. Consulta executada sem mudar trust, config global ou permissões.
