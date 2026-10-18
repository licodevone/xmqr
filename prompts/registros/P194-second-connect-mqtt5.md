# P194 — segundo CONNECT na conexão MQTT 5

- Prompt [P194 v1/v2](../broker/194-second-connect-mqtt5.md) commitado e enviado antes do código (`379b4d1`; revisão operacional `1e8dfa6`). Entrada limpa em `715bf45`, broker/admin legado 0.34.0, estado durável v15.
- Escopo implementado na árvore: erro tipado `SecondConnect` antes de interpretar o corpo após CONNACK MQTT 5; tentativa de DISCONNECT `0x82` com limite negociado, seguida de fechamento. MQTT 3.1.1 mantém fechamento sem pacote MQTT 5. Script TCP cobre corpo válido/malformado, Will original, ausência de sessão/Will secundários e regressão 3.1.1.
- Primeira sequência local: `cargo fmt --all -- --check` FAIL por formatação de asserção; `cargo fmt` aplicado. Repetição de teste direcionado com `-j 1` FAIL antes dos testes: WSL `Cannot allocate memory` ao gravar grafo incremental. Revisão 2 do prompt especifica recompilação sem incremental e com `debuginfo=0`; resultado pendente.
- Gates completos, CI do commit exato, aceite e checklist: pendentes. A fase 6A global permanece aberta.
