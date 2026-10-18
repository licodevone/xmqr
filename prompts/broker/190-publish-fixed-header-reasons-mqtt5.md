# P190 v1 — motivos MQTT 5 para flags PUBLISH inválidas

Estado de entrada: `main` limpo em `063419534bad98dd8dbb2acd9857fc9cd61cf9ff`, broker 0.33.0, estado durável v15. P189 aceito. O codec já recusa QoS reservado 3 e DUP=1 com QoS 0, mas após CONNACK MQTT 5 apenas fecha a conexão sem motivo.

Objetivo observável: um PUBLISH MQTT 5 com ambos os bits QoS ligados recebe DISCONNECT `0x81` (Malformed Packet); um PUBLISH QoS 0 com DUP ligado recebe DISCONNECT `0x82` (Protocol Error). Ambos fecham a conexão antes de publicar, alterar retained ou confirmar sucesso. PUBLISH válido continua funcionando; MQTT 3.1.1 conserva o fechamento sem DISCONNECT MQTT 5.

Fonte normativa: [OASIS MQTT 5.0](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html), §3.3.1.1, MQTT-3.3.1-2 (DUP=0 em QoS 0), §3.3.1.2, MQTT-3.3.1-4 (QoS reservado 3 é Malformed Packet e pede motivo `0x81`), e §4.13.1 (tratamento de erro com DISCONNECT quando aplicável).

Escopo: classificação tipada dos dois erros no codec, resposta no caminho MQTT 5 da conexão, unitários e verificador TCP real, CI, documentação de conformidade/plano e registro. Não alterar client, identidade/ACL, quotas, estado v15, versionamento, semântica QoS 1/2 ou tratamento de outros pacotes.

Invariantes: decisão no codec antes do roteador e do commit; Will de encerramento por erro segue o fluxo existente; Maximum Packet Size do destinatário limita o DISCONNECT; nenhum retained ou entrega é gerado pelo quadro inválido. Uma falha ao enviar DISCONNECT ainda fecha a conexão. QoS 0 com DUP=0, QoS 1/2 e cabeçalhos válidos permanecem aceitos.

Compatibilidade/migração: somente motivo de erro no wire MQTT 5; sem mudança em configuração ou estado durável. Não criar tag/release isolada, pois a fase 6A segue aberta.

Aceite: unitários para cabeçalhos QoS reservado, QoS 0 DUP, variantes válidas e MQTT 3.1.1; TCP com motivo exato, fechamento, Will, ausência de fanout/retained e regressões P178/P189. Executar `cargo fmt --all -- --check`, `cargo test --locked`, `cargo clippy --locked --all-targets -- -D warnings`, build release, inventário de licenças e distribuição no WSL. Registrar falhas intermediárias e CI do commit exato. Marcar apenas P190 após evidência; fase 6A global permanece desmarcada.
