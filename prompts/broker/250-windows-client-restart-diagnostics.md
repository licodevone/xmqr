# P250 — Diagnóstico somente leitura de falha após restart

Versão1.0, 22/10/2026. Base0fbe2dec/alterações locais preservadas.

Entrada: usuário relata Client em falha após parte de P249 e sem recuperação.
Captura042302 contém apenas roteiro; hash instalado é P248e9228b...bf51.
Ferramentas não elevadas, SCM/log negados; conexões HTTP9090/9080 recusadas.
Auditoria por agente: sem regressão restart comprovada; Running antecede
CONNACK, orçamento10reconexões é finito; sink exige ACL/arquivo/LF/capacidade.
Coletor existente não inclui metadados do sink e não diferencia estas causas.

Objetivo: uma coleta administrativa útil sem mudar estado da instalação.
Escopo: scripts/collect_windows_installed_diagnostics.ps1, registroP250 e chat.
Acrescentar PID ao SCM, metadados do sink, tamanho/LF final e observação de
estabilidade de tamanho, inventário dos listeners8883/9090/9080 com erro explícito.
Reusar mensagens lifecycle permitidas; preservar demais campos atuais.

Nunca imprimir conteúdos de sink, TOML, senhas, chaves, tokens ou payloads;
não abrir configuração privada para obter argumentos/limites. Limite padrão
8MiB é referência P247, não leitura da configuração real. Compartilhar somente
leitura/escrita no handle de consulta, sem criar/truncar/mover arquivos do host.
Não relaxar ACL/reparse; recusar reparse no caminho do sink. Somente relatório
no target do workspace. Sem start/stop/reinstalação/inicialização/publicação.

Aceite: parser PASS; helper em temporários comprova vazio/LF/nãoLF/ausente sem
conteúdo no resultado; nenhuma operação elevada real pelas ferramentas.
Operador executa o coletor e envia JSON. Runtime/causa/recuperação pendentes
de evidência real; não declarar testes instalados aprovados. Sem commit/push/tag.
