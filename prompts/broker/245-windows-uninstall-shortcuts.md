# P245 - Desinstalacao pela pasta do programa

Versao 1.2 - 21/10/2026, America/Sao_Paulo.

Revisao 1.2: nova compilacao parou em aws-lc-sys (erro nativo cl.exe), antes
de produzir um conjunto completo. Esta feature altera somente MSI/UI. Gerar
o candidato como reempacotamento explicito dos executaveis P243: extrair
payloads dos MSIs anteriores sem instalar, verificar SHA-256 de cada MSI e
executavel contra o manifesto P243, e reconstruir os quatro MSIs com authoring
P245. Preservar licencas e registrar origem/hash de cada executavel, commits
originais/dirty e modo de reempacotamento no novo manifesto. Nao alegar novo
build Rust nem reutilizar silenciosamente executaveis de target ou instalados.
Ferramenta intermediaria e extracao limitadas a target/p245; arquivos P243
somente lidos. Alteracao da fonte de runtime exige novo build fora deste escopo.

Revisao 1.1: a primeira geracao compilou Manager e Broker, mas parou no Client
com Cargo 101 porque o cache C:\Users\licod\.cargo recusou escrita de uma
dependencia. Usar CARGO_HOME gravavel dentro da arvore de projetos e caches
locais existentes quando disponiveis, preservando locks e sem mudar permissoes
globais. Reexecutar o build completo; nao substituir executaveis antigos nem
atribuir essa falha de build ao funcionamento dos servicos instalados.

## Entrada e autorizacao

Pedido: inserir opcao de desinstalar os softwares no diretorio instalado.
Repositorio responsavel: xmqr, empacotamento compartilhado dos tres produtos
e Manager auxiliar. HEAD 0fbe2dec3b8c6d4bb4da7f0a7180fba2498cdeed; preservar
chat e arquivos P244 ainda locais. O diagnostico dos servicos esta pendente;
este incremento nao o conclui nem altera instalacoes existentes no host.

## Objetivo e escopo

Criar atalho Desinstalar XMQR Broker/Client/Admin dentro do INSTALLFOLDER de
cada MSI e um equivalente independente para Manager. Usar msiexec do Windows
64-bit com /x do ProductCode exato e /norestart, sem script de exclusao,
custom action, dependencia do Manager ou remocao de outros produtos.
Exibir confirmacao de remocao com Desinstalar/Cancelar na UI completa, sem
tela de nova instalacao/licenca. Cancelar deve ser a opcao padrao.

Arquivos: packaging/windows/{Product,Manager,InstallerUI}.wxs, README;
verificadores de empacotamento/UI existentes, registro P245 e chat.
Gerar candidato experimental com authoring atual e binarios P243 conferidos;
sem instalar,
desinstalar, iniciar servicos, mudar ACLs, commit, push, tag ou versoes.

## Compatibilidade e migracao

MSI continua responsavel por parar/remover apenas seu servico, registros e
arquivos do programa. Configuracoes, certificados, logs e estado permanentes
em ProgramData continuam preservados. O atalho pertence ao MSI e e removido
com ele. Menu/desktop opcionais nao condicionam o atalho de desinstalacao.
Pacotes existentes nao ganham atalhos retroativamente; continua a regra que
exige remover candidato da mesma versao antes de instalar outro. Nao executar
essa migracao automaticamente nem alterar os pacotes anteriores.

## Aceite e validacao

- Build WiX para os quatro pacotes sem instalar; regressao de empacotamento.
- Auditoria somente leitura das tabelas MSI: diretorio, nome, target 64-bit,
  ProductCode, argumentos, componente/feature sem condicao nem Permanent.
- UI de remocao selecionada somente para REMOVE=ALL, com confirmacao e
  cancelamento; fluxo de instalacao/licenca existente preservado.
- Documentar execucoes reais, hashes e limites. Teste de remocao efetiva SCM
  permanece pendente de ambiente administrativo descartavel.
