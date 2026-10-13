# E01 — aceite físico ESP32 DevKit V1

Status atual2026-10-13/P84: retained create/update/replay/delete com observer
wire próprio independente do codec Rust PASS na COM4. Bytes dos loopbacks
também conferidos no host (entregas0/1/1 por assinaturaQoS1). Sem captura do
handshakeQoS2 da placa ou libmosquitto neste ensaio. Novos assinantes observaram
último valor1024bytes e não replay após exclusão na janela2s + PING vivo.
Will/reconexão/negativos/heap continuam pendentes. Broker/volume de teste
removidos; credenciais privadas/originais/backup preservados.
[RegistroP84](../prompts/registros/P84-e01-retained.md) e
[dados sanitizados](results/p84-e01-retained-2026-10-13.json).

Checkpoint2026-10-13/P83: primeira fatia física PASS na COM4. Senha corrigida
aplicada e recompilada; Wi-Fi/IP/SNTP/mTLS e loopback1024bytes/QoS0/1/2
confirmados. Scan isolado não é mais pré-condição; SDK tenta apenas AP
configurado com prazo limitado. Broker/volume de teste removidos. Firmware
diagnóstico permanece na placa; não existe broker permanente desse ensaio.
E01 global PARTIAL pelos cenários ainda pendentes, não pela senha/rede.
[RegistroP83](../prompts/registros/P83-e01-wifi.md) e
[dados sanitizados](results/p83-e01-wifi-2026-10-13.json).

Checkpoint histórico2026-10-13/P81: PARTIAL físico, BLOCKED por scan Wi-Fi sem alvo.
COM4/CH340 acessível, ESP32-D0WD-V3/rev3.0/4MiB confirmado. Duas leituras
completas do backup têm SHA256 idêntico; duas gravações/boots verificados.
Primeiro ensaio expirou Wi-Fi/IP; segundo scan direcionado não encontrou
o SSID configurado em2,4GHz. Windows também retornou zero correspondências.
Senha não foi avaliada; não diagnosticar senha incorreta por ausência do AP.
SNTP/mTLS/MQTT físicos continuam NOT_RUN. Firmware diagnóstico permanece
na placa; backup e credenciais são privados, serviços de teste removidos.
Veja [registroP81](../prompts/registros/P81-esp32-e01.md) e
[fixture Rust/ESP-IDF](../validation/esp32-e01/README.md).

RetomadaP82:40testes do coletor/guards PASS e observação real monitor-only na
COM4 confirmou novamente boot/WIFI_TARGET_NOT_FOUND_24GHZ/STOP. Nenhuma nova
gravação; firmware/NVS/backup preservados. Evidência restrita/sanitizada,
limites e veto a resultados contraditórios implementados. Isso não conclui
SNTP/MQTT nem substitui os gates abaixo. [RegistroP82](../prompts/registros/P82-e01-coleta.md).

ESP32 é consumidor, não alvo do broker. Não alterar firewall, Wi-Fi,
serviços instalados ou certificados reais por este guia. Conferir chip,
pinagem/LED da placa; não presumirGPIO2 universal.

## Checklist para execução real

- [x] Registrar placa/revisão/chip, porta, hash das fontes do firmware,
      RustESP1.97nightly/ESP-IDF5.5.5 e ambiente existente. EIM não alterado.
- [x] Boot/serial/reset reais PASS; backup completo consistente preservado.
- [x] Wi-Fi/IP de laboratório e SNTP antes do TLS, primeira associação P83.
- [x] Caminho positivo mTLS com CA/validade/SAN habilitados, sem insecure/fallback.
- [x] Certificado exclusivo da placa, usuário/senha MQTT e ACL mínima aceitos no ensaio.
- [x] Pub/sub com sequência e bytes sintéticos conferidos:1024bytes/QoS0/1/2 P83.
- [x] Confirmação de bytes/flags por fixture wire Python independente do codec/SDK P84;
      não é cliente terceiro completo nem atestado ELF↔Git/handshakeQoS2 MCU.
- [x] Retained create/replay/update/delete na placa e assinantes novos P84.
- [ ] Retained após restart do broker e campanha física com cliente terceiro.
- [ ] Will por reset/quebra real de link.
- [ ] QuedaWi-Fi/restartbroker, retry/backoff e duplicatasQoS1 observados.
- [ ] Negativos CA/SAN/senha/ACL recusados na placa.
- [ ] Heap/tempo de reconexão, ausência de loop ilimitado e evidência sanitizada.

ClientIDs devem ser distintos da CLI de diagnóstico. ACK não comprova negócio;
sessão no broker não comprova persistência no firmware. Nenhum log deve conter
SSID/senhaWi-Fi, chaves, hashes de senha ou payloadreal. Rotação/revogaçãoE02
fica na fase4; simulador/screenshot/fixtureDocker não substitui este gate.
