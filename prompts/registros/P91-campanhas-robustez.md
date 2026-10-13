# Registro P91 — B08: campanhas de robustez

Data:2026-10-13. Pedido explícito de finalizar fase3, trabalho paralelo com
ownership dos harnesses, sem editar Rust/client/versões ou publicar neste agente.
Entrada brokerd467bf3/runtime0.11.5; P89/P90/P93/C45/P92 paralelos preservados.
Prompt preparado antes de código: [P91](../broker/91-campanhas-robustez.md),
revisões reais registradas após falhas e antes de corrigir harnesses.
Skills xmqr-tests e xmqr-security-review guiaram negativos, oráculo wire
independente, estados temporários, mTLS/ACL e distinção entre evidências.

## Ambiente e proteção

Ubuntu26.04/WSL2 kernel6.18.33.2, Python3.14.4, filesystemLinux `/tmp` privado.
DockerDesktop Linuxamd64 controlado pelo CLI Windows; Python3.13 Windows e
OpenSSL Git existente. Nenhuma instalação ou instância do operador alterada,
nenhum firmwareESP32, senhaWi-Fi ou certificado privado real lido. Código MIT.

## Resultados intermediários realmente executados

- `python scripts/test_phase3_harness.py`:7testes PASS, exit0, repetidos após
  alterações do harness. Negativos de falta/bytes/QoS/retain/duplicaçãoQoS2;
  retransmissõesQoS1 legítimas não causam falsa falha.
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

## Candidato final em validação

Coordenador confirmoufreeze do runtimebroker0.11.6 em2026-10-13:
binarySHA256`d371d2834bc8f0d0f0bbd02ecd76393e4b8a88fb78465f5ed85fa7cad6b88903`;
adminlegadoSHA256`2cedc11d00c0a536501f0290741cba011fccb1e0b9b86ea5d127fa12a755d720`.
O harness copia broker para arquivo privadoimutável antes de iniciar/reiniciar.

- Wirecandidate `test_phase3_wire.py --broker target/release/mqtt-broker
  --label candidate`:19/19PASS, exit0; vaziosCS0/1CONNACK2 antesclose;
  keepalive1s fechou em1.503s; flags/UTF8/idzero/filtros/framingPASS.
- `phase3_soak.py --seconds600 --repetitions3 --labelcandidate`: iniciado,
  resultado final ainda pendente. Primeiroheartbeat60s:TCP8712pub/34848fanout,
  RSS7092KiB; mTLS4560pub/18240fanout,RSS28968KiB; retomadas/probes sem erro.
  RUNNINGnãoequivale a aceite; aguardar3repetições>=600s em ambos transportes.
- Interopcandidate com imagens finais: ainda pendente neste checkpoint.

Reports intermediários ficam em`../.artifacts/p91-*.json` fora deste Git;
somente reports finais sanitizados serão anexados/versionados pelo coordenador.
Nenhum hash de senha, PEM/chave, estado, rawlogs ou credencial faz parte deles.

## Limitações e publicação

Sem alegação de conformidade exaustiva, throughputmáximo/SLA, perda de energia,
estabilidade de dias, MSRVexato, Windowsbroker/arm64 ou ESP32nova. Counters do
monitor reiniciam por processo; memória é RSSamostrada, não heap nem prova
global contra vazamentos. B08 e fase3 não são aceitos por este registro parcial.
Commit/push/tag/deb/Hub ficam com coordenador após gates e commitexato.
