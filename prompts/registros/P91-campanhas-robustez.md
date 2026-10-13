# Registro P91 — B08: campanhas de robustez

Data:2026-10-13. Pedido explícito de finalizar fase3, trabalho paralelo com
ownership dos harnesses, sem editar Rust/client/versões ou publicar neste agente.
Entrada brokerd467bf3/runtime0.11.5; P89/P90/P93/C45/P92 paralelos preservados.
Prompt preparado antes de código: [P91](../broker/91-campanhas-robustez.md),
revisões reais registradas após falhas e antes de corrigir harnesses.
Skills xmqr-tests e xmqr-security-review guiaram negativos, oráculo wire
independente, estados temporários, mTLS/ACL e distinção entre evidências.

## Ambiente e proteção

Ubuntu26.04/WSL2 kernel6.18.33.2, Python3.14.4. Smoke inicial em `/tmp` privado;
diagnóstico posterior confirmou tmpfs100%: candidato prolongado final passa
a exigir filesystemLinux disk-backed `/var/tmp`ext4,>=512MiB livres.
DockerDesktop Linuxamd64 controlado pelo CLI Windows; Python3.13 Windows e
OpenSSL Git existente. Nenhuma instalação ou instância do operador alterada,
nenhum firmwareESP32, senhaWi-Fi ou certificado privado real lido. Código MIT.

## Resultados intermediários realmente executados

- `python scripts/test_phase3_harness.py`:13testes PASS, exit0, repetidos após
  alterações do harness. Negativos de falta/bytes/QoS/retain/duplicaçãoQoS2;
  retransmissõesQoS1 legítimas não causam falsa falha. O oitavo teste forçaEOF
  primário seguido de cancelamento paralelo e comprova que diagnóstico primário
  não é substituído pela falha secundária. Posteriores negativosQoS0/DUP e saúde:
  neverready, erro persistente mesmo ready1, transiente registrado e ready1
  posterior ao deadline rejeitado. O helper diagnóstico não é adotado pelo soak.
- Smoke nativebaseline0.11.5,8s/TCP+mTLS:primeiroFAIL na rotina offlineQoS2.
  Diagnóstico revelou pressuposto inválido de PUBREL imediatamente depois de
  cada PUBREC quando outros PUBLISH do lote estavam enfileirados. P91v1.2
  corrigiu contabilidade em lote, sem mudar core ou diminuir asserções.
- Smoke3PASS(TCP8.004s/mTLS9.049s); após complementoQoS1, smoke4PASS
  (TCP8.179s/960pub/3840fanout; mTLS8.376s/336pub/1344fanout). Em cada transporte:
  retainedSIGTERM/restart, offlineQoS1/2, inboundPUBRECcrash, outboundPUBRELcrash
  e outboundQoS1replay com mesmoID/DUP. Não são ensaios prolongados de aceite.
- Wirebaseline19vetores:17PASS,2FAIL(ClientIDvazioCS0/1 fechava sem CONNACK2),
  enviado ao coordenadorP93 antes de correção. Tentativa WSL anterior falhou no
  transporte0x8007274c antes de executar; retry normal funcionou sem instalação.
- C43 externo baselinebroker0.11.5/client0.8.1:59/59regressõesPASS. Extensão
  FAIL após59,458.703s, readiness timeout sem estágio detalhado. Não atribuir
  a defeito do client/broker sem dados. Recursos próprios removidos e listagem
  posterior confirmou0containers da campanha.
- Baselinefocado2:0cenários, FAILstartup,27.879s,1container/1volume removidos.
  A nova fixture de segunda identidade compartilhava fingerprint, proibido por
  AuthPolicy. P91v1.8 adicionou certificado independente e diagnóstico sanitizado.
- Baselinefocado3: primeira publicação conferida; FAILapósSIGTERM,
  estágio`publish_after_sigterm`, subscriberMosquitto exited7(CONN_LOST),44.507s;
  cleanup4containers/1volumePASS. P91v1.9 corrigiu ambiente: namespaceholder
  estável em vez de namespace do broker recriado após Dockerrestart. A próxima
  execução exige comparação do namespaceantes/depois; não relaxa reconexão.
- Baselinefocado4 manteve namespaceestável, mas aindaFAILapósSIGTERM:
  Mosquitto_subexited7,65.534s,cleanup5containers/1volumePASS. Não atribuir
  a namespace sozinho nem ao C45. P91v1.10 elevou-W8(lifetime total inadequado)
  para-W40apenas na extensão; C43mantém-W8.
- ReferênciaMosquittofocada após ajuste:12/12cenáriosPASS,397.339s,
  cleanup36containers/1volumePASS; ambosclients/sentidos de pub/sub,
  persistentQoS1/2SIGTERM,retainedcrash/explicitautosave e negativosACLpub/sub.
  É baseline/onlyMosquitto, não aceite de candidate/bothbrokers.

## Candidato final em validação

Coordenador confirmoufreeze do runtimebroker0.11.6 em2026-10-13:
binarySHA256`d371d2834bc8f0d0f0bbd02ecd76393e4b8a88fb78465f5ed85fa7cad6b88903`;
adminlegadoSHA256`2cedc11d00c0a536501f0290741cba011fccb1e0b9b86ea5d127fa12a755d720`.
O harness copia broker para arquivo privadoimutável antes de iniciar/reiniciar.

- Wirecandidate `test_phase3_wire.py --broker target/release/mqtt-broker
  --label candidate`:19/19PASS, exit0; vaziosCS0/1CONNACK2 antesclose;
  keepalive1s fechou em1.503s; flags/UTF8/idzero/filtros/framingPASS.
- Soakcandidate1: rep1TCP600.215s/61368pub/245472fanout e mTLS601.222s/
  22608pub/90432fanoutPASS. Cada15crashes+5SIGTERM,readiness1 eerrors0.
  Campanha completaFAIL795.000sna rep2; report preserva2cenáriosPASS, mas
  cancelamento secundário ocultou erro primário. P91v1.11 corrigiu diagnóstico.
- Soakcandidate2:FAIL136.107s; primárioTCP/liveQoS0/receive_fanoutEOF,
  sequence14008; cleanupbrokerexit1. Readonlydf confirmou/tmp3.9GiBtmpfs100%,
  0free; `/var/tmp`ext4/dev/sdf946GiBfree. SemmarcadorprocessonãoprovarENOSPC
  como causa exata, mas ambiente inadequado observado; P91v1.13 mudaFS/check.
  Nenhum arquivo externo apagado ou deadline reduzido. AmbosFAIL preservados.
- Terceiro launchWSLfalhou0x8007274c antesPython, semreport/resources;
  retryviaWSL--execPython absoluto comstate-root/var/tmp preparado. Resultado
  prolongado final continua pendente; 3repetições>=600s/TCP+mTLS são obrigatórias.
- Soakcandidate4 em `/var/tmp`:FAIL255.679s, probe single unhealthy,
  TCP/liveQoS2/pingbarrier/nextsequence2736; processo vivo, espaço disponível,
  semmarcadoresENOSPC/EIO/panic/persistence. Causa ainda não comprovada. P91v1.14
  registra três reprobes quiescentes mantendo FAIL se repetir, sem relaxar saúde.
- Diagnóstico300s:PASSTCP301.192s/2712pub/10848fanout,
  mTLS300.367s/2400pub/9600fanout, cada9crashes+3SIGTERM; sem observar ready0.
  Burstdiagnóstico64clientes×3:192PUBACKsPASS/1.860s, ready1 em todos probes,
  errors0. Nenhum desses testes reproduz ready0→1 ou aceita o gate600x3.
- Interopcandidate1:59C43PASS, extensãoFAIL no primeiro SIGTERMXMQR→Mosquitto;
  CONN_LOSTexit7, timed_out=false, logicalevents1;302.517s,cleanup128containers/
  2volumesPASS. Imagens broker0.11.6ID2f829190/client0.9.0IDe1c56183,
  brokerrev04e31d4. ReferênciaMosquitto passou nesse mesmo método após ajustes.
- ProvaTLSdireta baseline1:2DISCONNECTPASS/6SIGTERMFAIL emTLS1.2/1.3,
  `SSLEOFError/UNEXPECTED_EOF_WHILE_READING`, brokerexit0. Inspeção e prova
  enviadas ao coordenador e ao owner P95 antes de corrigir runtime.
- ProvaTLSdireta baseline2:2DISCONNECTPASS/8SIGTERMFAIL, incluindo os2casos
  com socket paralelo de handshake incompleto mantido aberto; exit0 em todos,
  shutdown.032–.123s. Binário d371d283, harnessSHA
  `b2b85b25c16279af291679a05f5655de05857c5e3b0d879caf584b435f693398`.
  Report `p91-tls-eof-baseline-2.json`. A prova demonstra EOF TLS truncado; não
  é apenas timeout, namespace ou hipótese sobre client. Core pertence ao P95.

P91v1.18 captura SHA do executável privado/harness antes do ensaio para impedir
proveniência falsa se target/release for recompilado depois. GateTLS10, wire19,
soak600x3 e matriz87 serão repetidos no SHA/imagem finais P95. Não há aceite
parcial ou conversão dos FAIL anteriores em PASS.

Reports intermediários ficam em`../.artifacts/p91-*.json` fora deste Git;
somente reports finais sanitizados serão anexados/versionados pelo coordenador.
Nenhum hash de senha, PEM/chave, estado, rawlogs ou credencial faz parte deles.

## Limitações e publicação

Sem alegação de conformidade exaustiva, throughputmáximo/SLA, perda de energia,
estabilidade de dias, MSRVexato, Windowsbroker/arm64 ou ESP32nova. Counters do
monitor reiniciam por processo; memória é RSSamostrada, não heap nem prova
global contra vazamentos. B08 e fase3 não são aceitos por este registro parcial.
Commit/push/tag/deb/Hub ficam com coordenador após gates e commitexato.
