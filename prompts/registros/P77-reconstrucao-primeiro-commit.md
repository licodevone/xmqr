# P77 — roteiro do zero ao primeiro commit XMQR

2026-10-12. Entrada HEAD90a46fa, sem alterações próprias prévias. Primeiro commit
f7efe357cdcd4a05e922a5fb205bd8757cdc5625: XMQR0.3.0,35 arquivos,6083 linhasRust,
broker/client/admin no mesmo pacote. Não existem prompts versionados nesse
primeiro registro; não atribuir sua autoria aos novos exercícios didáticos.

## Material criado

curso/reconstrucao-primeiro-commit/ROTEIRO.md: preparação/instalação opcional,
duas aulas iniciais, cinco seções e16 aulas ao todo, ordem de digitação por
arquivo, parâmetros/símbolos, compilação/checkpoints, laboratório Ubuntu/WSL
e git init/add/commit do aluno. BIBLIOTECAS.md detalha dependências, features,
responsabilidades e limites. Dez promptsR01..R10 criados antes dos snapshots.

R01 baseCargo/main de apresentação; R02manifest/lock histórico; R03persistência
e ator; R04auth/ACL; R05transporte; R06MQTT; R07main real; R08admin; R09client;
R10complemento documental/exemplo. Arquivos mantidos preservados; lib/main e
manifestos pedagógicos substituídos explicitamente nos diffs. R10 tem somente
os35 arquivos originais em codigo/, sem LICENSE adicional (incluído depois no
histórico). Primeiro commit novo tem SHA diferente, mas árvore de fontes igual.

Artefatos locais ../docs/curso-udemy/primeiro-commit:
indexHTML, roteiro/bibliotecas, dezZIPs cumulativos, índices/hashes/manifestos,
validações/logs, diff do ajusteClippy e primeiro-commit-curso-completo.zip.
HTML exibe6098 linhasRust (6083 originais +scaffolds/substituições iniciais) com
notas de leitura ao lado. Notas sintáticas assistidas não são auditoria semântica
humana integral de cada transição; aulas narram o funcionamento dos módulos.
Sidebar/tópicos/arquivos sincronizados, abrir/recolher todos, âncoras e busca
arquivo:linha. Não usadas analogias de escola ou conteúdo de preparação do professor.

## Validação real

- WindowsRust/Cargo1.98.1/MSVC: dez etapas, build/check20PASS; R01impressãoPASS.
- Ubuntu26WSL/RustCargo1.99: dez etapas, build/check20PASS; R01impressãoPASS.
- R10Linux: fmtPASS;52 testesPASS (37lib+4broker+11client); admin/doctest0testes.
- R10Clippy1.99 -Dwarnings: FAIL/exit101, assert_is_empty em mqtt/store.rs:305.
  Não é falha de build/check. Snapshot histórico preservado. Em cópia isolada
  adicional, debug_assert_eq!(remainder, []) passou fmt/test52/Clippy. Diff e
  resultados indicam ajuste para commit posterior, não código originalR10.
- Pub/subQoS0 open-lab PASS: portaLoopback57137, estado isolado fora da fonte,
  clientsub count1 e publisher próprios, payloadfictício 'Ola, XMQR!' recebido.
  Processos criados pelo teste encerrados somente pelos PIDs/grupos próprios.
- Git de ensaio em cópiasWindows/Linux: primeiro commit local criado, árvore
  03a0304b3d6e416139dadc96671433799eec588f igual ao histórico. Nenhuma configuração
  Git global/remota alterada; identidade p77@example.invalid apenas no ensaio.
- Fontes/checkpoints antes/depois dos comandos SHA-256PASS; R10blobsGitexatos.
- HTMLParser: código de cada tabela igual às fontes da respectiva etapa,
 6098 linhasRust presentes, IDs únicos, âncoras/links locais válidos;11ZIPsCRC PASS.
- Edgeheadless desktop/mobile390px: abrir/fechar sidebar e corpo sincronizados,
 abrir/recolher todos, busca src/main.rs:52 com1resultado, sem erroJS:PASS.
- git diff --checkPASS; não mudado código dos produtos/snapshotsP73/P74/P75/P76.

## Revisões e limites

P77rev2 antes do ensaio da correçãoClippy. R10promptrev2 inclui o resultado.
Rev3 moveu instruções de estado do aluno para fora do projeto: marcador de perfil
não seria totalmente ignorado pelo.gitignore original e poderia alterar a árvore
do primeiro commit. Ensaio já usava estado externo. --prepare preserva prompts
existentes para não sobrescrever revisões do professor.
Rev4 após duas tentativas de patch documental recusadas por contexto incorreto,
sem alterações; reaplicado somente no ponto real. Uma inspeção auxiliar Python
também teve erro de sintaxe em compreensão; nenhuma fonte alterada, inspeção
retomada por leitura direta dos resultados. Não confundidos com falha dos programas.

WSL emitiu aviso de chave automount.options desconhecida no.wslconfig do operador;
compilações/testes/pubsub prosseguiram. Configuração global não alterada.
Nenhuma ferramenta instalada, serviço systemd/firewall/certificado real tocado.
Não ensaiados TLS/mTLS/Mosquitto externo, energia, carga, MQTT5 ou operação plena
do broker Windows. Instalação e comandos de Git da aula são instruções ao aluno;
somente ensaios isolados foram executados. Nenhum repo de estudo publicado.

Commit/push do material autorizado na conversa. Sem nova versão/tag/release de
produto; a atualização cria o curso e seus exercícios, não altera XMQR0.11.2.
