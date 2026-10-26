# P255 — Managers Windows e Ubuntu

Data: 2026-10-25, America/Sao_Paulo. [Prompt v1.0–v1.4](../broker/255-desktop-managers.md).
Entrada: HEAD 654410c, históricos/P254 e alterações anteriores preservados.
Pedido: corrigir atalhos e criar Manager Ubuntu; durante o trabalho, o usuário
acrescentou iniciar/parar/reiniciar os três serviços. Implementados controles
individuais e gerais nos dois Managers. Não foi executado backlog do protocolo.

## Entrega Windows

- Atalhos sondam edição de configuração e listagem real de pastas. Acesso
  negado pode solicitar UAC para helper --open; o helper relê HKLM, sem caminho
  arbitrário vindo da linha de comando. Ausência e acesso negado são distintos.
- Configuração registrada usa Notepad com token elevado quando necessário.
  Pastas protegidas usam navegador WinForms de consulta, sem elevar Explorer,
  mudar ACLs, abrir conteúdo dos arquivos ou seguir links/junções. Pastas
  acessíveis continuam no Explorer. Falhas têm janela independente da bandeja.
- Menu principal: Iniciar todos os serviços, Parar todos os serviços e Reiniciar
  todos os serviços. Plano inclui somente serviços registrados, ignora CLIs,
  bloqueia estados desconhecidos/transição antes de agir. Início broker/admin/
  clients, parada inversa; reinício para o conjunto antes de iniciar. O helper
  --control-all solicita UAC uma vez após recusa, reconsulta o inventário e
  reavalia etapas já concluídas. Não há transação nem rollback automático.
- Erro interrompe sequência e informa possível resultado parcial. Dependentes
  externos não são forçados. Interface permanece responsiva durante o worker.
- build-windows.ps1 agora captura probes GUI com ProcessStartInfo, argumentos
  separados, pipes próprios e espera/prazo explícitos.

## Entrega Ubuntu

- Ferramenta independente tools/linux-manager, Python3/GTK3, janela desktop,
  início no login e bandeja Ayatana opcional. Controles individuais e gerais,
  status periódico, uma operação por vez, diálogos de erro e invalidação de
  estados anteriores quando consulta falha.
- Descobre binários e units XMQR do systemd; instanciações pub/sub/bridge do
  client usam os layouts reais. Confere ExecStart antes de controlar. Admin
  sem unit aparece como CLI; uma xmqr-admin.service existente é descoberta,
  sem inventar configuração, token ou URL. Paths personalizados ficam em
  JSON root protegido em /etc/xmqr-manager/components.d.
- systemctl usa polkit do desktop. GIO/GVfs admin:/// abre configurações/pastas
  protegidas; journalctl via pkexec mostra até 300 entradas somente na janela
  local. Não se cria regra permissiva, credencial, serviço ou diretório de
  estado do produto ao abrir o Manager.
- Pacote independente all/0.1.0-1, dependências declaradas, licença própria MIT,
  atalho, autostart e exemplo de registro Admin. Código e diretórios no pacote
  com owner root, sem escrita de grupo/outros. Launcher Python isolado.
- Workflow .github/workflows/desktop-managers.yml acrescentado; configuração
  local, não executada no GitHub nesta tarefa.

## Verificações reais

| Verificação | Resultado |
| --- | --- |
| Windows cargo fmt --all -- --check | PASS |
| Windows cargo test --locked | PASS, 20 testes |
| Windows cargo clippy --locked --all-targets -- -D warnings | PASS |
| Windows build release do Manager e MSI/WiX | PASS |
| Parser dos scripts PowerShell alterados | PASS |
| Navegador nativo WinForms com fixtures próprias | PASS: janela, listagem, subpasta, retorno à raiz, Unicode |
| Ubuntu 26.04 container: unittest discover | PASS, 29 testes, incluindo ownership e negativos do inventário |
| Ubuntu GTK + D-Bus + Xvfb, serviços simulados | PASS: seleção, parada individual, reinício geral, botões, erros e estados invalidados |
| Screenshot Ubuntu com fixtures | Inspecionada visualmente; rótulos/botões legíveis |
| desktop-file-validate | PASS |
| .deb: estrutura, ownership, modos, launcher/import isolado e atalhos | PASS no smoke de pacote |
| Testes reais de UAC/polkit, instalação/upgrade no desktop | NOT_RUN |
| Iniciar/parar/reiniciar os serviços reais do operador | NOT_RUN deliberado; fixtures/adapters foram usados |
| Rust do broker/client/admin e protocolo MQTT | NOT_APPLICABLE: nenhuma alteração nesses binários/protocolo |

Ambiente: sessão Windows administrativa e container descartável Ubuntu26.04,
com código montado somente leitura. Dependências GTK foram instaladas apenas
no container; não se instalou o Manager no Windows/WSL do usuário. WSL26.04
permitiu construir o .deb, mas --diagnose falhou na consulta systemctl; esse
ambiente não foi usado para declarar integração systemd real.

## Falhas encontradas e corrigidas

1. Build MSI inicial: --version do executável gráfico falhou com stdout pipe
   fechado (Windows232). Corrigido runner de probes; candidatos seguintes
   construídos em novas pastas. Nenhum candidato incompleto foi instalado.
2. Clippy após refatorar sequência geral: collapsible_if. Corrigido let-chain;
   gates finais passaram sem supressão de lint.
3. .deb inicial herdou 0700 no diretório raiz de TemporaryDirectory. Normalizado
   staging para 0755 e umask022; smoke inspeciona os modos do tar antes da
   entrega. Candidatos anteriores não são os arquivos indicados abaixo.

## Artefatos e limites

Pacote Windows final em
`dist/windows/p255-manager-20261025-r4/xmqr-manager-0.1.0-windows-x64-experimental.msi`.
SHA-256 MSI: `0177b526ce371878ce366dd5ce97c1aabbfd340174e4554f5c7182cc2db17b61`.
Executável: `14c79c6d4d9cd880b047d11baec2378bb728f578a0c9139eaaacd49988ae3881`.
Manifest e notices de 79 dependências acompanham o MSI. Fonte local dirty;
não se anuncia artefato de commit limpo ou release publicada.

Pacote Ubuntu final e checksum ficam em
`dist/linux/p255-manager-20261025-r2/`; imagem `preview-ubuntu.png` mostra dados
simulados. O checksum ao lado do .deb identifica os bytes entregues.
SHA-256 .deb: `bb04ce7a9b8a5fa31c6bc95dac0c3a83b6dfec7c121f2da394afb1df7fc10391`.
O build final também foi exercitado sob umask077; diretórios do pacote
continuaram 0755. O smoke confirmou importação isolada e arquivos desktop.

Nenhum Manager instalado foi substituído. O Windows instalado ainda tinha hash
`2EE8CB3EA1B914724896FA91EDF42B813E51A8D3509DEAFB05A5F5ABD086BA2D`
na conferência final; a versão anterior permanece ativa até aplicação do novo
pacote. O instalador mantém versão 0.1.0 e bloqueia outro candidato de mesma
versão: é necessário remover apenas o Manager anterior antes de instalar este
MSI, ou preparar release própria com incremento de versão. Não remover os
pacotes Broker/Client/Admin para atualizar somente o Manager.

Os fluxos UAC/polkit reais, GVfs admin, boot/login, Wayland, DPI e upgrade/rollback
precisam de aceite em desktop apropriado. GTK isolado emitiu avisos de ausência
do barramento de acessibilidade, depreciação do AppIndicator3 e Glycin sem
sandbox no container root; o smoke concluiu sem erro. Não houve instalação no
host, alterações de ACL/serviços reais, leitura de dados privados para testes,
commit, push, tag ou publicação.
