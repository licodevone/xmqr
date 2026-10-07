# Prompt mestre — manutenção do XMQR

Leia o contrato-base, contexto, sequência, cobertura, CONTRIBUTING, VERSIONING,
matriz de conformidade e código. Confirme o alvo e o estado de trabalho existente.
Prepare primeiro o prompt específico do pedido com ID e plano revisável.
Classifique o que já existe, o que exige correção e o que é proposta não autorizada.
Escolha a menor fatia do pedido; não reconstrua recursos existentes por prompts históricos.
Identifique comportamento observável, cláusulas, limites, riscos, arquivos e migração.
Leia [AGENTS](../../AGENTS.md) e escolha as skills locais pertinentes de
.agents/skills. Papéis configurados: xmqr_explorer, xmqr_rust_mqtt, xmqr_tests
e xmqr_security, descritos em [uso e carregamento](../../docs/agent-workflow.md).
Use somente ferramentas disponíveis; MCPs externos não são dependências instaladas.
Não delegue automaticamente; solicitação de agentes deve vir do usuário.
Implemente apenas o escopo funcional que o mantenedor pediu. Valide segundo
CONTRIBUTING, registrando resultado real e BLOCKED quando falta pré-requisito.
Atualize documentação pertinente quando autorizada, sem promover versão em PR comum.
Não avance para outro prompt, não faça commit/publicação e não implemente o consumidor.

Entrega: estado, prompt preparado, diff, validação real, limitações e próximo passo.
Origem preservada: [orquestrador anterior](../origem/broker/01-master-orchestrator.md).
