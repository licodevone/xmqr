# P263 v1.1 - Manager no terminal Windows

Data2026-11-03. Pedido: versao terminal Windows para uso local posterior,
alem do Manager Terminal Linux P262. Broker HEAD7c7a989, Manager Windows
0.1.1 com helpers CLI existentes --diagnose/--control/--control-all e inventario
HKLM64. Alteracoes P262 e outras preexistentes preservadas. Sem alterar Rust,
MSI, bandeja, produtos instalados ou configuracoes reais.

## Escopo/objetivo

Adicionar PowerShell7 com menu status/start/stop/restart/logs, consulta somente
ao inventario do Manager original e controle delegado a seus helpers validados.
Arquivos: tools/windows-manager/terminal/XMQR-Terminal.ps1,
tools/windows-manager/terminal/Test-Terminal.ps1,
tools/windows-manager/terminal/build_zip.py,
docs/windows-terminal-manager.md, referencia no README Windows e registroP263.
Versao do frontend independente0.1.0-rc.1; nenhuma nova versao Cargo/release.

## Requisitos

Somente executavel original xmqr-manager.exe0.1.1 com SHA oficial conhecido
3c4e11e1ae9e67e7a01d632d84d6dbf69addda4a85e2202ae0bc12c1e7c5943e.
Descoberta por caminhos usuais e/ou caminho local explicito; nao buscar no PATH,
nao baixar/copiar automaticamente executavel. Wrapper nao relanca bandeja.
ProcessStartInfo com ArgumentList, sem shell, janela ou elevacao automatica;
timeouts finitos e erros genericos sem conteudo privado. Helpers reais releem
HKLM/SCM e validam nomes/ExecStart, sem force/kill nem permissao alterada.

Controle exige terminal ja administrativo. DryRun somente mostra a intencao do
helper apos validar snapshot e alvo. Lista somente instalados; CLI sem servico
nao recebe controle. Estado global incerto/transicao/ExecStart divergente
bloqueia all. Falha parcial nao e sucesso e exige reconsulta. Menus e comandos
validam action/id, sem PowerShell avaliado a partir de dados/configuracoes.
Logs: eventos SCM do Windows referentes aos componentes escolhidos, filtro
exato por XML Data, janela7dias e busca limitada1000eventos; mostrar ate100.
Nao ler arquivos de logs/payload/configuracoes privadas de broker/client.

## Aceite/validacao

Testes PowerShell com invocador/snapshot/privilegio simulados, incluindo
injecao, hash divergente, ausencia de helper, nao admin, CLI-only, unknown,
client ambiguo, dry-run sem controle, falha de helper e pos-condicao. Nunca
start/stop/restart nos servicos do usuario. Parser/Help/Version e ZIP
deterministico/checksums/allowlist reais. Status real somente leitura quando
ferramenta/IPC permitir; ausencia de runtime/permissao e BLOCKED.
Gates Rust NOT_APPLICABLE. Sem commit/push/tag/release/instalacao no host.

## Pedido concomitante: atualizar painel Oracle

Usuario perguntou como igualar o painel Oracle ao local. Conferir releases
atuais via GitHub; em2026-11-03 ultimo publicado e v0.11.0 tag4483a356 sem
A23/A24/A25. Explicar caminho seguro de nova distribuicao Linux, configuracao
Console/perfis mTLS e contas, preservando PKI/estado/loopback19080. Nao executar
upgrade de fonte dirtyA29 nem publicar release sem gates/permissao de escrita.

## Revisao v1.1 - primeiro teste e helper portatil verificado

Parser PowerShell PASS. Primeiro teste FAIL: snapshot retornava array como
objeto unico por `return ,array`, mas consumidores ja coletam @(...). Corrigir
enumeracao tanto em Get-XmqrSnapshot quanto Select-XmqrTargets e repetir suite.
Revisao identificou um build local do Manager com hash diferente do publicado;
nao aceitar esse build nem relaxar pin para executa-lo como administrador.

ZIP oficial anterior existe em dist/releases/p256-verify/windows; SHA481bbb...
e exe interno SHA3c4e... conferidos. Permitido incluir a copia portatil IMUTAVEL
desse helper no pacote novo, com todos os seus LICENSE/notices e proveniencia,
sem instalar/substituir a bandeja. Descobrir primeiro helper adjacente em
helper/xmqr-manager.exe e manter verificacao do SHA antes de invoca-lo.
Isso elimina dependencia de instalacao grafica para uso futuro do terminal.
Build do frontend inclui somente wrapper/docs/helper licenciado/checksums,
nao inclui MSI, estado ou arquivos privados. Reproduzir bytes do ZIP duas vezes.
