# P246 - Marca Windows, atalhos e SCM1077

21/10/2026, America/Sao_Paulo. Prompt [P246 v1.4](../broker/246-windows-brand-icons-and-diagnosis.md).
HEAD de entrada 0fbe2dec3b8c6d4bb4da7f0a7180fba2498cdeed; P244/P245/chat
locais preservados. Agentes separados: diagnostico/modelo, authoring MSI e
helper PE. Sem commit/push/tag/versao/instalacao/servico/ACL alterados no host.

## Evidencia atual e correcao de interpretacao

Imagem image(2).png inspecionada visualmente: menu dos tres componentes em
Falha, submenu Client exibe codigo1077. A imagem image(4).png foi lida e
confirma nomes XMQR em Servicos Windows. Microsoft define ERROR_SERVICE_NEVER_STARTED
1077 como nenhuma tentativa de inicio desde o ultimo boot:
https://learn.microsoft.com/en-us/windows/win32/debug/system-error-codes--1000-1299-

O codigo do Manager classificava todo Stopped + exitcode nao zero como Falha.
Logo, 1077 nao comprovava a falha de execucao que havia sido inferida em P244.
Nova State::NeverStarted exibe Ainda nao iniciado, cor cinza e Iniciar habilitado.
Running, pending, falha real, erros de consulta e mismatch continuam distintos.
Detalhe explica o codigo e a preparacao dos arquivos privados antes de iniciar.

Revisao somente leitura atual: todos os tres servicos e quatro executaveis
registrados; hashes instalados iguais aos P243. Quatro atalhos do menu Iniciar
presentes, nenhum XMQR no desktop publico. Ultimos logs Manager/Broker/Client/Admin
terminaram0 com START_MENU=1, DESKTOP=0 e aceite1. Nao foi encontrada falha
de CreateShortcuts: a opcao de desktop estava desmarcada. Consultas SCM e
configuracoes privadas continuam acesso negado5 neste token, sem elevacao nova.
Nao foi comprovada ausencia/conteudo dos arquivos privados.

## Marca e empacotamento

Logo do usuario materializado e inspecionado: broker.png e copia byte a byte
da imagem original. Variantes geradas via imagegen, nao redesenhadas por script.
Primeira chamada por caminho Windows recusada antes de executar; referencia da
conversa utilizada. Usuario pediu nomes grandes e XMQR menor embaixo: versao
final possui assinatura pequena, aproximadamente um quarto da largura.
Imagens anteriores substituidas nos assets finais; PNGs transparentes.

.NET converte os assets para nove quadros ICO16-256 e RGBA32 para a bandeja.
Manager usa a marca com indicador verde em execucao, cinza/apagado parado,
amarelo em transicao/misto e vermelho em falha/estado indisponivel.
Os quatro MSIs incorporam icones em atalhos/Aplicativos; desktop agora marcado
por padrao, ainda opcional. P245 Desinstalar preservado.

Novo helper de recursos cria somente copia PE64 nao assinada. Verifica bytes,
RVA/tamanhos/flags de codigo/dados e recursos nao-icon. Prova inicial recusou
deslocamento de .reloc: inspecao mostrou bytes integralmente identicos e so
RVA/tabela corrigidos pelo Windows. Prompt revisado antes de permitir apenas
esse caso nao executavel. ICO invalido/PE assinado sintetico recusados sem saida.

build-windows.ps1 agora aplica recursos em staging novo e registra hashes antes
e depois, mantendo o build fonte obrigatorio no fluxo normal. Para esta entrega:
Manager recompilado da fonte P246; tres servicos usam payloads P243 extraidos
dos MSIs conferidos, com somente recursos de icone atualizados. Codigo/dados
preservados, manifestos explicitos; nao alegar rebuild Rust dos tres servicos.
Origem, hashes, proofs e auditorias: target/p246-audit e manifesto do pacote.

## Verificacoes reais

- Modelo puro rustc:8/8 PASS; Cargo Manager nativo:11/11 PASS.
- fmt PASS. Clippy inicialmente recusou chunks_exact_to_as_chunks; prompt
  revisado, as_chunks_mut aplicado, Clippy all-targets -D warnings PASS.
- Manager release locked/offline Windows x64: PASS (4.73s apos compilacao incremental).
- Helper PE com ICO real: nove imagens/dez recursos por executavel, codigo
  preservado. Tres capabilities de servico e Manager --version: PASS.
- Empacotamento final:17/17 PASS (9.599s), quatro fixtures compiladas sem instalar.
- MSIs reais: Manager70/70, Broker73/73, Client73/73, Admin73/73 (289 PASS),
  incluindo Icon/ARPPRODUCTICON/todos os atalhos e nova opcao desktop.
- git -c core.safecrlf=false diff --check: PASS.
- Novo ZIP inclui PNG/ICO finais, instaladores, docs e diagnostico somente leitura
  com copias de templates para comparacao de hash. Nenhuma senha/chave privada.

## Entrega e limites

dist/windows/XMQR-Windows-P246-icones-atalhos.zip, 11.072.946 bytes,
1051 entradas em SHA256SUMS.
SHA256 72f48a76c2c2d61dad2a565ad49eb5d20c764d72dfaf724e525d6833b2d2fce8.
Salvamento concluido: libfile_b6eb98f3dcd481919a83aeaff596cdd6,
file_000000004e08820e9254066aba19df37. Metadados preservados/verificados no
Windows por ponte de xattrs para streams NTFS; helper original mantido intacto.

Instalacoes existentes nao modificadas. Mesmo numero de versao exige remover
candidato anterior por Aplicativos Windows antes do novo MSI; instaladores
configurados para preservar ProgramData. Inicio real/configuracao TLS/usuarios/
ACL/conexao/boot/upgrade/remocao em SCM continuam pendentes de validacao elevada.
Arquivo diagnostico/Diagnosticar-XMQR.cmd incluido para operador coletar metadados
sem controlar servicos ou revelar segredos. Nao confundir estado1077 corrigido
com aceite operacional dos servicos.

## Atualizacao apos tentativas do operador

Usuario enviou image(6)/image(7)/image(8), lidas pelos identificadores exatos:
Client/Admin/Broker mostram Erro1 Funcao incorreta ao tentar iniciar. Agora ha
evidencia de tentativa com falha real, posterior ao snapshot1077. Fonte dos
tres windows_service.rs confirma ServiceExitCode::Win32(1) generico em falha
de callback inicializacao/runtime. Nenhuma causa especifica comprovada ainda.
Nova consulta somente leitura dos hashes dos tres TOMLs e das ultimas linhas
permitidas de logs resultou UnauthorizedAccessException para todos. Nao foram
lidos segredos nem alterados servicos. Coletor administrativo P244 existente
foi indicado por comando absoluto; resultado do operador segue necessario.
