# P194 v1 — segundo CONNECT na conexão MQTT 5

Estado de entrada: `main` limpo em `715bf45`, broker/admin legado 0.34.0 publicado, client independente 0.28.0, estado durável v15. Fase 6A aberta. Após CONNACK MQTT 5, o segundo CONNECT é fechado sem motivo no wire, porque o filtro de tipos do codec o recusa antes da classificação.

Objetivo observável: após CONNACK de sucesso MQTT 5, um segundo CONNECT recebe DISCONNECT `0x82` (Protocol Error) e a conexão é fechada, sem registrar outra sessão, trocar identidade, aplicar novo Will ou alterar estado com os dados do segundo pacote. A transição de fechamento deve preservar o Will da primeira conexão. MQTT 3.1.1 continua fechando sem DISCONNECT MQTT 5.

Fonte normativa: [OASIS MQTT 5.0](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html), §3.1, MQTT-3.1.0-2 (segundo CONNECT é Protocol Error e exige fechamento), e §4.13.1 (servidor deve fechar; após CONNECT aceito deve tentar DISCONNECT com motivo apropriado).

Escopo: classificação tipada no codec e resposta no caminho MQTT 5 após CONNACK; unitários, integração TCP real, CI, documentação de conformidade/plano e registro. Não alterar autenticação/ACL, quotas, estado v15, versionamento, client, admin ou aceites de outras partes da fase 6A.

Invariantes: verificar a duplicação pela posição do pacote na conexão antes de interpretar seus campos, inclusive quando o corpo do segundo CONNECT é malformado. O pacote não passa pelo roteador. Respeitar Maximum Packet Size de saída, tolerar falha de envio do DISCONNECT e fechar. A conexão inicial e o fluxo MQTT 3.1.1 preservam sua semântica.

Compatibilidade/migração: somente diagnóstico de erro no wire MQTT 5; sem migração de estado ou alteração de configuração. Sem tag/release isolada enquanto a fase 6A global segue aberta.

Aceite: unitários para segundo CONNECT válido e corpo malformado, CONNECT inicial válido e MQTT 3.1.1; TCP com motivo `0x82`, fechamento, Will original, nenhuma segunda sessão/Will/retained, e regressão P190. Gates no WSL: fmt, teste completo, Clippy, build release, licenças e distribuição; CI do commit exato. Registrar falhas reais e marcar apenas P194 após evidência.

Revisão 2: o primeiro `fmt --check` detectou somente uma asserção a reformatar; depois de `cargo fmt`, o teste direcionado parou na compilação com `Cannot allocate memory` ao gravar o grafo incremental no WSL (7,8 GiB RAM, swap em uso). A repetição usará `CARGO_INCREMENTAL=0` e `RUSTFLAGS=-Cdebuginfo=0` com `-j 1`, sem alteração funcional; registrar separadamente o resultado. Se a pressão persistir, obter CI do commit exato e não promover teste local bloqueado a PASS.
