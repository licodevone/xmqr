# P240 v1.0 — histórico datado de conversas

Pedido: guardar este chat em docs/chat, vincular a data da interação e atualizar
automaticamente a cada troca de mensagens atendida neste repositório.

Entrada: 2026-10-21, America/Sao_Paulo; HEAD 6cb7b1d, árvore Git limpa,
docs/chat existente e vazio. P239 já incorporado ao HEAD pelo mantenedor.

Objetivo: histórico legível das mensagens visíveis do usuário e do assistente,
com ordem/autoria/data e instrução persistente de atualização pelo agente.
Escopo: AGENTS.md; docs/chat/README.md; docs/chat/YYYY-MM-DD.md; este prompt e
prompts/registros/P240-chat-history.md. As próximas inclusões de mensagens
estão permanentemente autorizadas por este pedido e este prompt; não exigem
novo prompt ou nova confirmação. Outras alterações continuam com seu escopo.

Formato: Markdown UTF-8, arquivo diário no fuso America/Sao_Paulo, seção por
conversa/assunto e entradas numeradas. Registrar horários somente quando
disponíveis; distinguir momento de gravação de horário de envio. Preservar
texto e ordem das mensagens disponíveis, inclusive atualizações e perguntas.
Contexto de ambiente/instruções é referenciado; mensagens internas, raciocínio
privado e dumps de ferramentas não integram a transcrição. Evidências técnicas
ficam vinculadas aos registros existentes. Redigir segredos, se houver.

Implementação: primeiro arquivar o contexto visível desta conversa; acrescentar
regra no AGENTS para gravar novas mensagens ao atendê-las e a resposta final
antes de enviá-la, evitando duplicatas e preservando registros anteriores.
Trata-se de rotina do agente durante atendimento no repositório, sem serviço
em background, captura global ou acesso a conversas indisponíveis.

Aceite: mensagens desta conversa presentes, autoria/data explícitas, links
locais válidos, regra persistente no AGENTS e git diff --check sem erros.
Validar somente documentação; nenhum teste funcional Rust necessário.
Sem mudança de runtime, versões, serviços, permissões, commit ou publicação.
Registro de execução: prompts/registros/P240-chat-history.md.
