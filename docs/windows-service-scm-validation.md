# P239 — ensaio SCM preparado, ainda não executado

Artefatos: os três executáveis debug comprovados em
[p239-windows-service-proof-20261021.json](results/p239-windows-service-proof-20261021.json).
As versões são broker/client 0.43.0 e admin 0.11.0. A bandeja é o XMQR Manager
de tools/windows-manager, cujo backend de controle é também usado por --control.

## Pré-condição e escopo da autorização

Preferir VM Windows descartável. Neste host não foram encontrados Hyper-V ou
Windows Sandbox. O [prompt P239](../prompts/broker/239-windows-services-tray.md)
exclui instalação no host; portanto, a execução aqui exige autorização explícita
para registrar temporariamente serviços e inventário HKLM e aplicar ACL somente
à pasta dedicada do ensaio. Nenhuma dessas ações foi feita nesta etapa.

O ensaio usa **os três produtos reais**, com os hashes comprovados. Seu objetivo
possível nesta revisão é confirmar a propagação de falha de inicialização até
SCM e gerenciador. Os negativos já executados demonstraram que broker e admin
ainda recusam persistência/token Windows. Não há expectativa de três serviços
operacionais ou de PASS global de start/stop/restart nessa configuração.

## Ações concretas do ensaio negativo

1. Consultar novamente o SCM e HKLM 64-bit. Abortar se existir qualquer um dos
   serviços xmqr-broker, xmqr-client-default, xmqr-admin ou seus registros de
   componente; não substituir uma instalação. Conferir hashes dos executáveis
   contra o relatório e obter o hash do gerenciador utilizado.
2. Criar pasta exclusiva identificada por execução sob ProgramData\XMQR-P239,
   contendo cópias dos executáveis, configurações sintéticas, estado e logs.
   Proteger a pasta contra escrita de usuários comuns. Usar a conta interna
   LocalService; permitir-lhe leitura dos binários/configuração e escrita apenas
   em estado/logs. Não usar LocalSystem, credenciais reais ou pastas do operador.
3. Registrar os três serviços de início manual, sem recovery automático, com
   executável/caminhos absolutos e --windows-service NAME LOG_DIR --config FILE.
   Broker: open-lab loopback e estado novo do ensaio. Admin: loopback e caminho
   de token próprio não provisionado. Client: configuração sem argumentos para
   provar recusa antes de iniciar rede. Registrar somente os três componentes
   correspondentes em HKLM\SOFTWARE\XMQR\Components.
4. Consultar xmqr-manager --diagnose antes do início. Executar, um por vez,
   xmqr-manager --control start broker, start client-default e start admin,
   capturando stdout/stderr e saída de cada processo com prazo. Registrar estado
   SCM e diagnóstico do manager após cada tentativa. Esperado: controle retorna
   falha, serviço termina Stopped com ExitCode não zero, categoria fixa de falha
   em service.log e gerenciador relata falha em vez de Running/verde.
5. Conferir identidade antes da limpeza. Remover apenas as definições SCM e
   chaves HKLM criadas pelo ensaio; nunca forçar parada de processo ou apagar
   instalações encontradas depois. Confirmar ausência final. Preservar logs e
   hashes na pasta de evidência, sem apagar recursivamente pastas do sistema.

O relatório deve incluir comandos, códigos, estados antes/depois, conta de
serviço, hashes, limpeza e qualquer timeout/falha. Erro de ACL, SCM ou registro
é FAIL/BLOCKED do ensaio, não a recusa esperada de persistência/token/configuração.

## O que ainda é necessário para operação

Para provar os três serviços funcionando, W2 exige persistência Windows com
durabilidade, exclusão de segundo writer e recuperação; W3 exige proteção
nativa de token/arquivos. O cliente também exige credenciais/saída apropriadas
para modos autenticados ou assinatura. Essas implementações não fazem parte
da correção documental nem da comprovação de build desta revisão.

Depois desses pré-requisitos, executar o ciclo real start → Running → stop →
Stopped → start → restart, probes funcionais e controle pela interface visual,
incluindo UAC, boot/login e instalação/upgrade/remoção em VM. O ensaio negativo
acima não substitui esses gates, nem muda W4/W5/W6 ou fase 9 para concluídos.
