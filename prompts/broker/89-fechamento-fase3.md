# P89 v1 — encerrar fase3 robustez, sem iniciar fase4

Preparado2026-10-13 antes de mudanças. Pedido explícito: finalizarfase3,
mantendo prompts→implementação→gates→registro→commit/push→tags aceitas→
releases/deb/DockerHublepinheiro100. Agentes paralelos previamente autorizados.
Entrada confirmada: brokerd467bf3f7f654be6aa133cefe4ad07ff0e6818fb/runtime0.11.5
clean; clientd9d97d51b88832044c8d2de3786ce4262ee77ec1/runtime0.8.1, preservar
dois arquivoslocais0.7.1; admin ec67ce292be60e130e37076104a03d1734317f86/0.1.0
clean, corepin3606ede. Fase2aceita, B06P86/P87aceito, B07/B08/C07pendentes.
Pastaagora acmebr-projects/acmebr-broker-client,3repos,nãoCargoWorkspace.

## Fatias e ownership

- P90/B07 agenteRust: preparar promptantesfuzz/tests/CI/docfuzz; codec,
  filtros e estado/roteador, corpus sintético versionado pequeno, mutações
  repetíveis, watchdog/limites, crashes minimizados e regressõesantesfix.
  Ruststable disponível; cargo-fuzz/nightly não instalados. Mutationalfuzz
  próprio é execução real de mutações, não cobertura-guided/LibFuzzer/ASAN.
  Não instalarferramentas globais nem declarar esses gates ausentesPASS.
- C45/C07 agenteclient: prompt próprioantesCLI/session/tests/docsclient;
  prazos protocolo/idle/total separados, retry limitado/jitter/cancelamento,
  QoS1retransmissões legítimas, pubdesconhecida sem reenvio, QoS2recebidofail
  explícito conforme limitação rumqttc. Sem relaxar TLS/SAN ou leak.
- P91/B08 agenteinterop: promptantes harnesses/ensaios/matrizampliada;
  Mosquitto2.0.22 pinadoDocker existente, ambos sentidosmTLS/ACL e falhasrede,
  pressão/recuperação repetida com duração declarada e taxas/budgets reais,
  retenção/offline/inflight, retomada e invariantesQoS. Logssemsecrets.
- Coordenador: fechamento de gapsnormativos demonstrados em prompt próprio,
  revisão cruzada, gatesintegrados, versão/release e quadrophase3-acceptance.

## Critérios e limites

OASIS3.1.1+errata fonte normativa confirmada no início. Rastrear capítulos
CONNECT/ClientID/flags/UTF8, ACKs e retransmissão, sessões/keepalive,
SUBSCRIBE/UNSUBSCRIBE, retained/Will/$ e quotas. Matrixampliada por requisitos
do subconjunto anunciado: não chamarconformidade integral nem abrirmqtt5.
B06 será reexecutado no código final, não inferido só do registroP86.
Cadafatia registra entradas, negativos, seed/corpus/método/tempo/ambiente/
resultados; sem checklistconcluído peloarquivoexistir. Fase3só ACCEPTED
quando B06+B07+B08+C07PASS no recorte executado e rastreável. Lacunas fora
do recorte (energia/SLA/campanha dias/LibFuzzer/MSRVexato/Windows/arm64) claras.

Preservar MITprópria/avisosoriginais, backendsecure-mtls padrão, labsloopback,
budgets1024UTF8/4096/65536, ACLdenybydefault/restore, conexões/gerações/commit
durávelantesACKs, limitesfilas e formatos de estado. Testsprivados emLinux
filesystemtemporário; Dockerrecursos próprios, sem portasadmin/LAN, sem
firewall/serviço real/credenciais do operador/firmwareESP32. Não ler C:/x81.
Store/actor não seráaberto por segundo writer nem modificado pelo painel.

Gatesfmt/testlocked/clippy-Dwarnings/build/inventário e integrações
proporcionais, fuzzreal, campanha prolongada explícita, clienteindependente,
segurança e ciclo deartefatos dessecommit. Falha: revisar promptantesfix.
Publicar apenas marcosaceitos: versõesindependentes escolhidas por conteúdo,
tagvX.Y.Z imutável, prerelease/.debUbuntu26amd64 e DockerBookwormnonroot,
SHA/provenance/digestremoto conferidos; semforce/overwrite/latest. Admin0.1.0
compatível será exercitado, sem repinar/removerlegado automaticamente.
Finalizarfase3não autoriza implementarlisteners/fase4, MQTT5 ou canaisadmin.
