# E01 — aceite físico ESP32 DevKit V1

Status2026-10-13/P81: PARTIAL físico, BLOCKED por rede Wi-Fi não encontrada.
COM4/CH340 acessível, ESP32-D0WD-V3/rev3.0/4MiB confirmado. Duas leituras
completas do backup têm SHA256 idêntico; duas gravações/boots verificados.
Primeiro ensaio expirou Wi-Fi/IP; segundo scan direcionado não encontrou
o SSID configurado em2,4GHz. Windows também retornou zero correspondências.
Senha não foi avaliada; não diagnosticar senha incorreta por ausência do AP.
SNTP/mTLS/MQTT físicos continuam NOT_RUN. Firmware diagnóstico permanece
na placa; backup e credenciais são privados, serviços de teste removidos.
Veja [registroP81](../prompts/registros/P81-esp32-e01.md) e
[fixture Rust/ESP-IDF](../validation/esp32-e01/README.md).

ESP32 é consumidor, não alvo do broker. Não alterar firewall, Wi-Fi,
serviços instalados ou certificados reais por este guia. Conferir chip,
pinagem/LED da placa; não presumirGPIO2 universal.

## Checklist para execução real

- [x] Registrar placa/revisão/chip, porta, hash das fontes do firmware,
      RustESP1.97nightly/ESP-IDF5.5.5 e ambiente existente. EIM não alterado.
- [ ] Boot/serial/reset PASS; medição de heap ainda NOT_RUN.
- [ ] Wi-Fi de laboratório, reconexão limitada e SNTP antes de TLS.
- [ ] CA/validade/SAN validados, sem insecure/fallback.
- [ ] Certificado exclusivo da placa, senha e ACL mínima aceitos.
- [ ] Pub/sub com sequência e bytes conferidos; QoS0/1/2 somente conforme
      suporte comprovado do firmware/SDK. Registrar limites reais de memória.
- [ ] Retained replay/update/delete; Will por reset/quebra real de link.
- [ ] QuedaWi-Fi/restartbroker, retry/backoff e duplicatasQoS1 observados.
- [ ] Negativos CA/SAN/senha/ACL recusados na placa.
- [ ] Heap/tempo de reconexão, ausência de loop ilimitado e evidência sanitizada.

ClientIDs devem ser distintos da CLI de diagnóstico. ACK não comprova negócio;
sessão no broker não comprova persistência no firmware. Nenhum log deve conter
SSID/senhaWi-Fi, chaves, hashes de senha ou payloadreal. Rotação/revogaçãoE02
fica na fase4; simulador/screenshot/fixtureDocker não substitui este gate.
