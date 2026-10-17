# P142 rev1 — Response Topic, Correlation Data e User Property em PUBLISH MQTT 5

Entrada: iniciar código somente após P141/C77 aceitos em CI; broker publicado 0.21.0, documento de desenvolvimento v9, fase 6C aberta. Este prompt precede a funcionalidade. Fonte normativa: [OASIS MQTT 5 §3.3.2.3.5–7](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html).

Objetivo: aceitar e encaminhar sem alteração Response Topic `0x08` (tópico MQTT válido sem wildcards, até 1024 bytes), Correlation Data `0x09` (binário de até 256 bytes) e User Property `0x26` (pares repetíveis em ordem, cada campo até 256 bytes, até 2048 bytes codificados e 16 pares) no PUBLISH MQTT 5. Preservar em QoS2, retained, offline e replay após restart; documento durável v10 com leitura de v1–v9. Usar regras de Maximum Packet Size e Topic Alias existentes. MQTT 3.1.1 recebe apenas tópico e payload. Não interpretar metadados como ACL/credenciais nem registrar valores em logs. Will Properties, Subscription Identifier e AUTH permanecem fora desta fatia.

Aceite: vetores positivos/negativos de duplicatas proibidas, UTF-8, wildcard em Response Topic, comprimento, limite cumulativo e ordem/repetição de User Property; TCP real QoS0/1/2, retained/restart, client C78 e Mosquitto, ACL/limite de pacote, migração v9→v10, regressões P130/P139/P141, fmt/test/Clippy/build/CI. Documentar rollback com backup privado v9, checklist desmarcado até aceite, commit/push sem release isolada. Sem ensaio físico ESP32.

Rev2 antes da correção: o primeiro gate Clippy apontou funções de saída acima de 100 linhas e assinatura de serialização `&Option`. Extrair validação/serialização das propriedades para funções próprias e manter a assinatura exigida pelo Serde com justificativa localizada; repetir Clippy e testes.

Rev3 antes da correção: manter os dois fluxos de codificação e entrega coesos, com exceções Clippy locais e justificadas para o tamanho, evitando espalhar argumentos de segurança e limites em helpers; Serde exige `&Option` no adaptador `with`. Repetir gates.
