# P163 rev1 — metadados do Will MQTT 5 no broker

Entrada: P132 aceita Will Delay e o estado v14 já preserva nos `StoredMessage` os metadados MQTT 5 de PUBLISH: Payload Format Indicator, Content Type, Response Topic, Correlation Data e User Property ordenada. O parser de Will Properties no CONNECT ainda aceita apenas Will Delay. O admin independente 0.9.0 lê v14; este prompt precede o código.

Objetivo: aceitar no Will Properties MQTT 5 `0x01`, `0x03`, `0x08`, `0x09` e `0x26` além de `0x18`, com tipos, multiplicidade e limites equivalentes ao PUBLISH (Content Type até 256 bytes; Correlation Data até 256; até 16 pares/2048 bytes), inclusive propriedades em ordem arbitrária. Preservar a ordem dos User Properties até o PUBLISH do Will, retained, fila offline e recuperação após restart. Rejeitar duplicatas proibidas, valor PFI diferente de 0/1, tópico de resposta inválido, payload truncado, propriedades desconhecidas e orçamento excessivo antes da sessão. Sem mudar o documento v14; não adicionar Message Expiry Interval do Will `0x02` nesta parcela, pois seu prazo começa na publicação e requer contrato durável próprio/admin compatível.

Aceite: vetores de codec válidos/negativos; conexão real com Will imediato e atrasado, assinante MQTT 5 verificando bytes/metadados e ordem, retained/restart; integração com client C94 e regressão MQTT 3.1.1/Will Delay. Fmt, Rust, Clippy, release build, licenças, contratos de distribuição e CI do commit exato. Registrar parcela 6A/6B sem tag isolada nem fechar fases globais.

Fonte: [MQTT 5 §3.1.3.2](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html).
