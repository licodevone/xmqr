# P91 v1.17 — B08: campanhas limitadas de robustez e interoperabilidade

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
