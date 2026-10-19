# P236 — guia administrativo, temas e navegação

2026-10-19. Promptcf72ae7 antes do código, revisõesv1.1–1.3 registradas.
Basebroker195f9c2. Pedido explícito: atualizar ../docs/code-guide.html com
operação atual dos três programas, claro/escuro e sidebar sem setas para folhas.

Entregue fragmento versionado docs/course-admin-web.html com oito aulas,
15passos e34caixas manuais inicialmente desmarcadas. Cobre WSL/caminhos,
versões publicadas vs fonteA23–A25, portas, compilação sem substituir pacote,
monitor/logs/journalctl, token0600/bootstrap/senhaArgon2id/papéis/sessões,
perfisMQTT e senha privada, console/SUBACK/lease e indicadoresON-LINE/OFF-LINE.
Reset em subshell define/valida backup antes de mover caminhos fixos; exclusão
recebe caminho real validado sob /var/backups e usa rm-rI com y/n explicado.
Nenhum comando de limpeza foi executado pelo trabalho documental.

Extensões independentes/idempotentes guide_admin_panel, guide_theme e
guide_leaf_navigation, compostas em update_code_guide.py, preservam o snapshot
histórico. Gerador principal chama updater ao final para futuras regenerações.
Sidebar obtém títulos do fragmento e mantém links diretos sem details/summary/
seta/aria-expanded onde não há filhos. Tema respeita preferência do sistema,
salva escolha local e continua funcionando com storage bloqueado. Impressão
permanece legível. Sem bibliotecas/recursos remotos ou dados privados.

## Evidência

HTML local inicial SHA256
4b9708d71e4616058b67930ac3a7bf5df317ae52aea62f166f277bef598f2060.
Final SHA256
28ecafd9ba9f5250174cfc157e79819056c445e1be18c469936972e17bc3b5d8.
Arquivo pedido fica em ../docs, fora dos três Git roots; fontes, fragmento,
scripts e evidências são publicados aqui. O HTML local foi efetivamente atualizado.
Não alegar que o arquivo fora do Git foi enviado ao GitHub.

PythonAST/JSnodecheck PASS. Vinte blocos de comandos passam bash-n
(somente sintaxe, sem executar instalações/reset/exclusão). Updater executado
duas vezes: segunda execução informa já atualizado. Testesleaf5/5PASS;
estrutura real207links diretos/19pais expansíveis, IDs únicos/âncoras válidas.
[Browser](../../docs/evidence/p236/browser.json):11/11PASS Chromium1248,
desktop/mobile/print, temas/reload/sistema/storage indisponível, nomes iguais,
clique repetido de folha sempre abre aula, pais expandem, busca e34checkboxes.
Cinco capturas inspecionadas em dist/p236-browser-1; nenhum recurso remoto.

[FAIL inicial](../../docs/evidence/p236/leaf-first-fail.json): helperoffset
colidia com int interno deHTMLParser, cinco casos recusados antes de tocar
HTML final; após promptv1.2, renomeadocharacter_offset e mesmos casosPASS.
Outra expectativa de contagem errou16vs15passos; promptv1.3 registrou a
correção da validação, sem mudar o contrato/conteúdo para satisfazer o teste.
Uma tentativa de copiar snapshot para dist falhou por diretório de trabalho
omitido; não alterou o documento. Diretório vazio acidental retirado sem
recursão; resultado final copiado para dist/p236 no repositório correto.

Não houve alteração do protocolo/runtime broker/client, versão, pacote,
Docker, tag ou release. Fase8 permanece aberta no guia; implementação e
aceiteC148 foram retomados separadamente pelo pedido mais recente.
