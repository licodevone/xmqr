# P245 - Desinstalacao na pasta do programa

Prompt: [P245 v1.2](../broker/245-windows-uninstall-shortcuts.md).
Data: 21/10/2026, America/Sao_Paulo. Entrada HEAD
0fbe2dec3b8c6d4bb4da7f0a7180fba2498cdeed; arquivos P244/chat preservados.

## Alteracao

Product.wxs cria Desinstalar XMQR Broker/Client/Admin no INSTALLFOLDER do
respectivo MSI. Manager.wxs cria seu atalho auxiliar independente. Os atalhos
sao componentes MSI sempre incluidos, sem depender de Manager/menu/desktop,
nao permanentes e com chave HKLM por produto. Target e
`[System64Folder]msiexec.exe`, argumentos `/x [ProductCode] /norestart`.

InstallerUI.wxs mostra confirmacao especifica para REMOVE=ALL com Desinstalar
e Cancelar (padrao/Escape). Nessa operacao nao aparece o welcome de instalacao
nem os checkboxes de licenca/atalhos. O Windows Installer continua responsavel
por seu servico e arquivos. Nenhuma custom action ou exclusao manual foi
acrescentada; componentes/dados permanentes em ProgramData preservados.

Referencia consultada: [WiX Shortcut](https://docs.firegiant.com/wix/schema/wxs/shortcut/),
atributos Directory/Target/Arguments e propriedades formatadas. A validade dos
MSIs foi conferida com o compilador instalado, sem executar os instaladores.

## Validacao realizada

- `python scripts/verify_windows_packaging.py --wix`: 17/17 PASS, 9.812s.
  Compilacao de fixtures broker/client/admin/manager e auditoria somente leitura
  das tabelas MSI, incluindo novo fluxo de remocao e contrato dos atalhos.
- Verificador MSI ampliado para confirmar GUID de produto, target/argumentos,
  nome/pasta, inclusao na feature, independencia das escolhas e componente
  nao permanente. A regressao de aliases agora seleciona apenas os dois links
  do Manager, distinguindo a nova opcao de desinstalacao.
- `git -c core.safecrlf=false diff --check`: PASS.

Primeiro build completo: Manager e Broker compilaram, Client bloqueado com
Cargo 101 (cache global recusou gravacao de windows-permissions 0.2.4).
Prompt revisado antes da correcao. Cache dedicado target/p245-cargo-home
preparado com 630 arquivos publicos de cache para 379 pacotes dos locks,
preservando conteudo/cache global. Segunda geracao bloqueada em aws-lc-sys:
cl.exe falhou na compilacao nativa. Causa exata desse segundo erro nao foi
investigada neste incremento de MSI; nao corresponde a teste de servico.

Prompt revisado para v1.2 antes da alternativa: reempacotamento explicito
dos executaveis P243. Extracao por `wix msi decompile -x`, sem instalar.
Todos os checksums P243, MSIs de entrada e payloads executaveis conferidos
contra o manifesto anterior. Ferramenta intermediaria target/p245-repackage.py
recompilou somente authoring WiX/UI atual e preservou notices anteriores.
Manifesto final declara build_mode=installer-only-repackage-p243, origens e
hashes dos executaveis, commits/dirty originais e estado do empacotamento.
Nao e alegado um novo build Rust completo.

Auditoria somente leitura dos MSIs finais: Manager 68/68, Broker 71/71,
Client 71/71 e Admin 71/71 PASS (281 verificacoes). Logs em target/p245-audit.
Build/reempacotamento e empacotamento ZIP terminaram com codigo 0.
Os 1037 checksums de arquivos finais foram conferidos antes de fechar o ZIP.
Nenhuma instalacao/remocao executada no host.

## Entrega

`dist/windows/XMQR-Windows-P245-desinstalacao.zip`, 9.466.733 bytes.
SHA-256: `b200dcc1c4982c203d3af2668e11216151d90229526ac963f629b4ff464a0d87`.
Inclui tres produtos e o gerenciador auxiliar independente; versoes preservadas.
Salvamento persistente concluido: libfile_efa65c57086c8191b2259e85fdf29002,
file_000000008af0820eb40686a31e8b6a89, caminho
`/xmqr broker - client - admin/XMQR-Windows-P245-desinstalacao.zip`.
Helper local de xattrs tentou aplicar metadados, mas Python Windows nao fornece
os.setxattr; isso nao invalida o salvamento remoto ja concluido. Nao alegar
metadados estendidos locais aplicados.

## Limites

Este incremento e de empacotamento; nao altera codigo Rust ou corrige a falha
de inicializacao dos servicos relatada em P244. Instalacoes anteriores nao sao
modificadas pela geracao. A remocao real de MSI/SCM e preservacao efetiva de
dados permanecem NOT_RUN neste host, exigindo validacao administrativa isolada.
Nao ha bump de versao, commit, push, tag ou publicacao de release.
