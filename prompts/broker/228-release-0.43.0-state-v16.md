# P228 v1.2 — distribuir broker0.43.0 e estado16

Preparado em2026-10-18 antes de bump/build/publicação. Pedido vigente:
concluir fase6 e distribuir broker, client e admin com prompts, testes,
commits/push, tags imutáveis, releases, pacotesUbuntu26 e DockerHub numerado.

## Entrada e condição de execução

Publicado broker0.42.0/estado15, client0.36.0 e admin0.10.0. CandidatoP227E
88906d6 introduz estado16 e ainda tem gates abertos: fullsuite/revisão,
descarte por identidade e admin compatível. Nenhuma tag/publicação deste
prompt equivale a aceite dessas pendências. Consulta remota nesta preparação
não encontrou refs/tags/v0.43.0; reconferir imediatamente antes de publicar.

Só promover fonte depois de corrigir/revalidar falhas P227. A versão0.43.0
é minor experimental por mudança real de persistência/runtime, não por docs.
ClientC131 e adminA21/A22 mantêm versões/ciclos independentes. Preservar
trabalhoC128dirty do client; não absorver bridge implicitamente na release.

## Escopo

Cargo.toml/lock, Dockerfile/receitas de distribuição que declarem versão,
VERSIONING, README e docs/releases/0.43.0.md, CI integrada6A–6D com peers
pinados, metadados/proveniência e registroP228. Sem novas dependências,
mudanças no serviço/firewall/ESP32 do operador, tags antigas ou latest.

## Compatibilidade

Ler formatos1–15 e gravar16 sem inventar intervalo original de mensagens
antigas. Broker15 deve rejeitar16 sem alterar snapshot/WAL. Preservar backup
privado15 ANTES da primeira gravação16: downgrade do binário não converte
estado. Admin novo deve fixar SHA público validado e provar A21 real. Core
pinado anterior à nota/CI final é aceitável somente com runtime idêntico
comprovado por diff, nunca por igualdade do número da versão.

## Gates

Rustfmt, test locked, Clippy all-targets -Dwarnings, builddebug/release e
inventário/licenças; campanha integrada limpa com fontes/hashes/ELFs exatos,
legacy broker15/clientdraftv1 reais, Mosquitto/Paho e negativos TLS/mTLS.
Guardar FAIL e revisar prompt antes de correções. Nenhum skip implícito.
Fase6 só encerra depois de todos os critérios M01–M10 realmente aprovados.

Gerar .debUbuntu26amd64 com serviços verificados, testar instalação/upgrade
e rollback em container descartável, sem executar broker antigo em estado16.
Provar restauração de backup15 para rollback executável. Testar imagens
lepinheiro100/xmqr-broker:0.43.0 e xmqr-admin:0.43.0 por digest com defaults
seguros, versão e configuração sem segredos. Nenhuma publicação antes dos
gates da fonte exata; recursos de instalação somente no container próprio.

## Publicação

Push normal, tag anotada imutável v0.43.0 da fonte validada, prerelease com
notas francas, .deb, SHA256SUMS, inventário/notices originais e proveniência.
Comparar tamanho/SHA remoto dos anexos e digests remotos das imagens. Não
anunciar produção, certificação MQTT5 integral, perda de energia ou SLA por
campanha finita. MIT própria e licenças de terceiros preservadas. Depois
do aceite6, prosseguir fases restantes com prompts e critérios próprios.

## Revisão1.1 — ambiente do inventário após FAIL de launcher

Fullsuite043 passou311testes/6campanhas opt-in ignoradas; inventário foi
chamado em outro processoWSL sem o PATH explícito deRust usado pelo Cargo.
FalhouFileNotFoundError:cargo antes de produzir inventário, não uma licença
rejeitada. Preservar FAIL; repetir script original em subprocesso com PATH
da toolchain conhecida, TMPDIR=/var/tmp e modoCargooffline. Não instalar
ferramentas, alterar perfil/global ou modificar o script para esconder erro.

## Revisão1.2 — ENOMEM nos builds locais

Build nativo release043 -j1 falhou os12 Cannot allocate memory no arquivo
rlib temporário. BuildDocker próprio concomitante e coletor de notices também
observaram pressão/ENOMEM, sem licença rejeitada. FreeWSL posterior mostrou
7,9GiBRAM,3,3GiBavailable e6,27/8GiBswap utilizada; não prova a origem exata
de cada alocação, mas justifica serializar jobs antes de retry.

Cancelar somente o buildDocker próprio identificado, preservando caches/logs;
nunca daemon/serviço global, processos do operador, prune ou restartWSL.
Dar prioridade ao adminA21, depois release nativa do broker, depoisDocker.
Repetir comandos/perfil originais depois de cada slot liberado, sem reduzir
gates nem alterarRAM/swap/perfilLTO global para fabricarPASS. Manter FAIL.
