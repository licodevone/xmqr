# P260 — preparação Oracle e instalação pendente

Data: 2026-11-02, America/Sao_Paulo. Prompt: [P260 v1.0](../broker/260-oracle-instance-install.md).

## Entrada preservada

Broker HEAD 7c7a989, client a6d36f7 e admin 28fea43. Broker já tinha
docs/chat/2026-10-25.md modificado e arquivos não rastreados de chat,
guia 0.43.0/P259 e P257. Admin tinha README/assets/src modificados e
arquivos A29 de perfis não rastreados. Não foram revertidos ou publicados.

## Resultados observados

- PASS: sessão Oracle conectada, conta Free Trial, São Paulo home region.
- PASS: instância antiga instance-xmqr aparece Terminated; não foi alterada.
- PASS: formulário novo preparado até Review com nome `xmqr`, Ubuntu26.04
  2026.10.27-0, VM.Standard.E2.1.Micro, 1GB e rede/subnet existentes.
- PASS: disco padrão exibido 46,6GB, criptografia em trânsito habilitada.
- PASS: geração de chave pelo console e download da privada local concluído;
  somente existência/tamanho foram consultados. Conteúdo privado não foi lido
  nem registrado. Ainda não foi cadastrado acesso em uma VM criada.
- PASS: estimativa lida duas vezes: boot volume e total R$10,45/mês.
- BLOCKED: inventário de volumes não carregou pela navegação interna nem
  por URL observada. Não comprovado saldo dos 200GB Always Free.
- BLOCKED: consulta remota dos anexos GitHub pelo shell falhou antes do
  download, com DNS indisponível. Hashes publicados foram consultados na
  documentação local; não se declara conferência remota nova.
- WAITING_CONFIRMATION: Create cadastra acesso SSH persistente e pode gerar
  custo exibido. Política de controle do navegador exige confirmação no
  momento da criação desse acesso. Formulário preservado para continuação.
- NOT_RUN: criação, boot, SSH, download/verificação real dos pacotes, apt,
  configuração/ativação de serviços, firewall, mTLS e probes MQTT/admin.

## Documentação e validação

Criados prompt, este registro, [estado da implantação](../../docs/oracle-instance.md)
e histórico diário do chat. Links locais e diff-check verificados ao encerrar.
Sem mudança Rust; gates Cargo não aplicáveis a esta preparação documental.
Sem commit/push/tag, instalação Windows, remoção de volumes ou atualização de conta.
Não anunciar instância Running nem sistemas instalados neste checkpoint.

Se a criação falhar ou o operador limitar a custo zero, registrar o fato e
revisar o prompt antes de qualquer alternativa. Não trocar automaticamente
por plano pago nem expandir escopo.

## Continuação autorizada — 2026-11-02

Usuário perguntou se o plano é free e determinou prosseguir/finalizar.
O banner lido no turno anterior identifica Free Tier / Free Trial; nenhuma
atualização de conta ou assinatura paga foi solicitada ou executada.
Submissão efetiva de Create no formulário preparado retornou **FAIL:
Out of capacity for shape VM.Standard.E2.1.Micro in AD-1**. Não houve
confirmação de criação, OCID novo ou IP. O fault domain já estava automático.
Revisão P260 v1.1 precede a seleção alternativa A1 Always Free 2OCPU/12GB,
sem extrapolar autorização de custo nem usar pacote amd64 em ARM.

## Restrição explícita de arquitetura

Antes de selecionar uma forma alternativa, usuário determinou `não utilize arm`.
P260 v1.2 revoga o fallback. O diálogo de formas foi cancelado; a árvore
confirma E2.1.Micro/Ubuntu26 amd64 preservados. Nenhuma seleção ARM foi aplicada
ou submetida. Não houve segunda tentativa de criação, troca por forma paga,
assinatura, upgrade ou repetição automática. O bloqueio atual é capacidade
x86 Always Free no único AD-1, com fault domain já automático.

Um patch documental inicial v1.2 falhou por contexto ausente e não alterou
arquivos; foi reaplicado com o contexto correto antes de encerrar.
As marcações WAITING_CONFIRMATION/NOT_RUN de criação acima são históricas:
confirmação recebida, criação tentada e FAIL de capacidade, instalação NOT_RUN.

## Nova tentativa explícita — P260 v1.3

Usuário reiterou `prossiga com a criação da instância`. Após revisão do prompt,
confirmados nome xmqr, Ubuntu26 e E2.1.Micro; nova submissão enviada uma vez.
Retorno inicial: In Progress. Depois o indicador sumiu, sem novo erro visível,
sem URL de instância/OCID/IP e sem confirmação de Running. Usuário reportou
criação em andamento e autorizou solicitar sua ajuda quando necessário.

Status **UNKNOWN/PENDING**, não PASS nem novo FAIL de capacidade comprovado.
Lista de instâncias aberta separadamente para detectar eventual criação
antes de repetir a operação. Conteúdo principal não carregou, mesmo após
um reload apenas dessa lista. Formulário original preservado e sem reload.
Pedir conferência manual do operador; não repetir Create com resultado incerto.
Instalação e probes continuam NOT_RUN. Nenhum ARM/plano pago/upgrade aplicado.

Um patch documental de status falhou por contexto ausente sem alterar o arquivo;
foi reaplicado com contexto correto. Nenhuma falha documental alterou a VM.

Conferência final do inventário: AX contém apenas cabeçalho/rodapé e captura
visual confirma área central branca, sem dados de instâncias. Ambas as abas
foram preservadas para auxílio do operador. Pedido final: atualizar apenas
a lista e informar estado/IP público se xmqr existir. Não se pediu segredo,
nova autorização já concedida ou atualização de plano. Resultado segue
desconhecido; nenhum serviço XMQR foi instalado nesta etapa.

## Criação informada pelo usuário e interrupção de controle

Usuário informou ter criado a instância e forneceu URL com novo OCID terminado
em `kplsfp6sca`, aba de work-requests em São Paulo. O inventário do navegador
listou essa URL na aba existente. Tentativas de seleção por ID e pela URL
retornaram aba indisponível, sem leitura de estado/IP/arquitetura da VM.

Fallback pela janela Oracle no Windows foi interrompido pela própria ferramenta:
ela não conseguiu determinar a URL atual com confiança suficiente para aplicar
suas regras de segurança e determinou encerrar Computer Use neste turno.
Não houve tentativa de contornar a interrupção, obter sessão por outra via
ou executar comandos remotos. Continuação solicitada ao usuário: IP público
e confirmação do uso da chave já baixada. Não solicitado conteúdo privado.

Criação é informação do usuário, não PASS de validação remota. SSH, arquitetura,
imagem, Running, instalação e testes permanecem sem verificação/NOT_RUN.

## SSH ao IP informado e instruções ao operador — v1.4

IP 163.176.255.19 fornecido pelo usuário. Confirmada existência da chave privada
Downloads/ssh-key-2026-11-03.key, 1675 bytes; conteúdo não lido nem exibido.
Uma tentativa de conexão SSH com ubuntu, BatchMode/IdentitiesOnly, prazo12s e
accept-new (pin de host novo; chave alterada recusada) retornou exit255:
`ssh: connect to host 163.176.255.19 port 22: Permission denied`.
Falha na conexão, anterior à autenticação; sem teste efetivo de correspondência
da chave, sem saída remota e sem instalação. Não atribuir o erro a senha,
chave ou firewall Oracle sem evidência. Nenhuma tentativa por outro runtime.

Usuário então solicitou passo a passo SSH e localização das chaves. Listagem
restrita a nomes ssh-key em Downloads encontrou somente o arquivo .key acima.
Instruções conferidas nas fontes Oracle (Connecting to a Linux Instance),
Microsoft Learn (Windows Terminal SSH) e documentação Win32 OpenSSH via
Context7. Fornecido comando manual e pedido de whoami/uname/os-release.
Não houve cópia de chave, mudança de DACL, desligamento de verificação de
host, abertura de porta, script instalador ou instalação de pacote.

Fontes:
- https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/connect-to-linux-instance.htm
- https://learn.microsoft.com/en-us/windows/terminal/tutorials/ssh
- https://github.com/PowerShell/Win32-OpenSSH/wiki/ssh.exe-examples

## Chave no perfil Windows

Usuário informou ter colocado a chave no perfil. Inspeção de nomes/metadados
confirmou C:/Users/licod/ssh-key-2026-11-03.key, 1675 bytes. A cópia anterior
em Downloads continua presente. Nenhum conteúdo de chave foi lido, copiado,
exibido ou comparado. Fornecido comando PowerShell com USERPROFILE e destino
ubuntu@163.176.255.19, seguido de diagnóstico manual de arquitetura/imagem.
Não houve nova conexão remota nem alteração de permissões/serviços.

## Alvo confirmado pelo operador e instalador manual — v1.5/v1.6

Usuário forneceu saída `ubuntu@xmqr`, arquitetura x86_64 e Ubuntu26.04.1LTS
(VERSION_ID26.04), e pediu passo a passo para executar. Isso comprova acesso
na sessão do operador, não execução remota do agente. Instalação segue pendente.

P260v1.5 apresentado antes de criar scripts/install_oracle_x86.sh e
docs/oracle-install-manual.md. v1.6 precede os ajustes de validação/porta.
Script restrito a instalação nova Ubuntu26amd64; hashes/nome/versão/arquitetura
dos três .deb, usuários separados, CA privada, SANIP/loopback/localhost/xmqr,
senha randômica Argon2id19456/2/1, fingerprint, ACL só xmqr/health, tokenprivado,
serviços systemd, monitor9090/admin19080 loopback e testes finitos de runtime.
Falha preserva arquivos e desativa serviços novos, sem apagar estado nem
modificar firewall/SSH/VCN. Folhas365dias/CA3650dias; renovação documentada.

API GitHub: três releases públicas não draft consultadas pelo conector.
Anexos .deb, tamanhos/digests/URLs conferidos; hashes coincidem com o guia
local. Não houve download binário pela API nem nova afirmação de homologação:
broker c2341ab3..., client e4d09cec..., admin fe03ffc8.... Pacotes completos
serão baixados e verificados na VPS quando o operador executar o script.

Validação local:
- BLOCKED: GitBash `bash -n` não iniciou; erro de IPC NtCreateDirectoryObject
  0xC0000022, exit-1073741502, antes da análise. --plan também não executado.
- Não se tentou outro runtime para contornar essa restrição. Parsers Bash
  adicionais e argon2 não estão instalados no Python local consultado.
- PASS: compilação sintática dos três trechos Python embutidos pela stdlib.
- PASS: revisão das flags/unidades/Argon2 contra fontes das tags publicadas;
  perfil exato Argon2 conferido, docs argon2-cffi consultadas via Context7.
- PASS: links locais/whitespace, arquivo script LF, sem credenciais reais.
- NOT_RUN: sudo/APT/PKI/systemd/MQTT/admin e Bash na VPS; são etapas explícitas
  do operador. Guia exige bash-n remoto antes de sudo e marcador final
  XMQR_INSTALL_PASS; ausência do marcador não é aceite.

Mantidos todos os arquivos preexistentes; sem mudanças Rust, Cargo, manifests,
versões, tags, commit/push/release ou serviços do Windows.

## Falha real reportada na VPS — antes da correção v1.7

Operador executou etapa2. Mensagens needrestart informam kernel atualizado
e nenhum serviço/container/sessão a reiniciar; não são a falha. Script retornou
`ERRO: Versao inesperada da bridge.` e `Falha na etapa install-packages.`
O script só chega a essa comparação após apt instalar os três pacotes e
passarem as comparações broker/client. PKI, credenciais, units customizadas
e smoke tests não foram alcançados; broker foi parado/desabilitado pelo trap.

Falha do instalador: expectativa incompleta `mqtt-bridge 0.5.0`.
Fonte exata clientv0.43.0:src/bin/mqtt-bridge.rs imprime
`mqtt-bridge 0.5.0 (xmqr-client 0.43.0)`. Não é evidência de pacote errado.
Prompt v1.7 revisado antes da correção e da retomada. A saída efetiva do
executável na VPS ainda será validada na retomada, não foi lida pelo agente.

## Correção local e retomada v1.7 preparada

Comparação corrigida para a saída completa da bridge e exemplo do guia
atualizado. Conferidas também as saídas dos outros três executáveis nas
fontes das tags: broker043, client043 e admin011 coincidem com as comparações.
Adicionado --resume-packages: checkpoint/status privados, pacotes exatos e
dpkg-V limpo, hashes dos .deb cacheados, configuração/PKI ausentes, diretórios
de estado vazios, portas livres e nenhuma conta do observador preexistente.
Reserva atômica de diretório próprio impede retomadas concorrentes/repetidas;
status anterior é copiado com modo/proprietário preservados. APT/download
não são executados nesse modo. Nenhum dado/credencial é apagado.

Validação local: trechos Python compilam; revisão de fluxo/guardas e links,
diff-check PASS. Bash local e execução remota continuam BLOCKED/NOT_RUN;
comando do operador inclui bash-n antes de sudo. Nenhuma instalação remota
ou smoke test foi repetido pelo agente. Aceite depende do retorno da VPS.

## Nova falha reportada — mqtt-smoke, antes da correção v1.8

Operador enviou final da ajuda WS/WSS do client e falha em mqtt-smoke.
Trecho sem a primeira linha de erro; não inferir problema de transporte
WebSocket apenas pelo final da ajuda completa. Etapas PKI/configuração e
readiness precedem mqtt-smoke e foram ultrapassadas pelo fluxo do script.
Serviços novos foram parados/desabilitados pelo trap; arquivos preservados.

Defeito encontrado no script: ID p260-valid-after-negative tem25 caracteres,
mas cli.rs da tag v0.43.0 limita MQTT3.1.1 a23. Demais quatro IDs do smoke
têm14/14/18/12. Isso causa rejeição de argumentos nesse comando; associar
esse defeito ao trecho do operador é inferência até obter a primeira linha.
Promptv1.8 precede correção e retomada limitada a testes, sem regenerar segredos.
