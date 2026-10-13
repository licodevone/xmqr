# P80 rev1.7 — fechamento verificável da fase 2

Pedido: finalizar fase2; autorização vigente de commit/push e releases por marcos
aceitos. Data2026-10-13. Entrada broker/admin0.11.3 HEAD4e199b2244cc7758414531425dc1f1f483ac40ba,
client0.8.1 HEADbc94bd04d36f2bf5e61f3d60391bae142d9407b6. Broker limpo; duas
archives client0.7.1 não rastreadas preservadas. Fase1 aceita P61/C39,
campanhas P62/P72 aceitas. ESP32 físico é gate, não substituído por simulação.

Objetivo: completar a evidência de software da fase2 e fechar a fase somente
se TODOS os gates, inclusive E01 físico, passarem. Separar broker, client e placa.

Escopo: scripts/benchmark_pressure.py, scripts/test_benchmark_pressure.py,
testes determinísticos do ator em src/mqtt/router.rs; testes externos Docker
coordenados com C43; docs/results sem segredos, docs/phase2-acceptance.md,
docs/performance-pressure.md, docs/architecture/adr-0006-identity-quotas.md,
docs/esp32-phase2-checklist.md; matrizes/checklist/README e registro P80.
Não aumentar quotas nem alterar MQTT, TLS, perfis, WAL/snapshot, versões ou dependências.
Se aparecer defeito runtime, revisar este prompt antes de corrigir e preparar
o marco funcional com gates/artefatos exatos. Não avançar fase3 por gate bloqueado.

Método: Linux/WSL com binários release identificados e estado privado em filesystem
Linux nativo. 3 repetições open-lab/mTLS. Admissão simultânea N em1/8/32/64,
N+1 recusada, sessões clean distintas, vaga liberada e reutilizada. Clientes
sem completar handshake não prendem admissão indefinidamente. Medir RSS/HWM/CPU,
p50/p95/p99 conexão e PUBACK, contagens reais, tempo e ambiente. Gerador separado da CLI.
Clientes lentos: inflight e offline N/N+1 nas quotas reduzidas4/8 e defaults32/64;
sem ACK do assinante, recusa do publicador sem PUBACK/PUBCOMP indevido,
outras assinaturas progridem, sequência aceita é drenada e confirmada, reinício
com sessão persistente conserva obrigações. QoS0 não leitor no socket: teto de
mensagens/tempo, fechamento observável, demais clientes progridem. Teste do ator
determinístico cobre fila DELIVERY_CAPACITY64 cheia e ausência de avanço parcial
de estado na recusa de quota; respeitar PUBREC como aquisição durável do QoS2.

Referências consultadas2026-10-13: OASIS3.1.1 §§3.1.2.10,3.3.4,4.3.2,4.3.3,
4.4,4.6 (ACK/ownership, retransmissão e ordenação), fonte:
https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html .
Política de quota menor é local; não alegar confirmação de negócio ou perdas de energia.

Negativos do harness: limites/args inválidos, relatório existente/symlink,
sequência/ID/QoS incorretos, ACK prematuro não contabilizado, metadados/hash
do binário antes/depois e teardown apenas de recursos próprios. Relatórios
públicos não incluem certificados, hashes de senha, payloads sensíveis ou logs privados.
Campanha externa C43 usa Mosquitto2.0.22 local fixado por imageID/digest;
Docker Linux/amd64, rede namespace temporária sem portas publicadas, mTLS
CA/SAN/senha/ACL, pub/sub QoS0/1/2 e retained. Não instalar ferramentas no host.

Avaliar B05 por ADR: manter tetos/defaults até necessidade de isolamento por
identidade demonstrada e contrato de cobrança/fairness; registrar risco remanescente.
Aceite: gatesRust fmt/test/clippy/build/inventário; contratosPython; campanhas
completas/repetidas; matriz externa e relatório consolidado; E01 somente com
placa real, Wi-Fi/SNTP/mTLS/pubsub/reconexão e negativos observados.
Sem porta física acessível -> BLOCKED para E01, fase2 PARTIAL/BLOCKED,
nenhuma tag de aceite integral. Preparar checklist reproduzível da DevKitV1.

Compatibilidade/migração: nenhuma nesta fatia de testes/documentação. MIT própria
e terceiros preservados. Commit/push de evidência aceita autorizados; não criar
tag de runtime ou release binária fictícia por benchmark/documentação.

## rev1.1 — revisão do teste antes da compilação

Inspeção identificou que MqttStore não possui setter limits_for_test.
Não adicionar API de produção só para teste: encerrar/reabrir o store
temporário com open_with_limits existente e conferir rollback do candidato.
Tentativa de patch desta revisão recusada por contexto; nenhuma edição nessa tentativa.

## rev1.2 — revisão de lifecycle da amostragem

Antes da campanha, revisão encontrou shutdown dentro do bloco Sampler,
que precisa ler /proc ao terminar. Mover shutdown para depois da amostra,
sem interpretar desaparecimento do processo como resultado de capacidade.

## rev1.3 — smoke negativo mTLS não leitor

Primeiro smoke: admissão/handshake e filasQoS1/2/restart PASS nos dois
transportes; socket não leitorTCP PASS, mTLS atingiu o teto60s/5000 sem
fechamento comprovado. Não promover campanha aPASS. Acrescentar diagnóstico
sanitizado de contagens/tempo/métricas no timeout e permitir selecionar
apenas os cenários para investigação, sem alterar o critério de fechamento.

## rev1.4 — defeito real no encerramento TLS

Segundo ensaio reproduziu mTLS não leitor: sessão já removida (sessions2),
connections_active3 e 5024 publicações tentadas; TCP encerra em cerca5s.
Código: BrokerConnection::shutdown aguarda TLS shutdown/flush sem deadline
após unregister; a tarefa e o permit de admissão podem ficar presos.
Correção autorizada nesta fatia: timeout3s no shutdown de transporte, erro
io::TimedOut, teste determinístico de AsyncWrite com shutdown pendente e
regressão real mTLS de não leitor/vaga disponível. Sem mudança wire/estado.
Marco de correção broker/admin0.11.4, clientruntime0.8.1 preservado.
Gates + clone de commit exato, Docker/mTLS/admin/lifecycle e .debUbuntu26amd64
antes de tagv0.11.4/prerelease/Hub numérico. Fase2 ainda exige E01 físico.

## rev1.5 — revisão do harness após campanha candidata

60 cenários passaram no broker corrigido. Antes da campanha final, reforçar
cleanup de conexões paralelas em falha parcial, comprovar reutilização de vaga
após handshake silencioso e após não leitor com max_connections3, e nomear
latência terminal de publicação sem chamar PUBCOMP de PUBACK. A campanha
candidata preservada refere-se ao harness anterior identificado no seu hash.

## rev1.6 — geração documental e aceite revisado

Campanha revisada60PASS; C43 ampliado59PASS. Geração de documentos por
templateJS falhou em backtick sem editar arquivos; patch conjunto posterior
recusado porque READMEclient usa # xmqr-client, não # XMQR Client. Reaplicar
contextos conferidos. Nenhuma dessas tentativas alterou runtime ou evidência.
Aceite global deve distinguir softwarePASS e placaBLOCKED, sem mudar o gate.

## rev1.7 — gate de links no PowerShell

Validador de links falhou antes de staged/commit: Split-Path de README.md
relativo retorna diretório vazio. Reexecutar com caminho absoluto do documento;
não corrigir links/fontes para contornar erro do validador. Nenhum commit/push
na tentativa falha. Gate de secrets usa rgexit1 como ausência de matches.
