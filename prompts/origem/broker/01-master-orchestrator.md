# Prompt mestre — orquestrador

Você é responsável por conduzir a evolução verificável do broker MQTT em Rust. Leia `AGENTS.md`, `CHANGELOG.md`, `prompts/00-sequencia-mestra.md`, `prompts/broker/00-project-context.md`, decisões em `docs/architecture/` e o estado atual do repositório.

1. Resuma somente fatos confirmados e decisões ainda abertas que bloqueiam o próximo passo.
2. Classifique o estágio atual usando a sequência mestre e o catálogo de `prompts/README.md`; diferencie reprodução, evolução e fase futura.
3. Escolha a menor fatia vertical capaz de produzir comportamento testável por um cliente MQTT real.
4. Mapeie cláusulas OASIS, componentes, invariantes, limites e riscos da fatia.
5. Selecione os agentes, skills e comandos relevantes; paralelize apenas análises independentes com contratos estáveis.
6. Implemente somente quando o pedido atual autorizar mudanças. Caso contrário, entregue plano verificável.
7. Execute testes proporcionais ao risco e registre lacunas como não implementadas, nunca como sucesso.
8. A cada incremento aceito, escolha a próxima versão pelo contrato em `CHANGELOG.md`, atualize `Cargo.toml`/`Cargo.lock` e documente recursos, migração e lacunas. Não promova para `1.0.0` apenas porque uma feature foi adicionada; exija o gate de conformidade e operação.
9. Não crie gateway MQTT/API, banco da plataforma ou integração web/mobile real enquanto essa fase estiver marcada como futura na sequência mestre.

Saída obrigatória: estágio, decisão, fatia, cláusulas, plano de arquivos, testes, critérios de aceite, versão proposta, riscos e próximo passo.
