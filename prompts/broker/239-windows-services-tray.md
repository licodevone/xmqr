# P239 v1.0 - serviços Windows e bandeja XMQR

Pedido: implementar serviço e bandeja para os componentes instalados, com
iniciar/parar/reiniciar e acesso à configuração, certificados e logs do broker.
Data: 2026-10-20 (America/Sao_Paulo).

Entrada: broker 0.43.0, HEAD 26dd7b6134396aeb7b0368e5a15cad881af7edd4,
árvore limpa; Product.wxs existente preservado/evoluído. Client 0.43.0 e
admin 0.11.0 são repositórios independentes. Fase 9 permanece aberta.

Escopo: adaptador SCM Windows opt-in no broker; shutdown pelo caminho existente;
gerenciador Rust independente em tools/windows-manager (sem Cargo workspace),
inventário HKLM protegido pelo instalador, consultas SCM, menu dinâmico, estados
por componente/agregado e atalhos de caminhos registrados. Instaladores WiX e
scripts de build para broker, gerenciador e componentes opcionais. Documentação
e registro P239. C150/A26 governam adaptadores nos outros repositórios.

Requisitos: nenhum unsafe próprio; dependências Windows somente no alvo;
STOP/SHUTDOWN cooperativos, Pending/Running/Stopped reais, falha com exit code;
reinício aguarda parada e tem prazo; nenhuma execução arbitrária pelo menu;
sem componente instalado não há item; sem serviços não há ícone; acesso negado
não equivale a ausente; estado misto amarelo, parado cinza, erro vermelho;
verde indica execução confirmada (prontidão MQTT distinguida no texto).
Não bloquear UI em consulta/controle; uma operação por vez e fila limitada.
Atalhos usam caminhos absolutos instalados, sem interpolação em shell;
certificados não são lidos pelo gerenciador. Sair da bandeja não para serviços.
Instalação de componentes é independente; gerenciador compartilhado permanece
até remoção explícita, sem ícone quando nenhum componente estiver registrado.

Bloqueios de plataforma conhecidos: persistence::sync_directory recusa Windows;
admin token privado depende de Unix. Não remover essas proteções nem alegar
homologação. Implementar infraestrutura e registrar falha real de inicialização.
Adaptação durável/ACL nativa é pré-requisito de aceite funcional completo W2/W3.

Migração: nenhum formato MQTT/WAL, protocolo, versão ou pin Git alterado.
CLI sem opção de serviço e Linux preservados. Não instalar no host, publicar,
commit/push/tag nem alterar permissões do operador. MSI deve preservar dados.

Aceite/validação: fmt/test/clippy/build dos alvos alterados; testes de inventário,
combinações instalado/ausente/erro, estados e caminhos; empacotamento WiX;
smoke CLI e pré-requisitos nativos. Testes SCM elevados, boot/logon, UAC e ciclo
instalação/remoção em VM serão BLOCKED se ambiente ausente. Nenhum gate simulado
é apresentado como execução real de serviço. Revisar este prompt antes de
corrigir falhas; resultados em prompts/registros/P239-windows-services-tray.md.

## Revisão v1.1 - gates iniciais e backend da bandeja

Primeiro cargo check bloqueado por DNS indisponível para index.crates.io;
windows-service não está no cache. Não inventar Cargo.lock/checksums. Executar
gates offline e registrar dependências ausentes. Primeiro fmt --check detectou
somente formatação do código novo; aplicar rustfmt antes de repetir.
A bandeja usará dependências locais tray-icon/tao/winreg e ServiceController
via PowerShell com argumentos validados, em vez de windows-service/winit nela.
Elevação somente para ação explícita, inventário HKLM novamente validado pelo
helper, sem execução arbitrária. Adaptadores dos serviços usam windows-service.

## Revisão v1.2 - revisão de código e primeiro gate WiX

WiX WIX0230 em fixture: componentes cujo keypath é diretório não aceitam Guid=*.
Corrigir com GUID estável específico por componente e repetir compilação da
fixture, sem confundir fixture com pacote distribuível. Revisão do adaptador:
callback SCM deve somente sinalizar; retirar IO de log e garantir notificação
mesmo em falha do mutex de status. Não manter mutex de status durante IO.
Adicionar validação isolada dos argumentos/caminhos e testes sem dependências.
Cargo.lock antigo permanece sem windows-service: isso bloqueia também a
resolução --locked em Linux, não apenas Windows, até obter a dependência.

## Revisão v1.3 - isolamento do build experimental de serviço

Para não impedir os builds atuais, retirar a dependência nova do manifest raiz.
Manifest independente packaging/windows-service/Cargo.toml reutiliza as fontes
e declara feature windows-service-runtime; somente esse build inclui o adaptador.
Manifest raiz reconhece o cfg via check-cfg, mas não oferece essa feature.
CLI normal Windows/Linux e Cargo.lock raiz preservados. O script de serviço
exige o novo lock real antes de build --locked; nunca usa executável antigo.
Documentar duplicação de metadados e conferir drift dos manifests no validador.
Gates de serviço seguem BLOCKED; gates da CLI e modelo são executados separados.

## Revisão v1.4 - fixtures e verificação de artefato

Validador Python de MSI encontrou Temp do sandbox sem permissão de escrita/
remoção. Usar diretório exclusivo verificado em target/windows-packaging-tests,
com limpeza limitada a essa raiz. Gate de artefato exige resposta JSON do
--windows-service-capabilities no executável novo; binário console comum é
recusado. SCM: publicar notificação de stop antes de tentar mutex de status,
evitando tanto perda por mutex envenenado quanto Running após StopPending.

## Revisão v1.5 - revisão de privilégios do instalador

Revisão identificou DATADIR público livre combinado com ACL protegida em
CreateFolder. Restringir a raiz dedicada do produto (ou remover override livre)
para impedir alterar ACL de diretório compartilhado/raiz por parâmetro errado.
Documentar instalação coordenada do gerenciador como entrada padrão; MSI de
componente isolado não resolve a dependência da bandeja sozinho. Candidatos com
a mesma versão não devem permitir side-by-side ambíguo por ProductCode novo.

## Revisão v1.6 - revisão final de caminhos do wrapper e checksums

Usar Environment.SpecialFolder.System (ou HKLM protegido) para localizar
msiexec antes de elevação, sem confiar em env:SystemRoot. Localizar ProgramFiles
também por API conhecida. Corrigir normalização de barras no SHA256SUMS: string
PowerShell '\' representa uma barra literal, sem escape extra. Reempacotar o
gerenciador em diretório novo e conferir hashes; nenhum teste de serviço real
é inferido dessa correção do empacotador.

Esclarecimento da revisão v1.6: leitura do fonte confirmou que Replace('\','/')
já continha uma única barra. A aparência duplicada vinha do escape da saída da
ferramenta; não houve defeito de separador nem correção correspondente. Somente
ordenação determinística dos checksums e resolução de caminhos são alteradas.

## Revisão v1.7 — comprovação dos adaptadores (2026-10-21)

Pedido atual: resolver a pendência de comprovação referida como P329; a busca
local não encontrou esse ID. Pelo contexto da conversa, o alvo é P239, sujeito
à correção do mantenedor. Entrada: HEAD 26dd7b6, broker 0.43.0 e todas as
alterações locais P239 preservadas; client fbbf7af/C150 e admin 2b6f245/A26.
O download windows-service 0.8.1 e o lock do broker existem; nenhum serviço
xmqr está registrado e o inventário HKLM está ausente na consulta anterior.

Objetivo: substituir o bloqueio histórico de compilação por evidência real
dos três executáveis com adaptador, corrigindo erros encontrados nessa fatia.
Escopo: manifests/locks experimentais, src/windows_service.rs e integração
de lançamento se a compilação exigir correção, scripts de prova, guias e
registros P239/C150/A26. Antes de alterações nos projetos vizinhos, registrar
a revisão de seus prompts. Não alterar pins, versões, protocolo, quotas,
formato de estado ou proteções nativas de persistência/credenciais.

Validação: build/check --locked dos três adaptadores, testes dirigidos ao
serviço/configuração, fmt e Clippy; gates globais quando houver mudança
funcional, com falhas preexistentes explicitadas. Executar markers reais e
negativos de lançamento fora do SCM; registrar comandos, saídas, hashes dos
executáveis, plataforma e fonte local. Revalidar a bandeja e contratos MSI
somente quando necessário após mudanças. Corrigir referências obsoletas sobre
dependências. Build/marker/teste unitário não equivalem a controle SCM real.

Verificar disponibilidade de ambiente descartável Windows para o gate SCM.
Na ausência dele, preparar um procedimento concreto, com pré-requisitos e
resultado esperado, antes de solicitar autorização para instalação no host,
pois o prompt original exclui essa instalação. Não instalar serviços nem
alterar HKLM/permissões sem essa autorização. Recusa nativa de inicialização
é evidência negativa, jamais PASS de operação. Aceite de serviço exige estado
e transições reais; registrar separadamente o que permaneça bloqueado.

### Ajuste de validação v1.8

O primeiro check falhou no AWS-LC ao resolver um include pelo cache profundo
target/p239-cargo-home; o mesmo lock passou usando o cache padrão do Cargo.
O runner de prova detectou corretamente zero testes ao selecionar
configuration::tests no binário do broker. Corrigir a seleção para --lib,
manter zero testes como FAIL e repetir os gates finais com os builds em cache.
Guardar a primeira tentativa como evidência, sem editar seu resultado.

### Correção de lint v1.9

O build habilitado revelou clippy::collapsible_if em windows_service.rs do
cliente. O mesmo callback foi inspecionado nos três adaptadores. Unir os dois
if let em let-chain (Rust 2024/MSRV 1.88), mantendo sinalização de STOP antes
do mutex, sem IO no callback ou mudança de comportamento. Repetir fmt,
build, testes e Clippy dos adaptadores; avisos preexistentes de outros módulos
continuam separados. Corrigir também o runner conforme v1.8 após terminar a
primeira execução, preservando seus logs.
