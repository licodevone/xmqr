# P123 rev1 — propriedades informativas de CONNECT MQTT 5

Entrada: `main` `21162ec`, versão publicada 0.16.0, árvore limpa; P122/C63 aceitos. CONNECT 5 aceita apenas Session Expiry=0 e Receive Maximum válido. Fase 6A permanece aberta.

Objetivo: aceitar em CONNECT 5 Request Problem Information (0x17), Request Response Information (0x19), Topic Alias Maximum (0x22) e User Property (0x26), além das propriedades anteriores. Validar valor 0/1 e unicidade das duas flags, unicidade de Topic Alias Maximum e pares UTF-8 íntegros. O broker ainda não envia Reason String, User Property, Response Information nem Topic Alias; portanto não armazena nem reutiliza os valores. Propriedades fora do subconjunto, inclusive AUTH, expiração não-zero e Maximum Packet Size, continuam recusadas. Fonte: [OASIS MQTT 5 §§3.1.2.11.5–11.9](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html).

Escopo: `src/mqtt/codec.rs`, testes de contrato/interop e documentação. Sem alteração de estado durável, quotas, ACL, transporte, MQTT 3.1.1 ou versão. O pacote completo continua limitado a 64 KiB; propriedade recebida não é ecoada, persistida ou registrada.

Aceite: CONNECT 5 com cada propriedade e combinação passa; duplicatas, booleano inválido, UTF-8 malformado/truncado e propriedade ainda não suportada falham sem autenticação/commit. Integração MQTT real e gates fmt/test/Clippy/build/CI. Marcar apenas a fatia P123; não encerrar 6A.
