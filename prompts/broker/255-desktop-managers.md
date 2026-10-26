# P255 — Managers Windows e Ubuntu

Versão 1.0, 2026-10-25, America/Sao_Paulo. Pedido: corrigir o gerenciamento
Windows e criar equivalente para Ubuntu. Entrada: HEAD 654410c, P254 somente
documental e históricos locais preservados; Manager 0.1.0 independente.

Objetivo: atalhos protegidos funcionam após autenticação administrativa explícita;
erros são visíveis sem reabrir o menu. Ubuntu recebe Manager de desktop para
componentes instalados, controle systemd e atalhos. Não se confunde Running
com prontidão MQTT. Admin Ubuntu publicado é CLI/painel iniciado pelo operador;
não fabricar serviço ou painel em execução onde não há unit instalada.

Escopo: tools/windows-manager (helper --open, sondagens, navegador de pastas
protegidas e avisos), tools/linux-manager (backend, GTK, testes e pacote .deb),
scripts/build-windows.ps1 quando necessário, documentação e registro P255.
Não alterar broker/client/admin, protocolo, persistência ou versões existentes.
O novo pacote Ubuntu tem versão inicial própria 0.1.0; sem migração de dados.

Windows: inventário HKLM relido no helper; argumentos limitados a IDs e ações;
sem caminho arbitrário recebido pela elevação. Tentar acesso como usuário e
solicitar UAC só por acesso negado. Diferenciar ausência, tipo errado e acesso
negado. Explorer normal para pastas acessíveis; navegador WinForms elevado
para pastas protegidas, sem grants NTFS. Não elevar Explorer. Editor elevado
somente para configuração registrada. Cancelamento UAC visível. Conteúdo de
configuração, chaves e logs não vai para evidências. Novo binário/pacote é
construído para revisão; substituir instalação exige autorização específica.

Ubuntu: Python3/GTK, descoberta limitada a binários e units XMQR; sem shell
interpolado. systemctl usa polkit; GIO admin:// para caminhos protegidos e
ações de arquivos autenticadas; journal de unit limitada. Aplicativo não roda
como root, não instala política permissiva e não cria/reinicia serviços por
iniciar o Manager. Interface responsiva, uma operação por vez, estados
atualizados e erros explícitos. Pacote independente e atalho desktop; bandeja
AppIndicator opcional quando a sessão oferece suporte. Nenhum serviço do
usuário é usado como fixture.

Aceite/validação: Windows fmt/test/clippy/build do crate independente, negativos
de caminho/tipo/acesso e integridade de dados transmitidos ao PowerShell;
PowerShell parse, fixtures próprias e build do instalador se disponível.
Ubuntu testes backend (estados, descoberta, validação, comandos, falhas),
py_compile, pacote .deb inspecionado e teste GUI isolado quando GTK disponível.
UAC/polkit e desktop real devem ter limites explícitos se não reproduzíveis.
Registrar PASS/FAIL/BLOCKED/NOT_RUN reais em prompts/registros/P255-*.md.
Sem commit, push, tag, publicação ou alterações de permissões/serviços reais.

## Revisão v1.1 — falha observada no empacotamento Windows

O build release passou, mas build-windows.ps1 falhou na captura de --version
de um executável GUI: stdout pipe fechado (Windows 232), antes de gerar MSI.
Corrigir a captura de probes GUI por ProcessStartInfo com redirecionamento e
espera explícitos, argumentos separados e prazo limitado. Validar os probes
e repetir o build em diretório novo; não reutilizar artefato incompleto.
Acrescentar CI específica dos Managers e testes GUI Ubuntu isolados.

## Revisão v1.2 — comandos gerais solicitados durante a implementação

Pedido adicional: iniciar/parar/reiniciar os três serviços pelo Manager.
Acrescentar comandos gerais em Windows e Ubuntu, mantendo os individuais.
Alvo: somente serviços XMQR instalados/registrados; CLIs sem serviço são
ignoradas e não viram placeholders. Início: broker, admin, clients; parada:
clients, admin, broker. Reinício: parar o conjunto, depois iniciar o conjunto,
inclusive serviços previamente parados. Estado desconhecido/transição ou
executável divergente bloqueia o conjunto antes da primeira alteração.
Uma operação por vez, parar no primeiro erro, informar possível execução
parcial e reconsultar estados; não alegar transação ou rollback automático.
Windows: helper --control-all relê HKLM; uma solicitação UAC para o conjunto
quando acesso for negado. Ubuntu: autenticação normal do systemd/polkit;
autorizações podem ser solicitadas por unit conforme a política do desktop.
Negativos e ordem devem ser testados com adapters/fixtures, sem reiniciar
os três serviços reais do operador. Novos pacotes substituem candidatos
anteriores apenas na entrega; preservar todos os artefatos existentes.

Revisão v1.3: 20 testes Windows passaram; Clippy recusou um if aninhado no
fluxo de elevação geral. Colapsar com let-chain, preservar comportamento e
repetir fmt/test/Clippy antes do build final. Ubuntu: 29 testes e smoke GTK
com reinício geral passaram em container; não equivalem a polkit/SCM reais.

Revisão v1.4: inspeção do .deb encontrou o diretório raiz do staging herdando
0700 do TemporaryDirectory. Normalizar explicitamente para 0755 antes de
empacotar e validar permissões/ownership do tar, launcher isolado e atalho.
Não instalar esse candidato anterior; gerar novo arquivo em pasta nova.
