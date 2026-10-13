# P91 v1.23 — B08: campanhas limitadas de robustez e interoperabilidade

Preparado em 2026-10-13 antes de editar os harnesses. Pedido: finalizar fase 3,
mantendo prompts antes do código e publicação somente após aceite coordenado.
Entrada: broker HEAD d467bf3f7f654be6aa133cefe4ad07ff0e6818fb, runtime 0.11.5;
P89 preparado pelo coordenador; client independente 0.8.1; admin independente
0.1.0. B06 aceito, B07/B08/C07 ainda abertos. Preservar alterações paralelas.

## Objetivo, escopo e autoria

Criar `scripts/phase3_soak.py`, `scripts/verify_phase3_interop.py`, testes
`scripts/test_phase3*.py`, `docs/phase3-campaign.md` e registros P91. Reutilizar
fixtures wire independentes de `benchmark_pressure.py`/`benchmark_fanout.py`
e o ambiente Docker de C43, sem usar o encoder Rust como oráculo. Não editar
Rust, client, versões, manifestos, CI de fuzz ou checklist global. Defeitos
normativos demonstrados são enviados ao coordenador antes de qualquer correção.

## Requisitos e invariantes

- MQTT 3.1.1: CONNECT/CONNACK, flags/UTF-8/ClientID, §§3.3–3.7 QoS,
  §§3.8–3.11 SUB/UNSUB, §3.1.2.10 keepalive, §4.4 retransmissões e §4.7 filtros.
  Fonte OASIS indicada na matriz e confirmada pelo coordenador P89.
- Pressão real por duração medida: três repetições independentes de pelo menos
  600 segundos, TCP e mTLS em estados separados. Quando executadas em paralelo
  dentro de uma repetição, distinguir 30 minutos de parede de 60 processo-minutos.
  Payload sintético com sequência/digest; QoS0/1/2, fan-out 4, retained,
  sessões offline, inflight interrompido, SIGTERM/restart e SIGKILL/recovery.
- Cada fluxo tem timeout; conexões/filas/payload/RSS/quantidade de amostras têm
  budgets explícitos. Amostrar RSS e readiness, relatar crescimento observado
  sem inferir ausência universal de vazamento, throughput máximo ou SLA.
- QoS1 admite DUP legítimo; comparar conjunto lógico, sequência e bytes, não
  exigir exatamente-uma entrega para QoS1. QoS2 testar limites de responsabilidade:
  PUBREC antes de PUBREL e PUBREL antes de PUBCOMP, sem ACK fictício/cheat.
- Ampliar C43 com Mosquitto 2.0.22 existente e pinado por image ID: ambos os
  brokers e ambos os sentidos de pub/sub, QoS/retained/sessão, desconexão/restart,
  ACL negada com observação independente e mTLS. A campanha C43 histórica
  mantém 59 cenários; novos resultados são evidência adicional, não reetiquetação.
- Fixture de autenticação usa senha pública de teste e Argon2 do admin real,
  nunca credenciais do operador. Certificados/chaves/estado só temporários.
  Loopback, Docker namespaces sem portas publicadas, nonroot/caps-none.
  Não instalar ferramentas, alterar firewall/serviços reais ou tocar ESP32.

## Aceite e evidência

Primeiro smoke/baseline claramente rotulado (não aceite do candidato final),
testes determinísticos do harness e negativos reais. Depois repetir no binário
final informado pelo coordenador e registrar SHA256 de binários, harnesses,
image IDs, configuração, tempos reais, cenários PASS/FAIL/BLOCKED e cleanup.
Reports JSON exclusivos, sem sobrescrever, incluindo falha sanitizada sem logs,
senhas, hashes de senha, PEM/chaves ou payloads reais. Após falha, revisar este
prompt antes de corrigir. Registrar limites: não há conformidade exaustiva,
energia, ensaio de dias, MSRV exato ou homologação Windows/arm64/ESP32 nova.

Wire e formatos duráveis permanecem intactos; sem migração nesta fatia. Nenhum
commit/push/tag/release aqui: publicação coordenada após gates integrados.

## Revisão v1.1 após smoke FAIL

Smoke baseline de 8s falhou antes de cumprir duração: `unexpected QoS
acknowledgment or packet identifier`. Antes de qualquer correção, acrescentar
diagnóstico sanitizado de estágio/subestágio e header esperado/recebido da
fixture sintética; nunca imprimir certificado, password, hash ou payload.
Verificar o contrato do harness e, se demonstrar defeito do broker, enviar ao
coordenador em vez de alterar o núcleo ou enfraquecer a asserção.

## Revisão v1.2 — contrato de lote QoS2

Diagnóstico: no replay offline QoS2 havia mais PUBLISH enfileirados antes do
PUBREL. Isso é permitido por MQTT e não demonstra defeito do broker. O harness
deve conferir todos os quatro PUBLISH/bytes/IDs e enviar PUBREC, depois conferir
os quatro PUBREL por ID e responder PUBCOMP. Não alterar core nem exigir uma
ordenação global artificial entre frames de responsabilidades distintas.

## Refinamento v1.3 antes da campanha longa

Smoke TCP/mTLS 8s PASS após correção do harness. A campanha longa deve manter
tráfego contínuo entre eventos de recuperação separados por 120s, evitando
reinícios tão frequentes que escondam crescimento de memória no mesmo processo.
RSS inicial/final entre gerações não é evidência de leak; reportar também
intervalos/amostras e delta por geração. O número de crashes/restarts é observado,
não prefixado como promessa. Mínimo de duração do aceite permanece intacto.

## Ampliação v1.4 — negativa de entrega da assinatura

Além da ACL de publicação, testar assinatura não concedida nos dois brokers com
ambos os clients. Criar segunda identidade pública temporária `fixture-writer`
permitida a publicar `other/value`, e comprovar ACK do publicador independente
sem DATA no assinante não autorizado `other/#`. Mosquitto pode conceder SUBACK
e filtrar na entrega; não interpretar SUBACK sozinho como bypass. XMQR pode
recusar o filtro imediatamente. Credenciais/certificado somente desta fixture.

## Revisão v1.5 após baseline externo

Baseline0.11.5/0.8.1:59regressõesC43 PASS, extensão FAIL por readiness timeout
antes de concluir o primeiro cenário. Total458.703s; recursos próprios limpos.
Não aceitar essa extensão nem atribuir causa sem diagnóstico. Acrescentar
estágio/contexto e estado/exitcode sanitizados do assinante antes do cleanup.
Usar candidato0.9.0 para o gate que separa espera ociosa de deadline de protocolo,
mantendo asserções de bytes, sequência e autorizacão. Não trocarFAILporPASS.

## Diagnóstico v1.6 — reprodução focada

Permitir `--only expanded` exclusivamente no modo baseline para reproduzir o
primeiro FAIL sem repetir os59gates já executados. O report deve registrar0
regressõesC43 e seleção focada. Candidate exige `--only all`; não usar a redução
para aceitar subconjunto ou ocultar a falha anterior.

## Complemento v1.7 antes do gate prolongado

Acrescentar crash outboundQoS1 após receber PUBLISH e antes de enviar PUBACK:
reconectar sessão persistente e exigir mesmo ID/bytes/flagDUP, permitindo duas
observações da mesma mensagem lógica. Manter casosQoS2. Agregar falhas paralelas
na ordem de conclusão, para que cancelamento secundário não esconda causa
primária. Recursos/testes continuam privados e budgets/duração não diminuem.

## Revisão v1.8 — startup da fixture externa

Reprodução focada baseline2:0cenários/1container, FAIL no startup; cleanup
1container/1volume PASS. A fixturev1.4 vinculou dois usuários ao mesmo cert,
enquanto AuthPolicy proíbe esse compartilhamento. Antes de corrigir, registrar
estado/exitcode e booleanos de diagnóstico sanitizados no startup; criar
certificado separado `fixture-writer`, com CA/SAN válidos e fingerprint próprio.
Não relaxar a política do broker. A falha baseline1 continua sem causa atribuída,
pois antecedeu esta segunda identidade e não tinha estágio detalhado.

## Revisão v1.9 — namespace Docker estável

Baseline3 iniciou broker, entregou primeiro payload e falhou após SIGTERM:
assinanteMosquitto exited7(CONN_LOST), estágio `publish_after_sigterm`.
Um cliente em `--network container:broker` permanece no namespace antigo
quando o ownerbroker é reiniciado/recria namespace. Correção do harness:
namespaceanchor privado independente com loopback/nonroot/sem portas, broker
e clients compartilham esse namespace estável; comparar namespace antes/depois
do restart. Isso não modifica código nem reduz a exigência de reconexão.
Fonte consultada: Mosquitto2.0.22 header enum(exit7CONN_LOST), sub_client.c
loop_forever e manual-W, não alegar que erro7 significa timeout27.

## Revisão v1.10 — comparar referência e lifetime externo

Baseline4 continuaFAIL apósnamespaceestável: primeiraMSGconferida,
Mosquitto_sub exited7 apósXMQR_SIGTERM,65.534s; cleanup5containers/1volumePASS.
Namespacefix não explica sozinho a falha. Acrescentar flags de diagnóstico
sem rawlogs e modo focado somenteMosquitto no baseline para comparar referência.
O-W8herdado de C43 é lifetime total do processo e inadequado para extensão com
várias operaçõesDocker; usar-W40 somente na extensão. C43 mantém-W8. Candidate
exige ambosbrokers/todosgates; timeoutobservado não viraPASS por aumentar budget.

## Revisão v1.11 — falha primária do ensaio prolongado

Candidate1 preservou2cenáriosPASS(rep1TCP600.215s/mTLS601.222s), mas falhou
na rep2~193s,795sdeparede. O report capturou cancelamento secundárioTCP em vez
da exceção primáriaMTLS: ordenação porfuturecompleted não resolve o atraso
do cleanup. Antes de retry, registrar primeira falha em fila atômica antes do
cancelamento, com etapa/operação/sequence e tipo sanitizados; manter resultados
parciais. Não mudar timeout/asserções nem declarar causa ou30minaceitos. Depois
reexecutar todas3repetições600s e reportar a causa se repetir.

## Critério v1.12 — espera ociosa não pode ser mascarada por retry

ReferênciaMosquitto2.0.22focada com-W40:12extensõesPASS,397.339s,
cleanup36containers/1volumePASS. Isso não é aceite de candidate/bothbrokers.
No gatecandidate de esperaociosa4.3s, exigir também ausência de marcador
`Reconexao` no XMQRclient antes de publicar; um processo ainda vivo porque
reiniciou a sessão após timeout não comprova separação de deadline/idle.

## Revisão v1.13 — filesystem e ENOSPC ambiental

Candidate2 FAIL136.107s: fila capturou TCP/liveQoS0/receive_fanout EOF, depois
brokerexit1. Diagnóstico readonly: `/tmp` é tmpfs3.9GiB100%/0free; `/var/tmp`
é ext4 `/dev/sdf`,946GiBfree. Não apagar arquivos externos/compilação de outros
agentes para liberar espaço. Usar `--state-root /var/tmp` existente e privado;
validar filesystemLinux nontmpfs/nonDrvFS/free>=512MiB antes de iniciar e
registrar FS/free/logmarkers/exitcode sanitizados em falhas. O ENOSPC do root
foi observado, mas não atribuir erro do processo sem marcador. Reexecutar
600x3 completos; não contar o ensaio abortado como30minPASS. FS/método mudou,
não o binário, os deadlines ou as asserções de protocolo.

## Revisão v1.14 — diagnóstico do probe sob carga

Candidate4ext4 FAIL255.679s: unhealthysingleprobe apósload, processo vivo,
946GiB livres, semmarcadoresENOSPC/EIO/panic/persistence. Monitoring usa probe
500ms (`src/monitoring.rs`), portanto um único0pode indicar atraso de ator/writer
durante pressão; isso ainda não é causa comprovada. Instrumentar métricas e
3reprobesquiescentes de diagnóstico, mantendo FAIL mesmo se recuperar.
Só depois da evidência/promptnovo definir recuperação saudável por prazo finito.
Não relaxar ACKs/bytes/QoS/erros persistência. Corrigir também oráculoQoS0:
DUP deve ser0 nas entregas, não mascarado pelo matcher de header; negativo
determinístico do harness antes de próximo gate prolongado.

## Diagnóstico v1.15 — fila controlada e recuperação por prazo

Smokeext4diagnóstico300s PASS emambostransportes sem reproduzir unready;
isso não prova que candidate4 foi falsoalarme. Criar `test_phase3_health.py`:
64publicadoresTCP válidos (limiteexistente), umQoS1retained/payload1024 cada,
amostrar monitor durante fila; conferir64PUBACKs/IDs/counter recebido, fechar
clientes e registrar probesquiescentes até15s comready1 eerrors0. Nenhuma
alteração do broker, timeoutACK ou fsync. Criar helperdeadline com negativos
determinísticos para neverready,errors>0,falsohealthy e respostas além prazo.
O diagnóstico podePASS seu método, mas não encerra600x3. Somente após trace
ready0→1/zeroerrors uma nova revisão adotará helper no ensaio prolongado.

## Revisão v1.16 — reproduzir encerramento TLS diretamente

Candidateexterno1:59C43PASS, depois SIGTERM XMQR causaMosquitto_subexit7,
timed_out=false/logicalevents1; namespaceestável/W40,cleanup128containers/
2volumesPASS. ReferênciaMosquitto reinicia e reconecta no mesmo harness.
Inspeção: `mqtt::serve_connection` retorna errode unregister antes de TLSshutdown
se ator já encerrou; transporttasks detached/main aguarda apenas routershutdown.
Criar `test_phase3_tls_shutdown.py` antes de corrigir core: PythonSSL strict
`suppress_ragged_eofs=False`, CA/SAN/cert/senhafixture válidos, TLS1.2/1.3,
controleDISCONNECTnormal e3SIGTERM/cada. Conferir EOF limpo vsSSLEOFError,
exit0do processo e tempos; sem logs/certs/senhas. Se demonstrar raggedEOF,
enviar ao coordenadorP94, mantendo FAIL e sem editar Rust nesta ownership.

## Complemento v1.17 — drain inclui handshake incompleto

Prova direta executada: control2PASS/SIGTERM6FAIL, strictSSLEOF emTLS1.2/1.3,
processoexit0, SHA d371d283. AgenteP95 assume exclusivamente core e pediu
cenário extra: conexão mTLS autenticada e socket paralelo com recordClientHello
incompleto, antesSIGTERM. Adicionar1caso/cadaTLS (total10), exigirEOF limpo
da conexão autenticada e término<=15.5s (budget15s +tolerância de observação).
Socketstall privado fica aberto até processoencerrar; não fechar antecipadamente
para artificialmente liberarpermit. Sem alterações de timeout/handshake do core.

## Refinamento v1.18 — proveniência e negativo de deadline

Prova adicional: baseline2 tem 2 controles PASS e 8 SIGTERM FAIL, inclusive os
dois handshakes incompletos. Antes do candidato P95, capturar SHA do executável
privado efetivamente testado e do harness no início, nunca recalcular a partir
de target/release potencialmente recompilado ao término. Copiar também admin
privado e registrar dependências da fixture; label baseline/candidate explícito.
Acrescentar negativo determinístico: resposta ready1 que chega após o deadline
não pode ser aceita pelo helper diagnóstico. O soak continua com oráculo strict
e três reprobes somente para diagnóstico; nenhuma adoção do helper nesta revisão.

## Refinamento v1.19 — falhas TLS sempre produzem relatório

Candidato P95 disponível. Antes do gate externo, garantir que timeout, exitcode
não zero ou falha de cleanup também sejam casos FAIL sanitizados no JSON, não
exceções sem report. Preservar causa primária e registrar cleanup separadamente;
não permitir que cleanup FAIL mantenha status PASS. Nenhuma alteração nos
requisitos EOF limpo, exit0, handshake ativo ou prazo15.5s.

## Complemento v1.20 — TLS estabelecido sem primeiro pacote MQTT

Revisão P95 encontrou caminho anterior à criação de BrokerConnection: TLS já
estabelecido, mas nenhum byte MQTT enviado. Antes de corrigir core, criar teste
separado `test_phase3_tls_no_connect.py`, mantendo fontes do soak em execução
intactas. Dois casos TLS1.2/1.3 com peerSSLstrict, fixture sintética, binários
privados imutáveis, handshake completo/nenhum CONNECT, SIGTERM, EOF limpo/exit0
e shutdown<=15.5s. Registro sanitizado inclusive FAIL. Se demonstrado, enviar
ao owner P95; runtime só ele altera. Uma nova versão do core exige repetir
gates finais completos; não reutilizar30min do executável anterior como aceite.

## Correção v1.21 — SAN da fixture no cenário sem CONNECT

Primeira tentativa do novo teste falhou antes do handshake: usou localhost,
mas certificado da fixture tem SAN IP127.0.0.1, como os clients existentes.
Antes de retry, corrigir somente server_hostname para127.0.0.1, mantendo CA/SAN
verification e SSLstrict; nunca desligar check_hostname ou validar certificado
por exceção. A tentativa CERTIFICATE_VERIFY_FAILED não prova defeito de runtime.

## Revisão v1.22 — recuperação quiescente comprovada, não SLA instantâneo

Soakcandidate5 strict FAIL268.599s preservado: mTLS/liveQoS2/pingbarrier,
ready0/active1/commits305/errors0; após.103s ready1/active0/commits306, mantém
ready1 em.208/.314s, filas/inflight0, processo vivo. Isso demonstra conclusão
do disconnect/commit depois de fechar clients, sem falha durável. Coordenador
autorizou antes do fix: adotar helper15s somente depois de tráfego quiescente,
mesmo processo/PID vivo e zeroerrors em todos probes; ready1 deve chegar dentro
do deadline absoluto, nunca aceitar resposta tardia. Registrar TODOS os probes,
counter/active/fila/tempo, com budget4000probes/cenário; budget excedido é FAIL.
Tempo de espera conta na duração observada e deadline total segundos+45s.
O helper se aplica também à leitura FINAL, que deve exigir ready1/errors0/PID
vivo dentro do prazo; repetir quotas/RSS/arquivos duráveis após essa espera.
Negativos determinísticos neverready, errorsEvenReady, readyAfterDeadline,
deadProcess antes/durante probe e trocaPID; trace0→1 não é escondido.
Sem relaxar bytes, ACKs, QoS, IDs, inflight, quotas, RSS ou arquivos duráveis.
Não converter candidate5FAIL nem alegar SLA500ms. Só depois de binário P95
sem-CONNECT final repetir3x600 e matriz87 completos.

## Refinamento v1.23 — distinguir HEAD de fonte ainda não commitada

Antes do gate congelado, incluir source_tree_dirty e SHA por arquivo Rust,
Cargo.toml e Cargo.lock no report prolongado, além de HEAD/binary/harnessSHA.
HEAD durante gates pode anteceder o commit coordenado; não afirmar que ele
contém sozinho o candidato compilado. Capturar SHA da cópia privada executada
broker/admin depois da cópia; fixture usa admin privado. Sem alterar runtime,
critérios ou duração. Coordenador mapeará esses hashes ao commit de publicação.
