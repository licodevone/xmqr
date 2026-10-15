# P102 — campanha física E02 na COM4

- Prompt [P102](../broker/102-esp32-e02-rotacao.md) criado antes do firmware e
  harness. Modo E02 exclusivo, seis etapas finitas e sinais SIGUSR1; certificados
  e CRLs gerados somente no diretório privado. Fonte e build não contêm senhas.
- Verificados CH340/ESP32-D0WD-V3/4MiB na COM4, dois backups originais 4MiB
  idênticos, SAN IP e validade de CA/servidor/board, cross-build Rust release,
  formato e imagem Docker do broker. App 993136 bytes dentro da partição 1MiB;
  flash esptool verificado. Broker isolado e CRL inicial passaram mTLS host.
- Primeira tentativa: `E02_FAIL stage=WIFI_ASSOCIATION_TIMEOUT`; o SSID privado
  estava ausente. Após a rede 2,4 GHz voltar, a senha do arquivo Wi-Fi diferia
  da configuração incorporada. `sync_wifi.py` criou backup privado, sincronizou
  e o firmware E02 foi recompilado. Nenhum segredo foi copiado para o Git.
- Segunda tentativa: handshake inicial mTLS PASS; o harness alcançou
  `INVALID_KEY_ROLLBACK_READY`, mas lia somente stderr do Docker e não confirmou
  o marcador de rotação emitido em stdout. P102 rev13 corrigiu a leitura dos
  dois fluxos, com contadores anteriores/posteriores, antes da repetição.
- Terceira tentativa: **PASS_PHYSICAL_CAMPAIGN**. A placa emitiu os 16 marcos em
  ordem, incluindo baseline, seis pares READY/PASS, `E02_PHYSICAL_PASS` e
  `E02_STOP`. Os seis SIGUSR1 cobriram chave inválida com rollback, novo
  certificado, CA estranha rejeitada, recuperação da CA, CRL revogada e
  recuperação da CRL. Docker container e volume de teste removidos e ausência
  confirmada ao final. Evidência pública sanitizada em
  [JSON](../../docs/results/p102-e02-2026-10-15.json).
- Aceite físico limitado à campanha finita; não implica teste de energia,
  duração longa, revogação de sessões ativas nem prontidão para produção.
