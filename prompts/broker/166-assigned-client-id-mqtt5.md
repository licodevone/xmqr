# P166 rev1 — Client Identifier atribuído pelo broker em MQTT 5

Entrada: a fase 6A ainda não cobre CONNECT MQTT 5 com Client Identifier vazio. O [padrão OASIS MQTT 5, seções 3.1.3.1 e 3.2.2.3.7](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html) exige que, ao aceitar esse CONNECT, o broker atribua um identificador novo e o devolva na propriedade CONNACK `0x12`. Este prompt precede o código.

Objetivo: aceitar Client Identifier vazio somente no MQTT 5, gerar identificador imprevisível e exclusivo entre sessões ativas/duráveis, registrar a sessão sob o mesmo identificador (com escopo interno do listener quando houver) e enviar a propriedade `0x12` obrigatória. Preservar a recusa MQTT 3.1.1 e as políticas de autenticação/ACL. Falhar sem registrar sessão se o Maximum Packet Size do cliente não comportar o CONNACK obrigatório. Não alterar estado durável além das regras existentes da sessão.

Aceite: codec de CONNACK, colisão forçada no ator, conexão TCP real com dois clientes vazios simultâneos e reconexão pelo ID recebido, Clean Start e Session Expiry, limites de pacote e autenticação/ACL negativas; regressão MQTT 3.1.1, suites Rust/fmt/Clippy, CI do commit exato e registro factual. Sem marcar 6A global como concluída nem publicar release isolada automaticamente.
