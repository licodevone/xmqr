# P243 - Instalacao Windows visivel e descoberta pelo menu Iniciar

Versao 1.4 - 2026-10-21. Pedido: investigar instalacao que pede UAC, termina
sem assistente/conclusao e nao deixa aplicativo encontravel no Windows.

Revisao 1.1: gate detectou falta de Get-FileHash no WindowsPowerShell5 desta
sessao (modulos/ambiente herdados), consulta de tabela Shortcut inexistente nos
MSIs de componente e Control_First incorreto no ErrorDialog compilado. Usar
SHA256 .NET no coordenador; corrigir auditoria para tabelas opcionais e tornar
ErrorText primeiro controle como exige o protocolo de erro MSI. Recompilar os
MSIs alterados e verificar novamente; nao chamar esquema de UI executada.

Revisao 1.2: usuario perguntou sobre raiz C e pediu solicitacao de atalhos.
Manter ProgramFiles/XMQR para programas e ProgramData/XMQR para dados (nao
aplicar ACL privada a raiz C). Incluir opcoes no assistente para atalhos no
menu Iniciar (padrao) e Area de Trabalho (opt-in). Alias broker/client/admin
abre o manager existente, sem iniciar servico automaticamente, apenas quando
manager instalado; nunca criar atalho quebrado para componente ausente.
Coordenador instala manager antes dos componentes. Registros/atalhos sao por
maquina; manter inicializacao normal da bandeja por HKLM Run.

Revisao 1.3: usuario solicitou checkbox de aceite e texto abrivel. Criar termos
pt-BR em TXT/RTF, preservando integralmente a MIT real do repositorio e direitos
de dependencias, sem inventar CNPJ, foro, privacidade ou restricoes comerciais.
Informar limites experimentais e diretorios/provisionamento. Botao Ler termos
abre dialogo rolavel antes de instalar; checkbox desmarcado inicialmente e
botao Instalar bloqueado enquanto nao aceito. Aceite explicito obrigatorio
tambem para modo passivo/silencioso; remover/reparar instalacao existente nao
deve ficar preso por aceite anterior ausente. Incluir termos e licencas no
pacote, auditar propriedades/controles/rotas de aceite nos MSIs compilados.

Revisao 1.4: teste buscava Property de aceite no fragmento UI em vez dos dois
Packages; corrigir a localizacao do teste. Explicitar DisableCondition inversa
de EnableCondition para que desmarcar o aceite desabilite visualmente Instalar.
Comparar propriedades de atalhos explicitamente a "1", evitando confundir
valor textual "0" com escolha marcada. Auditar essas condicoes no MSI final.

Entrada: P242 tem quatro MSIs compilados, sem Dialog/UI/Shortcuts; coordenador
usa /passive e Start-Process Hidden. Manager MSI registra Run para proximo login;
broker/client/admin sao servicos e MSI individual nao inclui o manager.
Sessao leu Test-Path=false para ProgramFiles/XMQR e chaves padrao manager,
componentes/servicos. SCM access denied: nao afirmar inventario SCM completo.
Nao inferir que a tentativa do usuario concluiu com sucesso pelo UAC.

Objetivo: corrigir o pacote autorizado para assistente de instalacao/conclusao,
entrada pesquisavel XMQR Manager, orientacao de servicos, log MSI e resumo claro
de sucesso/cancelamento/erro no coordenador. Oferecer launcher de duplo clique
para o pacote completo, com janela persistente/erro visivel.

Escopo: packaging/windows/Manager.wxs, Product.wxs, UI compartilhada, README;
scripts/install-windows.ps1, build-windows.ps1, launcher cmd e verificacoes
de empacotamento. Registro P243, evidencia JSON, MSIs/ZIP novos sem sobrescrever
o candidato P242. Reutilizar fontes/bins exatos atuais, sem alterar Rust,
versoes/locks, protocolo, credenciais ou politica ACL. Sem commit/push/tag.

Requisitos: UAC apenas nas instalacoes necessarias; interface com Instalar e
Concluir, erros/cancelamento distinguiveis de sucesso. Logs sem incluir senhas
ou conteudo de configuracoes. Atalho no menu Iniciar de todos os usuarios para
manager instalado; componentes sao servicos, nao inventar GUI de broker/client.
Nenhum servico inicia antes do provisionamento. Nao executar tray elevado.
Nada de Win32_Product (provoca reparos), instalacao/reparo/desinstalacao no host
ou alteracao em HKLM por investigacao. Respeitar gatilho de versao duplicada;
nao remover dados existentes para contornar erro.

Aceite: testes XML/PowerShell/WiX com tabelas reais Shortcut/Dialog/ControlEvent
geradas; logs/resultados do coordenador verificaveis sem instalar (fixture
mock ou contratos estaticos proporcionais); build de todos os MSIs, hashes e
ZIP validos. Instalar/exercitar assistente e menu real exige ambiente elevado
autorizado; registrar NOT_RUN se indisponivel, sem chamar schema de aceite UI.

Agente de empacotamento: WiX UI/Shortcuts. Principal: coordenador/build/testes,
diagnostico local somente leitura, docs e entrega. Prompt autoriza executar
essas correcoes reversiveis no escopo ja solicitado.
