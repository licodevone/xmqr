# P249 — Roteiro de comandos para testes Windows

## Revisão 1.2 — suspender ciclos após falha relatada

22/10/2026: operador relata Client em falha após parte do roteiro e sem voltar
ao reiniciar. Imagem042302 mostra apenas os comandos da seção10, não o erro
do serviço. Hash instalado continua P248 correto; token das ferramentas não
elevado, logs/SCM negados; endpoints Broker/Admin indisponíveis nesta consulta.
Não atribuir causa ao timeout90, antivírus, ACL ou sequência sem diagnóstico.

Antes de corrigir documentação: suspender seção10 nas duas cópias e substituir
blocos de start/restart imediato por orientação de coleta existente somente
leitura. Diagnosticar estado/códigos/lifecycle recentes com operador elevado.
Não modificar runtime nem credenciais, não reinstalar/limpar sink e não executar
start/stop automaticamente. Retomar ciclos apenas com espera por estado e
prontidão, após identificar a falha real. Registro com evidência/limites.

Versão 1.0, 22/10/2026. Fatia documental solicitada após reinício do Windows.

Entrada: P248/C152 aplicado pelo operador, captura de observação 100s aceita;
usuário informa aparente funcionamento após reboot. Nova imagem de Serviços
recebida; não extrapolar captura para estabilidade, MQTT ou controles da bandeja.
Base broker 0fbe2dec; alterações locais anteriores preservadas.

Objetivo: entregar um arquivo legível no Codex Desktop e Bloco de Notas com
comandos PowerShell 7 x64 elevado, sequência e resultados esperados.

Escopo: docs/TESTES-XMQR-WINDOWS.md, este prompt, registro P249 e chat P240.
Não alterar runtime, instaladores, versões, registro, ACLs ou serviços do host.
Comandos de controle são exemplos para execução manual, claramente opcionais.

Cobrir: inventário SCM/boot, versões/capabilities, saúde HTTP/portas/métricas,
observação além 90s, publish QoS1 mTLS com credenciais em arquivo privado sem
imprimi-las e confirmação por mensagem sintética no sink; Admin, Manager/tray,
atalhos e acesso às pastas, start/stop/restart ordenados e coleta existente.
Manager é interface de sessão, não quarto serviço. Sem PATH obrigatório.

Aceite: caminhos/opções conferidos na fonte; blocos PowerShell parseados sem
executar ações; nenhum segredo real ou comando de inicialização/reinstalação;
arquivo disponível localmente e salvo para entrega. Distinguir teste de sintaxe
de execução instalada e prova interna de interoperabilidade externa.
Sem commit/push/tag. Não executar testes de VM descartável na instalação atual.

## Complemento v1.1 — pergunta sobre hospedagem

Incluir nota explicativa sobre certificados locais versus servidor com SAN
correto e identidades mTLS individuais; nenhuma geração/troca de certificados
ou configuração de hospedagem autorizada por esta pergunta. Fontes primárias:
RFC9525 e documentação TLS Mosquitto, sem extrapolar capacidades do XMQR.
