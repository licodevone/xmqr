# Implantação Oracle — xmqr

Estado em 2026-11-02 (America/Sao_Paulo): **PACOTES INSTALADOS PELO OPERADOR; CONFIGURAÇÃO PENDENTE**.
Execução: [P260](../prompts/registros/P260-oracle-instance-install.md).

O operador confirmou sessão `ubuntu@xmqr`, `uname -m` = x86_64 e
Ubuntu26.04.1LTS, VERSION_ID26.04. IP informado:163.176.255.19.
O agente não conseguiu conectar por SSH (conexão negada antes da autenticação).
O [passo a passo](oracle-install-manual.md) e o
[instalador](../scripts/install_oracle_x86.sh) estão preparados para execução
explícita pelo operador. Não foram executados na VPS pelo agente.
Configuração desse instalador: broker mTLS8883, monitor loopback9090 e
admin loopback19080 com túnel SSH, além de cliente local de teste.
Os relatos de capacidade/resultado desconhecido abaixo são históricos.

Primeira execução manual parou em install-packages: a comparação da versão
da bridge estava incompleta no instalador. PKI/serviços/probes ainda não foram
alcançados. P260v1.7 corrige a comparação e prepara --resume-packages com
checagens de integridade/estado, sem apagar dados ou repetir a instalação APT.
Retomada ainda aguarda execução e resultado do operador.

| Item | Configuração preparada no console |
| --- | --- |
| Nome | xmqr |
| Região principal | Brazil East (São Paulo), sa-saopaulo-1, AD-1 |
| Imagem | Canonical Ubuntu 26.04, build 2026.10.27-0 |
| Forma | VM.Standard.E2.1.Micro, amd64, 1 GB RAM, Always Free-eligible |
| Disco | Tamanho padrão exibido de 46,6 GB; criptografia em trânsito habilitada |
| Rede existente | vcn-xmqr / subnet-xmqr, IPv4 público automático |
| Acesso | Chave SSH gerada; privada baixada localmente, não versionada |
| Estimativa exibida | R$ 10,45/mês, atribuídos ao boot volume |
| Software pretendido | broker/client 0.43.0, admin independente 0.11.0 |

O formulário foi submetido após a confirmação do operador. Oracle retornou
`Out of capacity for shape VM.Standard.E2.1.Micro in availability domain AD-1`.
Não existe IP novo confirmado nem instalação executada nesta operação.
A instância antiga instance-xmqr aparece Terminated; seus recursos não foram removidos.

O usuário excluiu ARM explicitamente. Nenhuma forma ARM foi aplicada ou
submetida; o seletor foi cancelado, mantendo E2.1.Micro/Ubuntu26 amd64.
Não foi criada instância paga nem atualizada a conta. O único AD disponível
é AD-1 e o fault domain já estava automático na requisição recusada.

## Custo e acesso pendentes

A documentação Oracle informa 200 GB combinados de volumes de boot e de
bloco gratuitos na região principal. A tela confirmou São Paulo como região
principal e conta Free Trial. A lista de volumes não carregou, mesmo após
navegação direta à URL exposta, impedindo comprovar a capacidade livre.
A estimativa não deve ser anunciada como cobrança efetiva nem como zero.

O operador confirmou prosseguir após o resumo de SSH/custo. Não atualizar a conta, contratar add-ons,
apagar volumes antigos ou mudar de forma para contornar falta de capacidade.

Fonte: https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm

## Instalação prevista após provisionar

1. Confirmar Running, arquitetura amd64, Ubuntu 26.04, IP e chave do host.
2. Conectar por SSH com verificação da chave do host; não usar verificação desativada.
3. Obter os três pacotes oficiais e conferir os hashes do
   [guia de releases](current-releases-wsl.md).
4. Instalar os pacotes, preparar certificados próprios com SAN correspondente
   ao endereço usado, bundle privado, senha própria e ACL mínima.
5. Configurar broker systemd com mTLS, monitor loopback e estado privado.
6. Configurar token e serviço do admin em loopback. Pacote 0.11.0 é observador;
   não inclui automaticamente console/contas web posteriores.
7. Validar readiness, pub/sub QoS1, retained após restart, autenticação
   inválida recusada e acesso ao painel por túnel SSH.

A tentativa de provisionamento falhou por capacidade. Instalação, regras de
rede e testes dependentes continuam NOT_RUN. Sem migração de estado,
alteração de versões ou release nova. A criação gratuita x86 depende de
capacidade Oracle; não converter automaticamente para forma paga ou ARM.

## Nova submissão solicitada pelo operador

P260 v1.3 precedeu uma nova submissão da mesma configuração E2.1.Micro,
autorizada pelo pedido `prossiga com a criação da instância`. O console
mostrou In Progress, depois retirou o indicador sem redirecionar para uma
VM, sem OCID/IP e sem apresentar novo erro legível. O usuário também
informou ver a criação em andamento. Isso não comprova Running.

Uma aba separada da lista de instâncias foi aberta para conferir resultado
antes de qualquer retry, mas seu conteúdo principal não carregou, inclusive
após um reload da lista. O formulário original não foi recarregado.
Não enviar outra criação enquanto o resultado desta estiver desconhecido.
Solicitar ao operador conferir na lista se xmqr está Provisioning/Running
e informar o IP público se disponível. Instalação continua pendente.
