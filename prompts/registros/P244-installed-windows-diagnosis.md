# P244 - Diagnostico da instalacao real

Prompt: [P244 v1.1](../broker/244-installed-windows-diagnosis.md), 21/10/2026.
Usuario seguiu a sequencia P243 e relata ausencia de desktop e falha de execucao.
Git de entrada limpo: 0fbe2dec3b8c6d4bb4da7f0a7180fba2498cdeed. Nenhuma alteracao
anterior resetada. Investigacao independente de fonte SCM feita por agente,
somente leitura; sem instalar/iniciar/parar/reparar/desinstalar no host.

## Evidencia da maquina

- Imagem image(1).png resolvida pelo arquivo exato e lida: bandeja mostra
  XMQR Broker - Falha e XMQR Client - Falha. O gerenciador chegou a funcionar.
- HKLM64 e Program Files: Manager, Broker e Client presentes; hashes dos tres
  executaveis coincidem integralmente com P242/P243.
- Logs MSI3e326.LOG, MSI60606.LOG e MSIae91f.LOG em Temp do usuario: respectivos
  produtos Manager/Broker/Client, engine retornou0, XMQR_START_MENU=1,
  XMQR_DESKTOP=0 e XMQR_ACCEPT_LICENSE=1. Somente esses campos foram coletados.
- Existem os tres .lnk no menu comum XMQR: Broker, Client e Manager. Busca
  indexada mostrando somente Broker nao comprova ausencia dos outros atalhos.
- Desktop publico sem atalhos XMQR; parametro desktop ficou0 nos tres logs.
  Isso e consistente com opcao desmarcada, nao prova falha do CreateShortcuts.
- Admin nao tem registro HKLM Components, executavel instalado ou servico;
  `sc.exe queryex xmqr-admin` retorna1060 (ausente).
- Services registry mostra Broker/Client como LocalService, Start=auto e
  ImagePath correto. Consultas SCM dos dois, icacls e logs privados retornam
  acesso negado5 no token desta sessao. Nao interpretar isso como inexistencia.

## Limite e lacuna operacional

As17 verificacoes P243 eram de empacotamento/contratos/tabelas MSI. Nao eram
aceite do servico ja instalado. A sequencia foi correta, mas a orientacao foi
incompleta quanto ao provisionamento necessario antes de iniciar.

O template Client vem com arguments=[] e e recusado antes de conectar.
O Broker exige server.crt/key/ca.crt, users.toml e acl.toml; o MSI nao fornece
credenciais ou certificados de producao. Esses pontos explicam falhas de uma
instalacao ainda igual ao modelo; o conteudo instalado nao foi lido nesta
sessao por falta de acesso. Nao afirmar essa igualdade sem diagnostico.

Revisao do agente: ACL de DACL pretendida e compativel com LocalService, mas
owner individual em arquivos privados poderia ser rejeitado pelo Client.
Logs fixos e status Win32=1 sao genericos; ausencia de service.log nao prova
sozinha causa. O coletor solicita owner/DACL e igualdade de hash para resolver.

## Ferramenta concreta preparada

`scripts/collect_windows_installed_diagnostics.ps1` exige administrador64-bit,
le somente status SCM, existencia/owner/DACL e hash do TOML comparado ao modelo.
Le somente mensagens fixas permitidas de service.log; nao exibe senha, chave,
payload ou conteudo de configuracao. Caminhos de configuracao nao padrao sao
recusados. Nao usa Win32_Product, nao muda ACL nem controla servicos.
Resultado: `target/p244-diagnostic/installed-diagnostics.json` na mesma arvore.
Parser PowerShell: PASS. Launcher interativo `scripts/Diagnosticar-XMQR.cmd`.

Tentativa de iniciar PowerShell RunAs com esse arquivo concreto: Windows
retornou acesso negado ao Start-Process. Processo administrativo nao iniciou;
nenhum relatorio foi produzido. Isso foi falha de permissao do Windows, nao
uma rejeicao reportada de revisao automatica. Sem contornar a restricao.

Coleta elevada, causa exata por componente, normalizacao de owner quando
necessaria e configuracao inicial permanecem pendentes do relatorio do
operador. Nao substituir configuracao, gerar credenciais ficticias ou anunciar
servicos funcionando sem essa evidencia. Nenhum novo instalador foi gerado
apenas para repetir a instalacao falha. Sem commit/push/tag.

Reparo concreto preparado: `scripts/Corrigir-XMQR.cmd` chama um reparador separado
para atalhos de desktop e o coletor. O reparador cria apenas nomes fixos para
Manager e produtos presentes em HKLM com executavel existente; usa o desktop
publico conhecido do Windows, recusa reparse points, preserva links existentes
e aponta todos para o Manager registrado. Nao instala Admin ausente nem muda
servicos/configuracoes/ACL. Foi revisado e parseado, mas nao executado no host
por depender da elevacao bloqueada. O operador precisa executar o launcher
como administrador e disponibilizar o JSON para concluir o diagnostico.
