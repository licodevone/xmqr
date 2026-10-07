# Configuração local de trabalho por prompts

Configuração preparada em 2026-10-07 para este repositório. A inspeção encontrou
Codex CLI 0.160.1 no runtime local. Não se executou sessão de modelo ou subagente
para testar ativação. Arquivos configurados não significam agentes em execução.

| Recurso | Formato/local | Uso |
| --- | --- | --- |
| Instruções | [AGENTS.md](../AGENTS.md) | Política de trabalho do repositório |
| Implementação | [.agents/skills/xmqr-rust-mqtt/SKILL.md](../.agents/skills/xmqr-rust-mqtt/SKILL.md) | Fatias autorizadas Rust/MQTT |
| Testes | [.agents/skills/xmqr-tests/SKILL.md](../.agents/skills/xmqr-tests/SKILL.md) | Estratégia, gates e evidências |
| Segurança | [.agents/skills/xmqr-security-review/SKILL.md](../.agents/skills/xmqr-security-review/SKILL.md) | Revisão baseada em evidência |
| Agentes especializados | [.codex/agents](../.codex/agents) | Quatro definições TOML com name, description, developer_instructions |

Papéis: xmqr_explorer, xmqr_rust_mqtt, xmqr_tests e xmqr_security. O nome no
TOML identifica o papel; Markdown isolado em agents/ não registra agente.
Não foi criado config.toml global/projeto nem alterado modelo, permissões,
trust, sandbox, concorrência ou MCP. Os agentes herdam as configurações da sessão.
Restrição de leitura dos revisores é orientação, não uma nova política de sandbox.
Delegação depende de pedido e capacidade disponível na sessão; skill pode ser
usada diretamente pelo agente principal quando não houver subagente.

Para começar: inicie nova sessão com XMQR como diretório de trabalho, leia
AGENTS e invoque $xmqr-rust-mqtt, $xmqr-tests ou $xmqr-security-review conforme
o pedido. Prepare primeiro o prompt da mudança. Skills locais podem ser descobertas
automaticamente; se não aparecerem, reinicie o Codex. Esta sessão delegada mantém
cwd temporário fora do XMQR: a descoberta automática nela não foi comprovada.
Não mudar trust ou permissões para forçar carregamento; informe eventual bloqueio.

Exemplo futuro, somente por pedido: “Prepare o prompt da correção solicitada;
use xmqr_explorer para mapear o caminho e xmqr_security para revisar o diff”.
Isso não inicia os papéis ao abrir este arquivo.

## Fontes e validação

- [Formato de skills e descoberta local](https://learn.chatgpt.com/docs/build-skills).
- [Agentes customizados de projeto](https://learn.chatgpt.com/docs/agent-configuration/subagents).
- [Instruções AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md).
- [Prompt desta configuração](../prompts/01-configurar-agentes-skills.md).
- [Registro](../prompts/registros/P-DOC-02-configuracao.md).

Validação estrutural, links e preservação registrados em prompts/VALIDACAO-CONFIGURACAO.json.
Não houve execução de testes Rust, interop ou servidor. Frontmatter simples usa
name e description; sem scripts, dependências ou metadata de UI desnecessários.


## Verificação efetiva de descoberta

Na retomada, app-server 0.160.1 respondeu initialize e skills/list com cwd XMQR:
xmqr-rust-mqtt, xmqr-tests e xmqr-security-review vieram enabled=true, sem erros
do projeto. Não se abriu turno de modelo, nem acionou agente; os quatro TOMLs
continuam validação estrutural. Não é necessário reiniciar para essa consulta.
Para trabalho futuro, nova sessão no XMQR carrega instruções no contexto correto;
se alguma skill não aparecer na interface, reinicie conforme documentação oficial.
