# P162 rev1 — Server Keep Alive MQTT 5 por limite configurável

Entrada: o broker usa o Keep Alive do CONNECT e tempo de inatividade de 1,5×, mas não envia Server Keep Alive (propriedade CONNACK `0x13`). O client 0.25.0 usa `rumqttc` 0.25.1, cujo laço de eventos já lê essa propriedade. Versões publicadas permanecem broker 0.28.0/client 0.25.0; este prompt precede o código.

Objetivo: admitir `MQTT_SERVER_KEEP_ALIVE_SECONDS` opcional (TOML `[broker].server_keep_alive_seconds` ou ambiente), inteiro 1..65535, validado no startup. Para MQTT 5, quando CONNECT envia Keep Alive zero ou maior que o teto configurado, CONNACK de sucesso deve anunciar `0x13` com o teto e o broker deve usar exatamente esse valor para o prazo de 1,5×. Quando CONNECT já é menor/igual ao teto, omitir `0x13` e preservar o valor do cliente. MQTT 3.1.1 e ausência da opção não mudam. Se Maximum Packet Size do cliente impedir a propriedade obrigatória para essa negociação, recusar o CONNECT com 0x95 antes de criar sessão; propriedades opcionais de CONNACK podem ser omitidas conforme seus contratos existentes. Não alterar o documento durável v14.

Aceite: validação de TOML/ambiente e limites; bytes CONNACK e ausência de duplicidade; CONNECT zero, menor, igual e maior; pequeno Maximum Packet Size sem sessão criada; inatividade/PINGREQ com relógio controlado ou socket real; client independente confirma negociação em teste, mantendo regressão 3.1.1. Fmt, Rust, Clippy, build, licenças, contrato de distribuição e CI do commit exato. Registrar parcela 6A, sem tag/release isolada ou alegar fase concluída.

Fonte normativa: [MQTT 5 §3.2.2.3.14 e §3.1.2.10](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html).
