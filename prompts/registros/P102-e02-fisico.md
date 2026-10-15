# P102 — campanha física E02 na COM4

- Prompt [P102](../broker/102-esp32-e02-rotacao.md) criado antes do firmware e
  harness. Modo E02 exclusivo, seis etapas finitas e sinais SIGUSR1; certificados
  e CRLs gerados somente no diretório privado. Fonte e build não contêm senhas.
- Verificados CH340/ESP32-D0WD-V3/4MiB na COM4, dois backups originais 4MiB
  idênticos, SAN IP e validade de CA/servidor/board, cross-build Rust release,
  formato e imagem Docker do broker. App 993136 bytes dentro da partição 1MiB;
  flash esptool verificado. Broker isolado e CRL inicial passaram mTLS host.
- A placa emitiu `E02_BOOT fixture=0.1.0`, depois
  `E02_FAIL stage=WIFI_ASSOCIATION_TIMEOUT`. Nenhum SIGUSR1 físico foi executado.
  A varredura Windows atual não mostra o SSID privado da campanha E01; a rede
  usada pelo host também não é esse SSID. Recursos Docker foram limpos.
- Resultado: **BLOCKED_WIFI_ASSOCIATION** para E02. Não marcar aceite físico,
  nem fase 4 completa. Retomar o mesmo harness após a rede 2,4 GHz estar
  visível, repetindo preflight/backup e a campanha; registrar então cada etapa
  de certificado/CA/CRL e recuperação. Evidência pública sanitizada em
  [JSON](../../docs/results/p102-e02-2026-10-15.json).
