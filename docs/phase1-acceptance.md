# Aceite da fase1 — concluído em Ubuntu26/WSL

Estado: **PHASE1_ACCEPTED**, 2026-10-11, P61/C39. Broker0.11.0 e client0.7.0.
Critérios de código, integração e pacote satisfeitos. Não é conformidade MQTT
completa nem prontidão para produção; fase2 não iniciada.

| Critério | Resultado real |
| --- | --- |
| Quotas TOML/defaults/overrides e negativos | PASS:103 testes broker |
| Redução sem descarte, v1/v2 e Will saturada | PASS:12 imagens, hashes preservados/reabertura; testes internos e7 cenários reais |
| Pacote65536/N+1 e payload4096/N+1 | PASS: codec/client e fronteiras reaisQoS0/1/2 |
| Client, timeout/keepalive e diagnósticos | PASS:52 testes(31unit+21wire), C38 real |
| QoS/retained/offline/inflight/reconexão/TLS | PASS:P54/P55/Will/C27/C38, fontes congeladas |
| Cliente independente Mosquitto | PASS:4 cenários open-lab Mosquitto2.0.22 |
| systemctl/mTLS e shutdown | PASS:start/pub/sub/reload/restart/stop em units temporárias;3 regressões shutdown |
| Instalação/upgrade/rollback/remove/purge | PASS:containerUbuntu26amd64; documentos/arquivos/estado fictício preservados |

Runner final: target/phase1-20261011T232424Z-scjb4yeg/summary.json,
UNIT_INTEGRATION_PASS. phase1_accepted=false no runner é intencional: ele não
executa pacote. O aceite combinado P61 agrega lifecycle separado; resultado
bruto preservado. Não foram promovidos testes ignorados ou bloqueados aPASS.

## Compatibilidade e limites

Defaults e formato de estado preservados. Redução incompatível recusa startup
sem truncar imagem; recuperar restabelecendo quotas suficientes. TOML opt-in:
instalação não ativa MQTT_CONFIG nem troca broker.env.

Broker/envioSUBSCRIBE contam pacote completo65536. Clientrumqttc reserva
header5, recebe corpo até65531 e pode recusar frame canônico65536 por1byte.
Diferença defensiva explícita; TLS/SAN e autenticação preservados.

Testes isolados não operaram/desinstalaram/atualizaram os softwares em uso.
Estado de pacote é fictício, não substitui replayMQTT validado separadamente.
Ubuntu24, arm64, Windowsbroker e MSRV1.88 exato não homologados neste marco.
InteropMosquitto aberta não equivale aTLS/ACL externa: mTLS foi coberto pelo
client próprio e pelas units temporárias systemd.

## Evidências

- [P61 — tentativas, gates e publicação](../prompts/registros/P61-aceite-final-fase1.md)
- [C39 — client](../../xmqr-client/prompts/registros/C39-release-fase1.md)
- [Contrato de pacote](phase1-package-acceptance.md)

Próxima entrega: prompt da fase2 para medição RAM/CPU/latência/mensagens/s.
