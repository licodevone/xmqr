# P239 - serviço e bandeja Windows experimental

Prompt: [P239 v1.9](../broker/239-windows-services-tray.md), preparado/revisado
antes das respectivas alterações. Os resultados abaixo até a seção de
comprovação de 2026-10-21 preservam o histórico v1.0–v1.6.
Pedido: serviço Windows, ícone/menus dos componentes instalados, controles e
atalhos do broker. Paralelização autorizada explicitamente durante a execução.
Data de trabalho: 2026-10-20 America/Sao_Paulo; Windows nativo, Rust/Cargo
1.99.1, WiX 7.0.0, Python 3.13. Sem instalação ou alteração de serviço no host.

## Entrada e arquivos

Broker 0.43.0, HEAD 26dd7b6134396aeb7b0368e5a15cad881af7edd4, árvore limpa.
O Product.wxs inicial já havia sido commitado pelo usuário entre a análise
anterior e esta execução; foi evoluído, não substituído por outro projeto.
Client fbbf7af / 0.43.0 e admin 2b6f245 / 0.11.0 mantêm seus registros
[C150](../../../xmqr-client/prompts/registros/C150-windows-service.md) e
[A26](../../../xmqr-admin/prompts/registros/A26-windows-service.md).
Alteração preexistente do client em .serena/project.yml foi preservada.

Escopo implementado: src/main.rs, configuration.rs, windows_launch.rs e
windows_service.rs; manifest separado packaging/windows-service; gerenciador
independente tools/windows-manager; packaging/windows, scripts de build/
instalação/validação, documentação e este registro. Locks/manifests principais
não receberam a dependência indisponível; Cargo.toml raiz só reconhece o cfg
experimental. Sem versão, protocolo, formato durável ou core pin alterado.

## Resultados executados no broker

| Comando/checagem | Resultado real |
| --- | --- |
| cargo check --bin mqtt-broker, antes do isolamento | BLOCKED: DNS de index.crates.io indisponível; saída 1 |
| cargo check --offline --bin mqtt-broker, antes do isolamento | BLOCKED: windows-service ausente do cache; saída 1 |
| Primeiro cargo fmt --all -- --check | FAIL: formatação do código novo; corrigida por rustfmt após v1.1 |
| cargo fmt --all -- --check, final | PASS, saída 0 |
| cargo fmt --manifest-path packaging/windows-service/Cargo.toml -- --check | PASS, saída 0; não resolve/compila dependências |
| cargo check --offline --locked --bin mqtt-broker, raiz isolada | PASS, saída 0, avisos Windows em código existente |
| cargo test --offline --locked --bin mqtt-broker | PASS: 12 testes, incluindo 3 negativos/positivos dos argumentos de serviço |
| cargo test --offline --locked --lib configuration::tests | PASS: 10 testes, incluindo configuração explícita/relativos/erro sem segredo |
| cargo test --offline --locked | FAIL: biblioteca 129 PASS / 96 FAIL / 1 ignored, saída Cargo 101 |
| cargo clippy --locked --offline --all-targets -- -D warnings | FAIL: imports/deadcode Windows existentes em auth/dynamic, mqtt/router, mqtt/mod e persistence/faults |
| cargo build --offline --locked --bins | PASS, saída 0; são binários CLI, não adaptadores de serviço |
| CLI --version | PASS: mqtt-broker 0.43.0, saída 0 |
| CLI comum --windows-service-capabilities | PASS: recusado com saída 2; impede empacotar CLI como serviço |
| Inicialização nativa em estado temporário próprio, open-lab | Recusa esperada: saída 1, guarda Unix de fsync preservada |
| cargo check --offline --manifest-path packaging/windows-service/Cargo.toml --bin mqtt-broker | BLOCKED: windows-service ausente; sem lock ou binário experimental fabricado |
| CARGO_NET_OFFLINE=true python scripts/license_inventory.py --check | BLOCKED: r-efi 5.3.0 ausente no cache para metadata multiplataforma |
| git diff --check | PASS; avisos de conversão CRLF não são falha funcional |

As 96 falhas da suíte inteira contêm a mensagem preexistente `durable directory
fsync is supported on Unix targets only`. Não foram ocultadas nem convertidas
em testes ignorados. Logs locais em target/p239-tests.log e p239-build.log.
A execução completa parou na biblioteca; o binário foi testado separadamente.
O smoke usou target/p239-smoke e não acessou estado/credenciais do operador.
O WSL foi consultado na frente C150/A26 e retornou Wsl/E_ACCESSDENIED.

## Bandeja, empacotamento e revisão

O gerenciador usa dependências disponíveis localmente, com lock real gerado
offline. Windows SCM é consultado/controlado por scripts PowerShell fixos,
com dados em ambiente validado e prazo. Registro HKLM 64-bit somente leitura;
serviço/executável revalidados antes do controle. A UI não recebe privilégio
permanente. Não há shell composto a partir de caminhos/nomes arbitrários.

Gates do gerenciador: fmt, check, Clippy -D warnings e 9 testes PASS.
Os testes cobrem combinações de inventário, agregação de estados, validação de
caminhos/URL/ações, Unicode, prazo e consulta vazia. Consulta SCM real no sandbox
retornou estado desconhecido; a UI o trata como erro, não ausência. Isso não é
aceite de controle real/UAC. Revisões locais em
[P239-tray-revisions](../../tools/windows-manager/P239-tray-revisions.md).

Revisão em paralelo identificou e corrigiu IO no callback SCM, corrida entre
stop e Running, SystemRoot herdado usado pelo helper elevado e liberdade de
DATADIR combinada com ACL. O callback apenas sinaliza; logs usam categorias
fixas e mutex separado. A bandeja resolve diretório Windows por HKLM protegido.
Dados do MSI ficam na raiz dedicada, sem override arbitrário de ACL.

Primeiro WiX encontrou WIX0230 (Guid=* em componente de diretório), corrigido
após v1.2. Fixture Python em Temp do sandbox encontrou PermissionDenied; passou
a diretório próprio target após v1.4. Compilação de fixture não equivale a
instalação do produto. Build combinado recompilou a bandeja e parou na ausência
do lock experimental do broker; não criou MSI de serviço com binário antigo.

## Artefato experimental do gerenciador

Empacotamento final: 12/12 testes PASS, incluindo os manifests dos tres
servicos, parsing PowerShell, contratos de instalacao e compilacao de quatro
MSIs de fixture. O build ManagerOnly gerou o MSI real, sem instalar no host:

`dist/windows/p239-manager-final/xmqr-manager-0.1.0-windows-x64-experimental.msi`

Tamanho: 446464 bytes. SHA-256:
`b33d3f3c6cd467828737f86d2bcc64cdc270cc455a05aabb4a3927649d8e07e9`.
O pacote inclui licencas/notices de 79 dependencias; 150 entradas de checksums
foram verificadas. O diretorio final inclui manifest.json, SHA256SUMS.txt,
README.md e install-windows.ps1. O candidato anterior nao e o artefato final.

Diagnostico do gerenciador em inventario vazio: PASS, sem componentes e sem
erro. Isso nao valida controles reais de servicos, instalacao ou interface
visual. O MSI entregue instala apenas o gerenciador experimental; nao converte
executaveis CLI existentes em servicos nem registra componentes ausentes.

## Aceite e limites

Atualizacao de acesso em 2026-10-21: nova tentativa online conseguiu resolver
as dependencias e gerar packaging/windows-service/Cargo.lock. O cache padrao
do usuario recusou escrita (erro 5); CARGO_HOME em target/p239-cargo-home
permitiu baixar windows-service 0.8.1. O fetch geral foi interrompido apos
timeouts de downloads adicionais; o comando `cargo fetch --offline --locked
--target x86_64-pc-windows-msvc --manifest-path packaging/windows-service/Cargo.toml`
com esse CARGO_HOME terminou com saida 0. Portanto, o bloqueio de download do
broker para Windows x64 MSVC esta resolvido. Isso nao valida compilacao ou
execucao do adaptador. Get-Service recusou acesso ao SCM nesta sessao; nenhum
servico foi reiniciado e nao houve elevacao. Os bloqueios de acesso descritos
acima passam a ser historicos para esse alvo/cache; os demais limites de
aceite abaixo permanecem.

Entrega parcial de infraestrutura; W2/W3/W4/W5/W6 e fase 9 permanecem abertos.
Broker não inicia estado novo no Windows por proteção de durabilidade.
Admin mantém restrição de token/usuários Unix; client não oferece assinatura
de serviço que descarte stdout e mantém guarda de credenciais privadas.
Um ícone verde significa execução SCM confirmada, não conexão/prontidão MQTT.

Após a comprovação abaixo, faltam persistência/ACL nativas, VM elevada,
boot/login/UAC, instalação/upgrade/remoção, restart e recuperação real. Serviço
SHUTDOWN não comprova tempo suficiente para drenar estado durante reboot.
Logs service.log são de ciclo de vida; tracing operacional não foi redirecionado.
Não houve instalação de serviço, mudança de permissões, commit, push, tag ou
publicação. Nenhum resultado Linux anterior foi reutilizado como aceite nativo.

## Comprovação dos três adaptadores — 2026-10-21

Pedido atual menciona P329, não encontrado no repositório; contexto da conversa
identifica P239. Execução pelas revisões v1.7–v1.9, C150 v1.3/v1.4 e A26
v1.4/v1.5. HEADs preservados: broker 26dd7b6, client fbbf7af, admin 2b6f245;
árvores locais com alterações anteriores. Nenhum commit/release nesta etapa.

Dependências obtidas pelo Cargo, incluindo windows-service 0.8.1; locks reais
gerados para client/admin, mantendo core Git pinado e locks/manifests principais.
O check inicial com CARGO_HOME em target/p239-cargo-home falhou no include
jitterentropy.h do AWS-LC (o arquivo existia). Repetição do mesmo lock no cache
padrão passou. Logs locais: target/p239-service-check-initial.log e
target/p239-service-check-standard-cache.log. Não houve alteração do AWS-LC.

Runner novo: scripts/verify_windows_service_builds.py. Primeira execução em
target/p239-proof-20261021 detectou zero testes de configuração por seleção
equivocada de --bin; registrou FAIL apesar da saída Cargo 0. Corrigido para
--lib. O Clippy habilitado encontrou collapsible_if nos callbacks dos serviços
e needless_return no shutdown Windows do admin. Corrigidos sem mudança de
comportamento, antes da repetição final. Preservados STOP antes do mutex,
callback sem IO, guardas nativas e versões.

Execução final:

```text
python scripts/verify_windows_service_builds.py --output target/p239-proof-20261021-final --offline
```

Saída global **1**, refletindo os dois gates Clippy falhos; não é PASS global.
Ambiente Windows x64 MSVC, Rust/Cargo 1.99.1. Evidência versionável com comandos,
saídas, hashes de fontes/binários/logs:
[p239-windows-service-proof-20261021.json](../../docs/results/p239-windows-service-proof-20261021.json).
Logs completos e fixtures próprias em target/p239-proof-20261021-final.

| Gate real | Broker | Client | Admin |
| --- | --- | --- | --- |
| fmt --check do manifest experimental | PASS | PASS | PASS |
| build --locked Windows x64 MSVC debug | PASS | PASS | PASS |
| marker schema=1 / componente / service_entrypoint=true | PASS | PASS | PASS |
| --version | 0.43.0 | 0.43.0 | 0.11.0 |
| Testes de serviço/configuração | 14 PASS | 3 PASS | 4 PASS |
| Clippy --all-targets -- -D warnings | FAIL: avisos Windows preexistentes | PASS | FAIL: avisos Windows preexistentes |
| Recusa de config relativa | PASS negativo | PASS negativo | PASS negativo |
| Execução do dispatcher fora do SCM | PASS negativo, erro 1063 | PASS negativo, erro de dispatcher | PASS negativo, erro 1063 |
| Inicialização nativa em fixture própria | Recusa de fsync Unix confirmada | Não ensaiada como serviço | Recusa de token Unix confirmada |

Os 21 testes não incluem o controle de serviços instalados. Os negativos de
armazenamento/token são PASS da proteção, **não** PASS de operação nativa.
Os executáveis ficam em target/p239-service-proof/x86_64-pc-windows-msvc/debug:
mqtt-broker.exe, mqtt-client.exe e xmqr-admin.exe. Hashes no JSON, sem confundir
esses executáveis novos com o MSI antigo exclusivo do gerenciador.

Contrato de empacotamento após locks: `python scripts/verify_windows_packaging.py`
saída 0, 11 PASS e 1 NOT_RUN (--wix não solicitado nesta repetição). Os manifests
continuam alinhados; não houve reconstrução ou instalação de MSI nesta etapa.

Consulta SCM atual: zero serviços xmqr; inventário HKLM de componentes ausente.
Sessão elevada disponível, mas Hyper-V namespace root/virtualization/v2 ausente,
sem Windows Sandbox. Portanto, o gate real start/stop/restart pela bandeja é
NOT_RUN, sem VM apropriada e sem autorização específica de instalação no host.
O prompt original exclui essa instalação. O próximo teste concreto está em
[procedimento de SCM](../../docs/windows-service-scm-validation.md).

Conclusão delimitada: dependência, compilação, markers e testes dirigidos dos
três adaptadores estão comprovados. W2/W3 continuam pré-requisitos para manter
broker/admin em Running e testar operação dos três serviços. Instalar os
executáveis atuais permite ensaiar falhas de inicialização, não remove essas
recusas. W4/W5/W6 e fase 9 permanecem abertos.
