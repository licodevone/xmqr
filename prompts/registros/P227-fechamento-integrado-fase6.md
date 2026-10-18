# P227 — validação integrada da fase 6

Execução em 2026-10-18, Ubuntu26.04/WSL2, Rust1.99/Python3.14.
**EM VALIDAÇÃO: não é fechamento, tag ou release.**

## Proveniência dos primeiros gates

Entrada publicada: broker0.42.0/client0.36.0/admin0.10.0. Binário debug
preexistente do broker era0.41.0: não foi tratado como artefato0.42.0.
Baseline congelado SHA256
`674963f56ab2def9297847a94f5e2388003824eb6d67b75db27e4c7fbbd1709f`.

Candidato integrado com P227A/P227C, sem bump, compilado por
`cargo build --locked --offline --bins -j1` (58,01s). Mudanças funcionais
commitadas em `10bab601050cb547933d6702e4291fe184e86c8d` e `10d5081`.
ELF congelado `../.artifacts/p227-binaries/mqtt-broker-integrated-0.42.0`, SHA256
`46d79faf91220cdd59e43602c8f3528a2654463a6f71408c542a9c8638b4f809`.
Esse candidato modificado não é o artefato publicado da tagv0.42.0. Não houve
alegação de build bit a bit reproduzível entre diretórios/máquinas.

## Resultados efetivamente executados

| Gate | Resultado | Evidência / limite |
| --- | --- | --- |
| Contratos do executor integrado, revisão1.5 | 10PASS;0FAIL,0,098s | `scripts/test_phase6_acceptance.py`, execução nativa WSL |
| VBI MQTT5 | RED2PASS/18FAIL no baseline; GREEN21/21PASS no candidato | [P227A](P227A-fase6-vbi-canonico.md); helper/hashes e cleanup registrados pelo agente |
| Fairness e Will takeover | RED0/3; GREEN3/3PASS,4,972s | [P227C](P227C-fase6-shared-e-will.md); mesmo harness em RED/GREEN |
| Matriz de queda de processo do broker | 12/12PASS no baseline e candidato | QoS1, fasesQoS2, expiração e Will;4cenários×3, SIGKILL só nos filhos próprios |
| Paho MQTT5 P168 | PASS,1,597s no candidato | assignedID,SessionPresent,QoS0/1/2,retained,offline,recusa3.1.1 |
| Paho PLAIN inicial TLS/mTLS | PASS,7,654s no candidato; baseline tambémPASS | pub/subQoS1,senha inválida,método desconhecido; CA/SAN verificados; sem alegação de reauth externa |
| `cargo test --locked --offline -j1` | exit0;263PASS;0FAIL;6ignored | compile96s;lib239PASS/6ignored em43,67s;admin4,main9,integrações11;doc0 |

Relatórios locais sanitizados preservados fora do Git:
`../.artifacts/p227-crash-baseline-1.json`,
`../.artifacts/p227-crash-integrated-1.json`,
`../.artifacts/p227a-vbi-candidate-1.json`,
`../.artifacts/p227c-shared-will-baseline-1.json` e
`../.artifacts/p227c-shared-will-candidate-1.json`.
Os resultados Paho foram observados nos subprocessos exit0; não se anuncia
JSON inexistente desses testes individuais. O executor integrado produzirá
seu próprio relatório exclusivo após construir o conjunto final.

Paho é checkout oficialv2.1.0, commit
`af64a4365c6ac5a7a4d339e7b00f44df91353b35`, usado por PYTHONPATH privado,
sem instalação global/runtime vendorizado. Licenças originais preservadas.
Os seis testes ignorados são campanhas explícitas de fuzz; o gate comum
não equivale a executá-las novamente.

## Pendências que impedem o aceite

- P227D: alias válido ainda não mapeado com tópico vazio deve receber0x82;
  zero/excesso continuam0x94. Matriz registrou a divergência, sem ocultá-la.
- C129: journal inbound do client em clone isolado, ainda sem aceite final
  nem integração na árvore que contém distribuiçãoC128 de outro escritor.
- Repetir fmt/test/Clippy/build/inventário e wire integrados na fonte final,
  com manifests/versões/hashes coerentes e três repositórios limpos.
- Confrontar M01–M10, decisões opcionais e limites de interop com o aceite;
  não marcar fases por contar prompts nem transformar falha externa emPASS.
- Selecionar versões independentes e distribuir somente depois do aceite
  real: commits/push, tags imutáveis, prereleases,deb eHub numerados.

Não foram alterados serviços, firewall, ESP32, segredos ou estado do operador.
Resultados finitos não demonstram perda de energia, SLA, produção ou
certificação completa MQTT5. MIT própria e notices de terceiros preservados.

## Continuação — integração D, C129 e revisão do executor

P227D corrigiu alias válido não mapeado com tópico vazio para0x82, preservando
zero/excesso0x94. ELF D SHA256
`dca22b2624b7f36175d4e939c640b6f5730220bcc9510580eef9054a6af8ef57`,
runtime `d28f832`, versão de candidato0.42.0. Wire final9/9PASS; VBI21/21PASS.
O primeiro testeD com MPS7 tinha expectativa incorreta: esse CONNACK omite
TopicAliasMaximum, portantoalias1 é excesso e0x94 é correto. Prompt revisado
antes do ajuste; FAILs preservados no [registroD](P227D-fase6-alias-nao-mapeado.md).

A primeira tentativa do agregado foiBLOCKED/OSError antes dos cenários.
Diagnósticos posteriores identificaram divergência de normalizaçãoGit entre
Windows/WSL nos clones; opção autocrlf foi alinhada só nesses clones, sem
editar configuração global ou árvores do operador. A causa do OSError
original não foi comprovada só pelo tipo. Outra chamada nem iniciouPython
por WSL/Service/0x8007274c; repetição posterior voltou a funcionar sem reinício.

Revisão independente do executor reproduziu falsos positivos de markers
NOT_*_PASS e stderrBLOCKED ignorado; identificou possível filho remanescente
após exit0 e orçamento tardio de logs. P227v1.7/v1.8 precederam correções:
markers específicos por fixture, duas linhas obrigatórias cross/sessions,
negativos nos dois canais, pipes com memória limitada, limpeza do grupo
privado mesmo em sucesso e estágio/errno sanitizados. Primeiro gate14 teve
13PASS/1FAIL de expectativa do motivo mais estrito; após revisão15/15PASS.
Mosquitto/OpenSSL agora têm versão/hash; Paho tem hashes dos módulosPython,
não apenas__init__.py. `mosquitto_pub/sub --help` retorna1 normalmente,
validado pela linha de versão e tratado explicitamente como tal.

Campanha **selecionada6A**, não fechamento6A–6D:
`../.artifacts/p227-acceptance-d-6a-2.json`,32/32fixturesPASS,94,986s,
fontes/binariesunchangedtrue. Snapshotbroker `8160858`, clientbaseb9f46cb,
admin17c3cff. Client036 foi extraído do.debpublicadoSHA256
`904c9731ac9a9c218e9533a4b89388859f07c0767f68fb7ba14409ffdbac4040`,
sem instalação: mesmo ELFrelease copiado para os caminhos debug/release de
teste, não anúncio de duas compilações. O runtime mqtt-client não mudou entre
a tag036 e b9f46cb; o sidecarbridge adicional não foi exercitado neste gate.
O admin010 foi reutilizado e seu runtime comparado à tag, sem alterações.

P227F cobriu controle no mesmo peer com ReceiveMaximum1 esgotado: QoS1 antes
PUBACK e QoS2 antesPUBCOMP, PINGRESP/SUBACK/UNSUBACK e QoS0 progridem;
segunda cópia aguarda ACKterminal e depois conclui.2/2PASS noELFD,2,89s,
`../.artifacts/p227f-control-d-baseline-2.json`. Não foi preciso mudar runtime.

C129 foi integrado por commits próprios sem incorporarC128dirty.175Rust,
18TCP e6compatPASS constam no [registro do client](../../../xmqr-client/prompts/registros/C129-subscription-inbound-state.md).
Revisão independente encontrou metadadosSubscriptionID mutáveis e journal
órfão semmanifesto: correçõesC129v1.12 ainda em andamento antes de push final.
P227E também está corrigindo intervalo original/clockregressivo e distinguindo
envioPrepared deMayHaveSent com formatov16. AdminA21 tem prompt, não aceite.
Essas pendências impedem conclusão da fase6 ou publicação de marco final.

P227G acrescentou interop de alias com dois peersPaho2.1.0 oficiais: nome+
alias inicial, forma compactaQoS0/1/2, rebind da entrada, retained e reset de
conexão da saída. `P227_PAHO_ALIAS_PASS` real noELFD, report exclusivo
`../.artifacts/p227g-paho-alias-d-1.json`. Paho decodifica wire/propriedades
e conduz ACKs; o callback do harness faz a resolução do tópico por tabela
limitada. Isso não é substituição nativa de tópico peloPaho nem homologação
da recepçãoMosquitto2.0.22. Nenhuma biblioteca/runtime/serviço foi instalado.
O gate6C passa a exigir essa prova independente, além de conservar o caso
Mosquitto explicitamente rotulado como reprodução de limitação.

## Campanha ampla Dall4 — resultado não aprovado

`../.artifacts/p227-acceptance-d-all-4.json`:68fixtures,62PASS/6FAIL,
224,067s; fontes/ELFs inalterados. Quatro FAILs foram reproduzidos e
diagnosticados como expectativas históricas emP227H: fronteirasCONNACK
pré-anúncioSharedAvailable, parser0x2a usado porP146, associação persistente
shared anterior aP154 e alias desconhecido anterior à correçãoP227D.
Após revisão do prompt, os quatro harnesses passaram isoladamente no mesmo
ELFD e client109ec973, sem alterar runtime para satisfazer expectativas.

VBI ealiasReason falharam antes de imprimircenários/criarJSON na campanha;
repetições isoladas completas passaram. Causa original não confirmada,
portanto não se transforma Dall4 emPASS. O executor agora registra tipo
permitido de exceção e número da última linha de stack, sem mensagens/paths
privados. Seus16contratos determinísticos passaram em0,246s.

C129 final foi integrado após181Rust/21TCP/6compat e migração realv1→v2PASS.
As correções foram enviadas aGitHubmain, preservandoC128dirty no original.
C131 prepara client038 em clone/branchseparados: nenhuma release038 é
anunciada como existente só por essa preparação. E/admin16 permanecem
abertos, de modo que esta campanha ainda não encerra a fase6.

## Executor v16 — entradas legadas explícitas

P227v1.10 precedeu a integração de A21 e da migração real do journalC129.
O registro corrente preserva o script históricoA19, mas exige a fixtureA21
para formato16. --legacy-broker e --legacy-client são obrigatórios nos
respectivos gates6B: ausência resultaBLOCKED, sem fallback para binário
corrente ou interferir nas seleções6A/6C/6D. Versão/SHA legados são registrados
separadamente e conferidos ao término, sem exigir versão igual ao manifesto.

Contratos do executor:19/19PASS em0,237s, Python3.14 Ubuntu26.04/WSL,
incluindo ausência de entrada, versão antiga independente e argumentos dos
harnesses. Isto não é execução de A21 nem da migração wire. Campanha final
aguarda coreE congelado, admin pinado compatível e fonteC131 com teardown
corrigido: seu CI anterior confirmou dados MQTT mas falhou ao remover pasta
antes de encerrar filho, não pode ser tratado como aprovação da distribuição.

Revisão independente do executor identificou opt-inP147_MOSQUITTO_PORT herdado
e falta de cleanup se captura fosse interrompida. P227v1.11 precedeu remoção
do seletor do ambiente dos filhos e proteção de captura emBaseException com
kill/wait/close somente do grupo privado criado.21contratosPASS em0,342s,
incluindo interrupção injetada com filho real próprio e repropagação de
KeyboardInterrupt. Não foi consultado/alterado Mosquitto do operador.

## Fullsuite P227E inicial — FAIL preservado

Fonte runtime88906d63c4384961f7a9215945840905f3568b4d; comandoUbuntu26WSL
cargo test --locked --offline -j1, Rust1.99, TMPDIR=/var/tmp. Compilação75s;
lib66,69s:263PASS/8FAIL/6ignored, exit1. As seis campanhasfuzz ignoradas
são opt-in históricas explícitas, não homologadas nesta execução. Cargo
interrompeu apóslib, portanto integrações/binários posteriores NOT_RUN.

Oito falhas em connect_contract_tests linha306 exigiam contador absoluto0;
o startupP227E grava watermark antes do primeiro CONNECT, observado1. O
contrato que continua obrigatório é ausência de commit adicional pelo
CONNECT recusado, não substituir zero por um literal. OwnerE revisará prompt
antes de capturar baseline após startup e repetir negativos/invariantes.

Revisão independente também identificou possível corrida permit→descarte:
prepare valida identidade durável, mas descarte posterior só porpacketID
poderia remover nova obrigação após poda/reutilização. OwnerE recebeu pedido
de reproduzirRED e corrigir descarte condicionado à mesma identidade. Nenhum
resultado acima aceita essa corrida, encerra fase6 ou autoriza tag antecipada.

## Preparação CI exata, ainda NOT_RUN

P227v1.12 precedeu .github/workflows/phase6-acceptance.yml: dispatchmanual,
Ubuntu26 descartável, Rust1.99, quatro inputsSHA completos validados antes
checkout, Pahooficial fixadoaf64a43 e projetos/legacies isolados. Compila
fontes específicas, executa gatesRust e registra manifestoELF→commit/SHA,
depois contratos/coordenador com relatórios exclusivos sanitizados. Artefatos
JSON preservados viaalways mesmo após falha. Nenhuma instalação no host do
operador ou execução automática sobre serviços existentes.

Validação local: YAML parse PyYAML6.0.3, quatroinputs/defaultsSHA e duas
seçõesPython embutidas porAST PASS; gitdiffcheckPASS. Não equivale a CI:
dispatch/aceite continuaNOT_RUN, aguardando coreE, peers públicos e A21.

## Checkpoints seguintes, sem aceite global antecipado

CoreE corrigido emc3713c839e17020d76dbca60e737c36c9b271860: owner reportou
E38/router93/store19/connect14/codec67PASS, ClippytestsfmtPASS. DescarteR0
fica no mesmo comando do ator e MPS verifica identidade/metadados/estágio;
root leu helpers e aguarda fullsuite. Resultados dirigidos não substituem
o gate completo, migração/admin16 ou distribuição.

Root executou novos9gruposP227I:3PASS/6FAIL, compile2,07s/test0,02s.
Os seis falharam em codec4406 comSecondConnect, pois o helperWill usava
decoder de conexão já estabelecida. Owner revisou prompt antes de mudar
somente o contexto inicial; repetição9/9PASS, sem parser/tetos/oráculos
alterados. RegistroP227I preserva falhas e gates subsequentes; repetição
completa ainda pendente neste checkpoint.

Client038: root confirmou viaGitHubCLI prerelease/seisassets e viaHubCLI
índiceOCI remoto SHA256b025a82ab4172f82223e8b01b125570996f374a27ee524a04cc62eac81a148f9.
Aceite clone client foi fixado emtagfca6fc8 e recebeu o ELFrelease congelado
a5ccc205... em ambos caminhos de fixture, não duas builds diferentes.
Correção do harness de teardownC131 foi integrada isoladamente em main pelo
C132/dd3d2f8 e enviada aoGitHub, sem CI/Cargo/bridgeC128dirty. Root repetiu
migração com ELF109ec→a5ccc:PASS0,2733s, sem saída duplicada e cleanupPASS.

## Campanha ampla Eall6 — FAIL preservado

Relatório ../.artifacts/p227-acceptance-e-all-6.json:69fixtures,65PASS/4FAIL,
208,554s. Brokerba6/ELFfce43, clientfca/ELFa5ccc038, adminba7/ELF732011;
sources/binaries/legacyunchangedtrue. MigrationsA21/journal, crash, controles,
PahoAUTH/aliases e todos os scripts MQTT5 históricos passaram. Falharam:

- VBI ealiasReason:nonzero_exit/OSError, última linha203, stdout0;
- sharedWill:setupOSError antes de cenários, cleanupPASS,0,881s;
- channelCLI:AssertionError no stop/linha110; repetição isolada do owner
 admin antes da campanha havia passado, sem comprovar a causa desta falha.

O intervalo coincidiu com builds próprios/ENOMEM, mas OSError semerrno não
prova essa causa específica. Não transformar Eall6 emPASS por repetição.
P227J foi delegado para hashes de ELF emstream limitado em vez de read_bytes,
sem alterar oráculos de protocolo. ChannelCLI exige diagnóstico separado.
RegistroP228 preserva FAILrelease e retryserial posterior aprovado.

## CI integrada — cancelamento preventivo e trust delimitado

Run39141241671 na fonte pública ba6/clientfca/adminba7 foi cancelado por
ação própria antes do gatefinal; GitHub confirmou completed/cancelled. Não é
FAILMQTT nemPASS. JobadminA22 detectou emUbuntu26/Git2.53 erroreal de dubious
ownership, portanto P227v1.13 precedeu proteção de processoGit somente para
seis caminhos exatos de checkout, semwildcard/global/host. Novo preflight
registra revisões/statuslimpos antes de builds e artefatosJSON exclusivos.
YAML/ASTtrêsblocos e contratos seispathsPASS; dispatch corrigido pendente.

## Continuação P227 v1.14 — envio explícito de evidências ocultas

O workflow tinha `path: .evidence/*.json` sem `include-hidden-files`:
`upload-artifact@v4` ignorava o diretório oculto e podia terminar com
`No files found` mesmo após gates funcionais. O prompt P227 v1.14 foi
versionado antes da correção. O workflow agora exige 13 JSON finitos,
presentes, não simbólicos, limitados a 4 MiB e parseáveis depois do PASS do
coordenador; os relatórios de fase devem declarar `status=PASS`. O upload em
`if: always()` enumera exatamente esses 13 caminhos, habilita arquivos
ocultos e trata ausência de arquivo como erro. Uma falha anterior continua
produzindo apenas a evidência parcial existente, sem alegar aceite.

Validação local em Ubuntu 26.04/WSL: PyYAML 6.0.3 leu o YAML; AST do bloco
Python e seleção exata 13/13, `include-hidden-files`, `always` e `error`
PASS (`P227_WORKFLOW_STATIC_PASS`). `scripts/test_phase6_acceptance.py`:
21/21 PASS. `actionlint` não está instalado nesta máquina: BLOCKED para esse
gate local, sem instalação implícita. Dispatch remoto, download dos JSON e
aceite integrado permanecem PENDING neste checkpoint.

## Run integrado 39162215519 — FAIL preservado

Na fonte broker `1574ab9fcaf5268a3c2eb54e49fcaca9cc598cc4`, o workflow
manual terminou FAIL: 69 cenários, 66 PASS e 3 FAIL. O artefato oculto foi
publicado e baixado; SHA-256 do `phase6.json`:
`d78574d942daf7cc55b7ac202046a91cf7c0634b661774fcdd8d509eb4b8889a6`.
VBI e aliasReason (6A), sharedWill (6D) encerraram com `nonzero_exit`
antes dos respectivos JSON. Seus outros 66 cenários, incluindo as migrações
reais e fixtures dos peers, passaram; isso não fecha a fase 6.

As três fixtures verificam filesystem nativo no `--state-root` e usam
`/var/tmp` por default. `stat -f -c %T /var/tmp` no container Ubuntu 26.04
retornou `overlayfs`, logo a incompatibilidade é uma hipótese forte para os
três exit2 imediatos; a causa só será confirmada por novo run com raiz
montada do host e verificações explícitas. Prompt P227 v1.15 precede a
correção. Não alteramos os oráculos para aceitar overlayfs.

## Campanha local Eall7 e revisão de encerramento

O relatório `../.artifacts/p227-acceptance-e-all-7.json` contém 69/69
fixtures PASS, 195,813s, `source_unchanged`, `binaries_unchanged` e
`legacy_binaries_unchanged` verdadeiros. Não reclassifica Eall6 nem o
run remoto 39162215519. Fontes: broker44b4b28, clientfca6fc8 e adminfe8cff5.
Broker e admin legado foram os ELFs release extraídos do pacote oficial
CI39140250983/ba6ef50 (hashes1ee611b0/3081297f), não os ELFs debug da
campanha anterior. Client038 usoua5ccc205 e admin011 usou73222f35; os
legadosDdca22b2 e client109ec973 foram entradas separadas explícitas.

Mosquitto_pub/sub2.0.22 e OpenSSL3.5.5 foram identificados por versão/hash.
Os casos incluem A21v16, migração real do journalv1, compatibilidade inbound,
crash, controle comquotaesgotada, aliases e autenticação inicial Paho.
É evidência local finita, não aceite da CI exata ou certificação MQTT5.

Retomada solicitada pelo mantenedor: fonte broker congelada emdb472bc64558bf0e376a902b7780a259247c5149,
CI padrão39164202189SUCCESS. Diff de src/Cargo.toml/Cargo.lock/Dockerfile
entreba6ef50 e esse candidato é vazio. Run integrado39164217059 está em
execução; não é anunciado comoPASS. P227v1.16 precedeu a consolidação.
O admin011 foi publicado separadamente; seu helper de readiness/cleanup
precisa constar no peer efetivamente validado, conferido pelo manifesto.
Distribuição broker043 e aceite global6 permanecem pendentes neste ponto.
