# P114 rev3 — recusa explícita de CONNECT MQTT 5

Data: 2026-10-16. Estado de entrada: `main` limpo em `e4456a1`, broker/`mqtt-admin` legado 0.15.0, fase 5 aceita. O codec admite MQTT 3.1.1 (nível 4); qualquer outro nível recebe hoje `CONNACK` 3.1.1 com código `0x01`. O client independente permanece 0.13.0.

## Objetivo observável

Quando o primeiro pacote é um `CONNECT` com nome `MQTT` e nível 5, responder com `CONNACK` MQTT 5, Session Present 0, Reason Code `0x84` (Unsupported Protocol Version), comprimento de propriedades 0, e encerrar a conexão. Níveis diferentes de 4 e 5 conservam a recusa 3.1.1 existente. Um `CONNECT` 3.1.1 válido conserva a sessão normal. Nenhuma conexão MQTT 5 será admitida nesta fatia.

## Escopo e invariantes

- Arquivos de código: `src/mqtt/codec.rs`, `src/mqtt/mod.rs`, `src/mqtt/connect_contract_tests.rs`; documentação do plano e matriz da fase 6A; registro P114.
- Separar o nível recusado no erro tipado para escolher o wire da resposta. Não reutilizar código de sucesso 3.1.1 para MQTT 5.
- Manter limite de pacote, timeout, primeira mensagem obrigatória, isolamento de ACL, quotas, ator único e fechamento da conexão. Recusa não registra sessão, não faz commit e não processa pacote em pipeline.
- Não modificar client, persistência, perfis de listener, dependências ou versões. MQTT 5 completo, propriedades de CONNECT, PUBLISH e QoS 5 permanecem pendentes.

## Contrato normativo

OASIS MQTT 5 §3.1.2.1–2 permite ao servidor que não aceita o nível solicitado enviar `CONNACK` com `0x84` e então exige fechar a conexão (MQTT-3.1.2-1/2). §3.2.2 define Reason Code `0x84` e a codificação do comprimento de propriedades; uma recusa usa Session Present 0. Fonte: <https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html>. Para níveis legados, preservar a recusa 3.1.1 de P93/§3.1.2.2: <https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html>.

## Compatibilidade e migração

MQTT 3.1.1, estado durável v5, configuração e pacotes não mudam. Clients MQTT 5 passam a receber uma rejeição parseável na sua versão; continuam incapazes de conectar. Nenhuma migração ou rollback de dados é necessária. Esta não é uma declaração de suporte MQTT 5 nem altera a versão 0.15.0 sem marco de release próprio.

## Validação e aceite

Testes de processo TCP com bytes independentes do encoder devem comprovar: `0x20 0x03 0x00 0x84 0x00` para CONNECT5, fechamento e ausência de commit; nível 0/3/255 recebe os quatro bytes legados; nível 4 conecta; pacote em pipeline após recusa não é processado. Unitário do codec preserva erro tipado. Executar `cargo fmt --all -- --check`, `cargo test --locked`, `cargo clippy --locked --all-targets -- -D warnings` no Ubuntu/WSL ou registrar bloqueio real. Documentar o subconjunto 6A e resultados em `prompts/registros/P114-recusa-connect-mqtt5.md`. Sem tag/release para esta fatia isolada.

Rev2: a primeira checagem de links falhou porque o registro P114 ainda não existia; criar o registro com os resultados já obtidos e repetir a checagem. Isso não altera o contrato wire ou os critérios de aceite.

Rev3: após acrescentar o unitário do erro tipado, `cargo fmt --check` apontou somente a quebra de linha desse assert; aplicar rustfmt e repetir fmt/test/Clippy. Sem alteração de comportamento.
