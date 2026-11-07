# P257 — atualização instalada do Manager Windows

Data: 2026-10-25, America/Sao_Paulo. [Prompt v1.0–v1.1](../broker/257-manager-installed-update.md).
Autorização atual: usuário pediu "prossiga com a atualização".
HEAD de entrada 7c7a989; histórico local anterior preservado. Apenas atualização
da instalação Manager 0.1.0 → 0.1.1 e documentos desta operação.

## Execução e verificações

- SHA-256 do MSI em dist/releases/p256-verify/windows conferido:
  cd193c74e37267e66d14a63cd52d3cadb147f6e21e39071829657e52238e3f7f.
- Serviços antes da operação: admin Running, broker Stopped,
  client-default Stopped; todos Auto. Snapshot sanitizado local em
  dist/local-updates/p257-manager-20261025/services-before.json.
- Encerrado somente o Manager antigo. MSI aplicado com /qn /norestart,
  REBOOT=ReallySuppress, licença MIT existente e ambas as opções de atalhos
  preservadas em 1. msiexec retornou 0: instalação bem-sucedida, sem pedido
  de reboot. Log local em dist/local-updates/p257-manager-20261025/upgrade-msi.log.
- Registro de desinstalação confirma uma instalação XMQR Manager 0.1.1.
- Executável instalado em C:\Program Files\XMQR\Manager\xmqr-manager.exe:
  SHA-256 3c4e11e1ae9e67e7a01d632d84d6dbf69addda4a85e2202ae0bc12c1e7c5943e,
  correspondente ao executável P256 publicado e validado anteriormente.
- Probes do executável instalado capturados por pipes: --version retorna
  xmqr-manager 0.1.1; --help inclui --control-all start|stop|restart;
  --diagnose retorna os três componentes sem erro global de inventário.
  Admin aparece em execução; broker/client preservam o estado Falha reportado
  pelo SCM. Nenhuma ação de controle real foi executada.
- Atalhos comuns do desktop e menu Iniciar apontam para o executável instalado.
  Autostart HKLM Run preservado no mesmo caminho.
- Reabertura direta herdou token administrativo do agente. Conforme revisão
  1.1, esse processo foi encerrado e a bandeja reaberta pelo Shell do desktop.
  Processo final 30428, sessão interativa; TokenElevation consultado pela API
  Windows confirmou False. Nenhuma mudança de permissões foi necessária.
- Comparação final dos nomes/estados/modos de inicialização dos três serviços
  com snapshot inicial não encontrou diferenças.

## Limites e encerramento

Skill computer-use consultada para inspeção visual. list_windows/list_apps
não expõem janela controlável da bandeja nem barra de tarefas nesta sessão;
portanto não houve comprovação visual do menu. O processo permanece ativo,
e os comandos foram comprovados pelo help do binário instalado e sua identidade
com o pacote P256. Não foi necessário alterar código nem repetir gates Rust
já aprovados na conferência imediatamente anterior (20 testes, fmt e Clippy).
Controle real do conjunto, UAC, reboot/login e resolução das falhas anteriores
dos serviços não foram exercitados por esta atualização. Não houve alteração
dos produtos/configurações/dados, commit, push, tag ou publicação nesta tarefa.
