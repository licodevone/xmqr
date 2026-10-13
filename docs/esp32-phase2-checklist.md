# E01 — aceite físico ESP32 DevKit V1

Status2026-10-13: BLOCKED/NOT_RUN físico. Windows não apresentou porta
Win32_SerialPort; WSL não apresentou ttyUSB/ttyACM/serial-by-id.
Não acessar/flashear firmware sem alvo identificado. Ausência de porta
acessível não comprova ausência de placa no computador do usuário.

ESP32 é consumidor, não alvo do broker. Não alterar firewall, Wi-Fi,
serviços instalados ou certificados reais por este guia. Conferir chip,
pinagem/LED da placa; não presumirGPIO2 universal.

## Checklist para execução real

- [ ] Registrar placa/revisão/chip, porta, firmwarecommit e Rust/ESP-IDF/EIM.
- [ ] Boot/serial/heap/reset observados com timeouts definidos.
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
