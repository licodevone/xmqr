# P120 rev1 — motivo de recusa ACL em SUBACK MQTT 5

Entrada: `main` em `99d8a18`, versão 0.16.0, árvore limpa; P116 responde `0x80` para assinatura recusada mesmo em MQTT 5. P119 já distingue recusa de publicação QoS 1. Cliente C60 reconhece `0x87` em fixture, mas a integração real ainda recebe `0x80`.

Objetivo: assinatura negada por ACL em MQTT 5 retorna SUBACK `0x87` (Not authorized) na posição do filtro, preservando a conexão e as assinaturas permitidas. MQTT 3.1.1 continua com `0x80`. Recusa total não deve gerar commit de estado. A ordem dos motivos acompanha a ordem dos filtros (OASIS MQTT 5 §§3.9.3 e 4.13; [padrão](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html)).

Escopo: `src/mqtt/{mod,router,connect_contract_tests}.rs`, documentação de conformidade, CHANGELOG, plano e registro. Sem mudança no formato persistido, quotas, ACL, QoS, retained ou versão. O código de recusa do roteador continua interno `0x80`; apenas a codificação MQTT 5 o traduz para `0x87`. Falhas de persistência seguem impedindo ACK de assinatura aceita.

Aceite: teste wire negativo para MQTT 5 e 3.1.1, contagem de commits inalterada após recusa total, aceitação posterior na mesma conexão e integração com cliente real C61. Gates `fmt`, `test --locked`, `clippy --locked --all-targets -D warnings` e CI. Registrar PASS/FAIL/BLOCKED reais antes de ticar o plano.

Rev2 após execução: o primeiro gate completo reproduziu `AlreadyOpen` intermitente no teste antigo de persistência (P118); teste isolado e repetição completa passaram, sem correção de causa. O primeiro Clippy apontou 124 linhas no teste ampliado; extrair helpers de wire e repetir os gates. Não atribuir o defeito de lock à mudança MQTT.
