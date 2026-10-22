# Instaladores Windows experimentais - P246

## Icones, atalhos e estado inicial

P246 usa a marca XMQR no Broker e os nomes Admin/Client/Manager grandes com
XMQR pequeno embaixo nos demais. Os icones identificam os executaveis, a
entrada em Aplicativos, menu Iniciar, desktop e desinstalacao. As duas opcoes
de atalhos agora comecam marcadas; o usuario pode desmarca-las no assistente.
Os atalhos dos componentes abrem o Manager da bandeja, onde ficam os controles
dos servicos instalados. Broker, Client e Admin sao servicos; o Manager e o
aplicativo de interface, nao um quarto servico Windows.

O codigo SCM1077 significa que nao houve tentativa de inicio desde o ultimo
boot. A bandeja agora mostra **Ainda nao iniciado**, sem classifica-lo como
falha de execucao. O MSI continua sem iniciar servicos ainda nao provisionados.
Configure arquivos privados/certificados/conexao antes de iniciar. Quando
solicitar Iniciar pela bandeja, permita o UAC e consulte o resultado.

Instalacoes existentes nao sao modificadas pela geracao de novos MSIs. Os
registros da instalacao anterior mostraram desktop desmarcado e atalhos de
menu presentes. A consulta administrativa de configs/status nesta sessao foi
negada: isso nao comprova falta de arquivos ou causa de inicializacao.

## Desinstalar pela pasta do programa

Cada novo MSI cria um atalho de desinstalacao na propria pasta do programa,
independentemente das opcoes de menu Iniciar/Area de Trabalho e da presenca
do Manager:

| Pasta padrao | Atalho |
| --- | --- |
| `C:\Program Files\XMQR\Broker` | Desinstalar XMQR Broker |
| `C:\Program Files\XMQR\Client` | Desinstalar XMQR Client |
| `C:\Program Files\XMQR\Admin` | Desinstalar XMQR Admin |
| `C:\Program Files\XMQR\Manager` | Desinstalar XMQR Manager (auxiliar) |

Abra o atalho, confirme **Desinstalar** e permita a elevacao do Windows se
solicitada. **Cancelar** encerra antes da remocao. O Windows Installer usa o
ProductCode daquele MSI para remover somente aquele produto, sem reinicio
automatico. O MSI para/remove o servico correspondente e os arquivos do
programa; configuracoes, certificados, logs e estado em ProgramData permanecem.
Remover um componente preserva o Manager; remover o Manager preserva os
componentes instalados, mas retira o gerenciador da bandeja.

Pacotes ja instalados nao recebem esse atalho automaticamente. Para eles,
continue usando **Configuracoes > Aplicativos > Aplicativos instalados** do
Windows. Um novo candidato da mesma versao exige remover o anterior antes de
instalar este, conforme a protecao existente; nao faca essa troca apenas para
diagnosticar servicos. Os pacotes anteriores e os dados nao sao alterados
pela geracao deste candidato.

Os arquivos deste diretório implementam empacotamento nativo. Não constituem
release aceita nem prova de instalação, persistência ou segurança no Windows.
P241 implementa armazenamento do broker no Windows com testes de recuperação
e MQTT nativos. Instalação e controle SCM ainda aguardam aceite elevado em VM;
veja o [registro P241](../../prompts/registros/P241-windows-broker-runtime.md).
O runtime nativo do admin passou prova de token/usuários privados e autenticação
web. O runtime nativo do client passou prova de senha/configuração privadas e
saída JSONL privada com limite. O aceite de MSI/SCM, boot/login, upgrade/reparo/
rollback e integração com a bandeja segue pendente em VM descartável.

## Componentes independentes

- `Product.wxs`: MSI parametrizado do broker, client ou admin. Cada pacote
  registra apenas seu executável, serviço e entrada da bandeja. O serviço usa
  `NT AUTHORITY\LocalService`, início automático e parada cooperativa. O MSI
  **não inicia o serviço**, pois configuração/credenciais precisam ser preparadas
  e os gates nativos ainda estão abertos.
- `Manager.wxs`: MSI separado do gerenciador `xmqr-manager.exe`. Uma entrada
  no menu Iniciar permite pesquisar **XMQR Manager**; HKLM Run inicia a bandeja
  no login normal do usuário. A remoção de um componente
  não remove o gerenciador dos demais. Sem componentes registrados, o gerenciador
  não mostra ícone. Sua remoção é explícita em Aplicativos do Windows.
- `install-windows.ps1`: instalação coordenada do gerenciador e dos componentes
  escolhidos. Verifica os SHA-256 antes de abrir o Windows Installer com UAC.
  Exibe os assistentes completos por padrão; `-Passive` é opt-in. Grava logs
  individuais e `result.json` em `%LOCALAPPDATA%\XMQR\InstallLogs\<execução>`.
  Sucesso, cancelamento e erro são resultados distintos. Confere registro e
  existência do executável após cada MSI antes de anunciar conclusão.
  Ao ser executado em sessão não elevada, abre a bandeja após instalar. Não
  encerra nem inicia os serviços. Se executado elevado, deixa a bandeja para o
  próximo login normal, evitando uma interface permanentemente privilegiada.
- `Instalar-XMQR.cmd`: após extrair o ZIP inteiro, duplo clique abre o coordenador
  para os componentes presentes no pacote. A janela permanece aberta no fim,
  inclusive em erro. Respeita a política local de scripts; se bloqueado, use os
  MSIs individualmente, começando pelo manager.
- `diagnose-windows.ps1`: inventário somente leitura de registros, executáveis,
  status consultável dos serviços e atalho do manager. Falha de consulta não
  significa serviço ausente. Não lê credenciais, inicia serviços nem usa
  `Win32_Product`, que pode disparar reparos.
- `provision_windows_service_file.ps1`: aplica ACL protegida a um único arquivo
  existente dentro da pasta dedicada de um client/admin instalado. Exige sessão
  elevada, recusa caminhos absolutos/traversal/reparse points e não lê nem exibe
  o conteúdo do arquivo. `-Writable` concede Modify ao serviço no arquivo;
  `-ParentWritable` faz o mesmo apenas na pasta imediata. Revise com `-WhatIf`
  antes de aplicar:

```powershell
./provision_windows_service_file.ps1 -Component client -RelativePath client.toml -WhatIf
./provision_windows_service_file.ps1 -Component client -RelativePath client.toml
./provision_windows_service_file.ps1 -Component client -RelativePath 'certificates\password' -WhatIf
./provision_windows_service_file.ps1 -Component client -RelativePath 'certificates\password'
./provision_windows_service_file.ps1 -Component client -RelativePath 'state\output.ndjson' -Writable -ParentWritable -WhatIf
./provision_windows_service_file.ps1 -Component client -RelativePath 'state\output.ndjson' -Writable -ParentWritable
./provision_windows_service_file.ps1 -Component admin -RelativePath 'state\token' -ParentWritable -WhatIf
./provision_windows_service_file.ps1 -Component admin -RelativePath 'state\token' -ParentWritable
./provision_windows_service_file.ps1 -Component admin -RelativePath 'state\users.json' -Writable -ParentWritable -WhatIf
./provision_windows_service_file.ps1 -Component admin -RelativePath 'state\users.json' -Writable -ParentWritable
```

Crie cada arquivo privado pela CLI do componente ou por um procedimento seguro
do operador. Execute o helper em PowerShell elevado; ele define Administrators
como proprietário e concede acesso somente a SYSTEM, Administrators e
LocalService. Para o estado do admin, `-ParentWritable` permite que LocalService
crie o banco, lock e arquivos temporários irmãos. O helper prepara caminho e
ACL, mas não prova uma execução SCM como LocalService; isso segue como gate em VM.

`-ParentWritable` tambem permite que LocalService crie, remova ou renomeie itens
irmaos nessa pasta, e a ACE herdavel se aplica a filhos criados depois; use-o
somente em uma pasta de estado dedicada. Arquivos irmaos existentes nao sao
reescritos recursivamente pelo helper.

## Build da fonte exata

Pré-requisitos: PowerShell 7 para o build, Rust MSVC x64 e ferramentas de linkagem,
WiX 7, Python 3.11+, acesso às
dependências dos manifests. Nenhum desses pré-requisitos é instalado pelo script.
Os executáveis de serviço usam os manifests independentes
`packaging/windows-service/Cargo.toml` de cada repositório. Os binários normais
da raiz não contêm o adaptador e nunca são usados como substitutos.

Quando houver acesso à rede, resolver uma vez e revisar/versionar os lockfiles:

```powershell
cargo generate-lockfile --manifest-path packaging/windows-service/Cargo.toml
cargo generate-lockfile --manifest-path ../xmqr-client/packaging/windows-service/Cargo.toml
cargo generate-lockfile --manifest-path ../xmqr-admin/packaging/windows-service/Cargo.toml
cargo generate-lockfile --manifest-path tools/windows-manager/Cargo.toml
```

Depois, a partir de `xmqr/`:

```powershell
./scripts/build-windows.ps1 -Components broker,client,admin
# Para compilar e empacotar somente a bandeja:
./scripts/build-windows.ps1 -ManagerOnly
```

O build sempre usa `--locked`, recompila a fonte corrente e para se faltar
lockfile ou se houver qualquer erro. Somente depois cria um diretório novo em
`dist/windows/candidate-*`, com MSIs, manifesto, executáveis identificados por
hash, commits/estado sujo, script de instalação e `SHA256SUMS.txt`. Não usa um
`.exe` antigo já presente em `target/`. Não assina, instala, publica nem cria tag.
Cada executável de serviço precisa também responder ao probe
`--windows-service-capabilities` com JSON schema 1, componente correto e
`service_entrypoint=true`; um build convencional é recusado antes de empacotar.
O build coleta os textos LICENSE/NOTICE das dependências resolvidas no cache
Cargo e os inclui em `notices/` dentro de cada MSI e também no diretório gerado.
Quando um archive omite o texto, o build só continua para pares exatos de crate,
versão e licença revisados; o caso MIT do `windows-permissions 0.2.4` usa o texto
canônico de permissão/isenção SPDX com hash fixado e conserva os manifests Cargo
originais como atribuição, sem inferir titular ou ano. Outros textos ausentes
continuam bloqueando o pacote; uma tabela de nomes de licença não é suficiente.
Hashes verificam integridade; não substituem assinatura/autenticidade.

## Instalação futura em VM descartável

Após resolver os bloqueios e validar os binários, a partir do pacote gerado:

Extraia o ZIP inteiro e abra `Instalar-XMQR.cmd`. Os assistentes oferecem
Instalar e Concluir, com uma opção marcada para criar atalhos no menu Iniciar
e outra, opcional, para a Área de Trabalho. Cada MSI também pode ser aberto por duplo clique.
O botão **Ler termos** abre o texto completo em uma janela rolável. Marque
**Li e aceito os termos de licença** para liberar a instalação; o aceite começa
desmarcado. O mesmo texto está em `TERMS.pt-BR.txt` e `TERMS.pt-BR.rtf` no pacote.
Ele reproduz a licença MIT original do projeto e explica as licenças de
terceiros, os diretórios, o provisionamento e o caráter experimental.
A janela final do coordenador informa a pasta dos logs e o aplicativo a pesquisar.
Broker/client/admin são serviços; a interface de controle é **XMQR Manager**,
e o painel web do admin é aberto pelo menu da bandeja após provisionamento.
Os atalhos de cada componente abrem esse gerenciador sem iniciar o serviço.
São criados apenas se o gerenciador já estiver instalado; por isso o coordenador
instala o manager primeiro. Instalar só um MSI de componente não instala o manager.

```powershell
./install-windows.ps1 -Components broker
# Ou selecione somente os softwares necessários:
./install-windows.ps1 -Components broker,client,admin
# Um pacote contendo somente a bandeja pode ser instalado assim:
./install-windows.ps1 -ManagerOnly
# Diagnóstico sem alterar o computador:
./diagnose-windows.ps1
# Somente após ler os termos, para instalação passiva explicitamente autorizada:
./install-windows.ps1 -Components broker -Passive -AcceptLicense
```

Cada MSI também pode ser instalado individualmente. **O MSI do broker sozinho
não instala nem inicia a bandeja**: use o script coordenado ou instale também
o MSI do gerenciador. O MSI do gerenciador configura o próximo login; o script
coordenado também o abre ao final quando executado sem elevação permanente.
Se a opção padrão for mantida, o menu Iniciar contém `XMQR > XMQR Manager`.
A conclusão do MSI não inicia um
serviço sem certificados/configuração. Se apenas o manager estiver instalado,
não há ícone até existir um componente registrado. Se o manager for instalado
sozinho por MSI, abra o atalho ou entre novamente no Windows.

O candidato anterior P242 não incluía assistente nem atalhos e o coordenador
usava `/passive`; pedir UAC não comprovava sucesso. P243 corrige esses pontos.
Se o novo candidato da mesma versão for recusado, consulte o log e Aplicativos
Instalados: o bloqueio de mesma versão continua intencional. A remoção normal
preserva dados, mas não remova pastas de configuração para tentar contorná-lo.

Em uma implantação silenciosa direta de MSI novo, o operador precisa informar
`XMQR_ACCEPT_LICENSE=1` explicitamente após ler os termos; sem isso, o pacote
recusa a instalação passiva/silenciosa. Manutenção/remoção de instalação existente
continua disponível. O aceite é uma escolha desta instalação e não altera as
permissões de uso concedidas pelas licenças distribuídas.
O instalador e o gerenciador são localizados pelo registro protegido HKLM 64-bit,
sem confiar em SystemRoot/ProgramFiles herdados do ambiente da sessão.

O diretório de dados fica restrito ao caminho dedicado padrão em ProgramData;
o MSI rejeita `DATADIR` diferente antes de aplicar permissões. Isso evita aplicar
uma DACL privada a uma raiz de disco ou pasta compartilhada. Caminhos de dados
personalizados ficam pendentes de validação nativa, incluindo reparse points.
O diretório padrão é lembrado em HKLM para upgrades.
O `INSTALLFOLDER` padrão é `Program Files\XMQR\Broker|Client|Admin|Manager`.
Não coloque binários/configuração em local gravável por usuários comuns.
Em um Windows instalado no C:, isso significa `C:\Program Files\XMQR` para
os programas e `C:\ProgramData\XMQR` para configurações, certificados, logs e
estado. A raiz `C:\` não é necessária para resolver descoberta ou permissão;
manter programas e dados separados permite conceder escrita apenas onde o
serviço precisa. Esta correção conserva esses diretórios conhecidos do Windows.
Outro candidato da mesma versão é recusado para evitar instalações duplicadas
com ProductCodes diferentes. Remova o candidato anterior antes de reinstalar;
os dados permanecem. Reparo/manutenção do mesmo pacote continuam disponíveis.

Arquivos padrão, relativos a `ProgramData\XMQR\<componente>`:

| Componente | ID | Serviço | Configuração |
| --- | --- | --- | --- |
| Broker | `broker` | `xmqr-broker` | `broker.toml` |
| Client | `client-default` | `xmqr-client-default` | `client.toml` |
| Admin | `admin` | `xmqr-admin` | `admin.toml` |

Cada instalação cria `certificates`, `logs` e `state`. O template inicial é
preservado em upgrade e remoção (`Permanent`/`NeverOverwrite`). Não são
distribuídos certificados, chaves, senha, token nem estado. O broker usa mTLS
loopback por padrão; o client permanece deliberadamente sem argumentos até
provisionamento. O admin mantém HTTP loopback autenticado.

Dados/configuração/certificados recebem DACL protegida: SYSTEM e Administrators
com acesso total; LocalService com leitura. Logs e estado permitem escrita de
LocalService. Nenhum acesso amplo a Everyone/Users é concedido. Abrir a pasta
de certificados poderá exigir credenciais administrativas. Uma conta de serviço
compartilhada é uma limitação desta primeira fatia; isolamento por SID de serviço
e acesso de operadores precisam de validação própria antes de produção.

Ao editar caminhos internos da configuração depois da instalação, atualize também
os atalhos registrados quando aplicável; não há inferência nem leitura de chaves
privadas pelo gerenciador. `PanelUrl` do admin aponta inicialmente para
`http://127.0.0.1:9080/`; ajuste-o se provisionar outra porta loopback.

## Contrato com a bandeja

Registro **HKLM 64-bit** `SOFTWARE\XMQR\Components\<id>`:

| Valor | Conteúdo |
| --- | --- |
| Kind | `broker`, `client` ou `admin` |
| DisplayName | Nome visível do componente |
| Executable | Caminho absoluto do executável instalado |
| ServiceName | Serviço deste componente |
| ConfigFile | Arquivo real instalado no diretório dedicado do componente |
| CertificatesDir | Diretório de certificados instalado |
| LogsDir | Diretório de logs instalado |
| PanelUrl | Somente admin; URL HTTP loopback |

A desinstalação para/remove apenas o serviço e o registro do componente; conserva
dados e a localização lembrada em `SOFTWARE\XMQR\Install\<id>`. Não há remoção
recursiva de dados. A bandeja detecta a remoção sem reinstalação.

## Validação

`python scripts/verify_windows_packaging.py` verifica os contratos estáticos.
`--wix` acrescenta compilação de MSIs **de fixture** em diretório temporário,
com arquivos de teste explícitos, sem instalar ou executar nenhum software.
Isso prova schema/linkagem WiX e não um pacote de produto pronto.


Para exercitar o ciclo SCM do broker, use uma VM Windows x64 descartavel limpa,
com uma sessao PowerShell 7 elevada e sem o servico/MSI do broker instalado.
O script exige o opt-in `-DisposableVmAcceptance`, confirma que o Windows se
identifica como VM, recusa `xmqr-broker` ou XMQR Broker MSI ja existentes, cria
uma instalacao de teste em diretorio temporario proprio, usa ACLs protegidas,
configura `NT AUTHORITY\LocalService`, verifica start/listener/stop/restart duas
vezes e remove somente o servico cuja imagem corresponde ao executavel copiado
para esse diretorio. O exemplo pressupoe que o build do broker ja foi concluido:

```powershell
./scripts/verify_windows_broker_scm.ps1 `
  -BrokerExecutable ./target/windows-msi/x86_64-pc-windows-msvc/release/mqtt-broker.exe `
  -DisposableVmAcceptance
```

O teste abre apenas `127.0.0.1` em porta efemera, no perfil temporario `open-lab`.
O relatorio e o log do servico ficam em um diretorio separado `xmqr-broker-scm-evidence-*`
sob `%TEMP%`. Se o SCM/servico nao puder ser encerrado e removido com seguranca,
o script preserva o diretorio de teste e termina com erro; nao encerra processos
a forca. Este teste valida o ciclo de servico com o executavel fornecido; ele
nao instala nem valida o MSI, boot/login, upgrade, rollback ou provisionamento
do certificado mTLS. Esses cenarios continuam exigindo aceitacao em VM.

Para validar somente o ciclo SCM do client ou do admin em uma VM descartavel,
use um executavel com marker valido e um TOML de teste absoluto previamente
provisionado. O runner recusa servico/MSI do componente ja existentes, exige
Windows x64 identificado como VM e PowerShell 7 elevado, registra o servico
como `NT AUTHORITY\LocalService`, verifica caminho/conta, executa dois ciclos
start/stop e remove apenas o servico e diretorio temporario desta execucao.
Ele nao instala MSI, nao altera o TOML fornecido e nao muda o broker externo.

```powershell
./scripts/verify_windows_component_scm.ps1 `
  -Component client `
  -Executable ./../xmqr-client/target/windows-msi/x86_64-pc-windows-msvc/release/mqtt-client.exe `
  -Config C:\ProgramData\XMQR\client-default\client.acceptance.toml `
  -DisposableVmAcceptance

./scripts/verify_windows_component_scm.ps1 `
  -Component admin `
  -Executable ./../xmqr-admin/target/windows-msi/x86_64-pc-windows-msvc/release/xmqr-admin.exe `
  -Config C:\ProgramData\XMQR\admin\admin.acceptance.toml `
  -AdminTokenFile C:\ProgramData\XMQR\admin\state\token `
  -AdminStatusUrl http://127.0.0.1:9080/api/status `
  -DisposableVmAcceptance
```

O TOML do client e seu diretório pai devem ter ACL privada. Ele deve iniciar uma
assinatura TLS/mTLS de longa duração apontada para um broker isolado provisionado
pelo operador. O arquivo de senha e o arquivo JSONL existente, junto com seus
diretórios privados, precisam permitir acesso apenas às identidades esperadas e
ao `LocalService` do serviço; nunca coloque o valor da senha em `arguments`.
O template instalado continua com
`arguments = []` e requer provisionamento antes de iniciar. O TOML do admin usa
`token_file = "state/token"` e `users_file = "state/users.json"`; ambos ficam
na pasta `state` protegida para a identidade do serviço. Inicialize o token
de um PowerShell elevado. Antes de registrar ou iniciar o serviço, normalize a
DACL protegida do token e de `state` para SYSTEM, Administrators e LocalService;
remova a ACE do operador criada pelo comando de inicialização. O serviço valida
proprietário e DACL. O token deve existir antes de iniciar o serviço. O runner
verifica `/api/status` com HTTP 401 sem
token e 200 com o token lido somente em memória; nao grava o valor em log ou
relatorio. Esses scripts validam registro/lifecycle em SCM, nao instalação MSI,
boot/login, ACL efetiva criada pelo MSI, upgrade/reparo/rollback ou integração
com o serviço de produção.

Aceite operacional pendente: instalação limpa em VM elevada, conta/ACL efetiva,
boot/login, parada/reinício, remoção de cada combinação de componentes, upgrade,
reparo, rollback e preservação de dados. A fase 9 permanece aberta.
