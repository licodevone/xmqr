# XMQR Manager Terminal Windows 0.1.0-rc.1

Menu PowerShell7 para uso local posterior no Windows. O pacote inclui copia
portatil IMUTAVEL do Manager Windows0.1.1 publicado, SHA3c4e11e1..., licencas e
notices originais. A interface chama apenas --diagnose/--control/--control-all;
nao abre a bandeja, nao instala programas nem configura servicos/ACLs.

Extraia o ZIP numa pasta nova e, no PowerShell7, entre nela. Confira antes o
SHA256 do ZIP com o arquivo .sha256 e os arquivos extraidos com SHA256SUMS.
O wrapper verifica adicionalmente o hash do helper antes de cada invocacao
inicial. Nao e necessario instalar o Manager grafico para usar esse pacote.

```powershell
pwsh -NoProfile -File .\XMQR-Terminal.ps1 -Action version
pwsh -NoProfile -File .\XMQR-Terminal.ps1 -Action status
pwsh -NoProfile -File .\XMQR-Terminal.ps1
pwsh -NoProfile -File .\XMQR-Terminal.ps1 -Action restart -Target all -DryRun
```

Status e plano nao alteram servicos. Para iniciar/parar/reiniciar, abra o
PowerShell como Administrador e execute explicitamente o comando desejado:

```powershell
pwsh -NoProfile -File .\XMQR-Terminal.ps1 -Action restart -Target all
pwsh -NoProfile -File .\XMQR-Terminal.ps1 -Action stop -Target client
pwsh -NoProfile -File .\XMQR-Terminal.ps1 -Action start -Target client
pwsh -NoProfile -File .\XMQR-Terminal.ps1 -Action logs -Target broker
```

Alvos: broker/admin/client/all ou ID completo do status. Client exige ID completo
quando houver varias instancias. Entradas CLI sem servico nao viram servicos.
Helper original consulta registro HKLM64 protegido, confirma executavel SCM e
executa ordem Broker/Admin/Clients, parada inversa. Falha interrompe o conjunto
e pode deixar etapas concluidas. Reconsulte status antes de repetir.

Logs nesta interface sao eventos Service Control Manager do Windows, nao
payloads ou arquivos privados do broker. Busca finita nas ultimas1000entradas
SCM de7dias, correspondencia exata por dados do evento, ate100resultados.
Permissoes do Event Log continuam aplicaveis. Nao compartilhe logs privados.

Menu/consulta nao significam readiness MQTT. Servico em transicao, consulta
indisponivel ou executavel divergente bloqueia controle. Nao ha elevacao
automatica/UAC, desvio de politica de execucao ou mudanca de firewall/contas.
Se o prazo do wrapper expirar, o helper pode continuar: consulte status em vez
de repetir. O frontend aceita somente o helper oficial0.1.1 fixado; build
local diferente e recusado. Outra copia oficial pode ser dada por -ManagerPath.

Validacao: testes de politica/controle com invocador simulado; nenhum servico
real e iniciado/parado/reiniciado nos testes. Uso real administrativo permanece
pendente. O componente e candidato independente, sem nova tag/release/MSI.

Fonte: tools/windows-manager/terminal; registroP263 em prompts/registros.
Licenca MIT do frontend; licencas/notices do helper incluidos sem alteracao.
