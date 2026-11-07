# P260 v1.8 — instância Oracle e instalação XMQR

Data: 2026-11-02, America/Sao_Paulo.

## Entrada e autorização

Pedido atual: criar uma instância na Oracle em sa-saopaulo-1 e instalar os
sistemas XMQR; nome corrigido explicitamente pelo usuário para `xmqr`.
Broker HEAD 7c7a989, versão local 0.43.0; client HEAD a6d36f7, 0.43.0;
admin HEAD 28fea43, 0.11.0, com alterações locais A29 não publicadas.
Preservar todos os arquivos modificados/não rastreados preexistentes.
AGENTS dos três projetos, plano de evolução, referências P87/P88/P228/A22,
guia current-releases-wsl e distribuição foram consultados.
O pedido autoriza provisionamento e instalação, sem commit/push/tag/release.

## Objetivo e escopo

Criar somente uma nova VM `xmqr`, Ubuntu 26.04 amd64, preferindo forma
VM.Standard.E2.1.Micro elegível ao Always Free. Reutilizar vcn-xmqr e
subnet-xmqr quando adequadas. Verificar orçamento, volumes existentes e
capacidade antes de submeter. Não remover recursos da instância encerrada.

Instalar pacotes publicados: broker/legado 0.43.0, client 0.43.0 e admin
independente 0.11.0. Não apresentar funcionalidades posteriores do HEAD
como presentes nesses pacotes. Conferir SHA-256 com registros de release.
Configurar serviços e testar no host novo, sem alterar serviços Windows.

Arquivos locais: este prompt, prompts/registros/P260-oracle-instance-install.md,
docs/oracle-instance.md e docs/chat/2026-11-02.md. Credenciais e estado reais
ficam fora das raízes Git e dos registros/documentação.

## Requisitos e migração

- Não assumir custo zero pela etiqueta da forma; conferir armazenamento e
  estimativa. Não autorizar atualização de conta nem custo recorrente extra.
- Respeitar confirmação da ferramenta de navegador para criar acesso SSH
  persistente/exposição pública; preparar resumo concreto antes de perguntar.
- Chaves/senhas/tokens privados não aparecem em chat, logs ou Git.
- Manter mTLS, SAN correto, senha, ACL deny-by-default e limites do projeto.
- Monitor e admin permanecem loopback; acesso web por túnel SSH.
- Nenhum laboratório aberto à internet. Somente tráfego TLS 8883, quando
  configurado e autorizado, e acesso administrativo SSH necessário.
- Instalação nova usa estado privado novo v16; não migrar dados existentes.
  Remover pacote não remove automaticamente estado/certificados.
- Admin 0.11.0 usa autenticação token e painel observador, sem alegar console
  MQTT/contas web das mudanças posteriores não publicadas.

## Aceite e validação

1. VM em Running, nome/região/imagem/arquitetura e IP conferidos.
2. SSH funcional com chave correspondente, sem desativar verificação de host.
3. Pacotes oficiais com os três SHA-256 do guia de releases conferidos;
   dpkg e comandos --version corretos; dependências resolvidas.
4. Broker pronto pelo monitor local; admin autenticado em loopback;
   pub/sub mTLS QoS1 real e recusa de credenciais inválidas comprovados.
5. Reinício dos serviços e retained testados com dados sintéticos próprios.
6. Registro diferencia PASS, FAIL, BLOCKED e NOT_RUN; falhas exigem revisão
   deste prompt antes de correção. Não anunciar instalação antes de executar.

Sem mudança Rust: gates de compilação não são necessários para instalar
pacotes publicados. Evidência de aceites antigos não substitui probes da VM.

## Revisão v1.1 — falta de capacidade AMD

O usuário confirmou prosseguir/finalizar após a apresentação do custo e SSH.
A submissão real retornou Out of capacity para E2.1.Micro no único AD-1.
Não houve VM criada nessa tentativa. Antes de corrigir, autoriza-se no escopo
do pedido a alternativa gratuita VM.Standard.A1.Flex, limitada a 2 OCPUs e
12 GB no total da conta, em São Paulo, com o mesmo nome, disco e chave.
Não escolher forma paga nem atualizar a conta. Esta revisão substitui a
proibição de trocar de forma apenas para essa alternativa Always Free.

Se a alternativa ARM tiver capacidade, não instalar pacotes amd64 nem
anunciar homologação arm64 anterior. Compilar as fontes de tags publicadas,
em cópias isoladas, com Cargo.lock, validar arquitetura/versões e executar
gates Rust e integrações proporcionais antes de iniciar a instalação.
Registrar a implantação ARM como experimental e distinguir os binários
novos dos artefatos oficiais amd64. Se também faltar capacidade, registrar
o bloqueio real e preservar o formulário; não repetir requisições em loop.

## Revisão v1.2 — ARM expressamente excluído

Durante a inspeção do seletor, antes de escolher/submeter qualquer forma ARM,
o usuário determinou: `não utilize arm`. Fica revogada a alternativa A1 da
revisão v1.1. Apenas x86_64 (AMD/Intel) está no escopo; preservar Ubuntu26
amd64 e os três pacotes publicados. A forma E2.1.Micro permaneceu selecionada,
e o seletor de alternativas foi cancelado. Não criar forma paga sem nova
autorização específica, nem repetir a requisição em loop. Falta de capacidade
Always Free no único AD disponível é bloqueio externo, não instalação concluída.

## Revisão v1.3 — nova tentativa solicitada

Usuário renovou o pedido: `prossiga com a criação da instância`.
Uma nova submissão da mesma configuração x86 E2.1.Micro/Ubuntu26 está
autorizada após conferir o formulário. Manter nome xmqr, chave, rede e
orçamento já apresentados; sem ARM, upgrade de conta ou forma paga.
Se houver novo erro de capacidade, registrar o retorno e preservar o
formulário, sem repetição em loop nem sucesso presumido. Se criar, aguardar
Running e seguir o aceite original de instalação e probes.

## Revisão v1.4 — IP informado e acesso SSH manual

Usuário informou IP público 163.176.255.19. Chave privada já baixada existe
em Downloads; não presumir correspondência com eventual novo par gerado
durante a criação manual. A tentativa SSH retornou connect port22 Permission
denied antes da autenticação; isso não comprova erro de chave ou firewall OCI.
Não contornar restrições do ambiente por outro runtime/terminal automatizado.
Usuário pediu passo a passo e localização da chave: fornecer comando manual
com usuário ubuntu somente para imagem Ubuntu, sem desativar verificação de
host; solicitar whoami, uname -m e os-release para verificar alvo antes de
instalar. Nenhuma alteração de chave, DACL, firewall ou versão autorizada
por consequência desse diagnóstico. A proposta de preparar instalador não
foi implementada; a próxima etapa depende do acesso e da imagem confirmados.

## Revisão v1.5 — instalador para execução manual autorizada

Usuário confirmou por saída da sessão Ubuntu x86_64/26.04.1 e pediu passo
a passo para executar a instalação. Preparar scripts/install_oracle_x86.sh
e docs/oracle-install-manual.md no broker, com instruções PowerShell/SCP,
execução explícita sudo pelo operador e verificações. Apresentar esta revisão
antes da implementação; não contornar bloqueio SSH do ambiente do agente.

O instalador só aceita implantação nova Ubuntu26 amd64/systemd. Recusa
configuração/estado/serviços preexistentes, sem apagar ou sobrescrever dados.
Baixa os três .deb oficiais e confere hashes fixados, confirmados também
na API GitHub neste atendimento. Instala dependências pelo APT oficial,
gera CA/folhas próprias para IP informado, chave/senha/token privados,
bundle mínimo e três serviços separados. Broker usa mTLS; monitor/admin
são loopback, painel por túnel SSH; não alterar firewall/VCN/SSH do host.
Cliente de teste só recebe tópico sintético xmqr/health; sem bridge automática.

Executar probes de readiness, pub/sub QoS1, retained após restart e recusa
de senha inválida quando o operador executar o script. Não marcar esse
aceite remoto como executado pelo agente. Falha para os serviços criados
nessa execução e preserva arquivos para diagnóstico; não reexecutar sobre
instalação parcial sem revisão. Testar sintaxe Bash e Python embutido local,
revisar permissões/flags/limites e documentar validação remota pendente.

## Revisão v1.6 — validação disponível e porta do observador

Bash Git local não iniciou por bloqueio de IPC/Access Denied, antes de
analisar o script. Não tentar outro runtime para contornar essa restrição.
Compilar sintaticamente os trechos Python com stdlib local; informar Bash
como BLOCKED e incluir `bash -n` na VPS antes da execução sudo.
Observador da VPS usará loopback19080 e túnel local19080, evitando conflito
com o admin Windows9080. Portas local/remota iguais preservam a validação
Host/Origin do admin publicado. Monitor permanece loopback9090 e TLS8883.
Assegurar travessia privada de /etc/xmqr-client pelo grupo do serviço.

## Revisão v1.7 — saída da bridge e retomada controlada

Operador executou o script: FAIL em install-packages, comparação da bridge.
Fonte da tag clientv0.43.0 confirma saída completa
`mqtt-bridge 0.5.0 (xmqr-client 0.43.0)`, diferente da comparação escrita no
instalador. Registrar a falha antes de corrigir; pacotes chegaram a instalar,
PKI/configuração/testes não foram alcançados. Não remover estado ou reinstalar
para ocultar esse erro. Corrigir expectativa e exemplo documental.

Adicionar opção explícita `--resume-packages IP`, somente para esse checkpoint
com status root0600 FAILED stage=install-packages exit=1 e diretório root0700.
Exigir pacotes nas versões exatas, dpkg-V limpo, .deb cache com SHA fixado,
estado MQTT vazio, ausência de PKI, credenciais, perfil/units novos e portas
livres. Preservar status anterior em arquivo novo; uma retomada falha não
autoriza repetição genérica. Não repetir APT/download na retomada; verificar
versões e seguir a partir da configuração ainda inexistente. Instalação nova
continua recusando arquivos/contas preexistentes. Nenhuma execução remota
pelo agente; fornecer nova cópia SCP e comando de retomada ao operador.

## Revisão v1.8 — limite de Client ID e retomada dos testes

Operador chegou a mqtt-smoke e enviou fim da ajuda CLI seguido de FAIL.
Primeira linha de erro não veio no trecho. Revisão da tag client043 mostra
limite23 ASCII para MQTT3.1.1; comando pós-negativo do instalador usava
`p260-valid-after-negative` (25). Corrigir para `p260-valid-after` (16) e
registrar distinção entre defeito comprovado no comando e diagnóstico
inferido do trecho parcial. Preservar PKI, senha, token, bundle e estado.

Adicionar `--resume-mqtt IP` apenas para checkpoint privado FAILED em
mqtt-smoke exit1/2, com pacotes/cache/versões verificados e configurações
privadas/units presentes. Validar bundle, cadeia/SAN dos certificados e
materiais por proprietário/modo, recusar symlinks e serviços ativos.
Reservar uma única retomada e preservar status anterior. Não executar APT,
download, geração de PKI/segredos, useradd ou gravação de configuração nesse
modo: reiniciar somente serviços existentes e repetir testes finitos.
Identificar comandos MQTT em mensagens de progresso e registrar stderr
dos testes em logs privados, sem imprimir senha/chaves/tokens. Saída de
ajuda em negativo não equivale a recusa autenticada. Sem aceite remoto
presumido. Se nova falha, pedir primeira linha/etapa e log de erro apropriado.
