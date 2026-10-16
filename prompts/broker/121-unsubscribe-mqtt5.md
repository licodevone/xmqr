# P121 rev1 — UNSUBSCRIBE/UNSUBACK MQTT 5 inicial

Entrada: `main` `f74741d`, versão 0.16.0, árvore limpa. O broker aceita SUBSCRIBE 5, mas interpreta UNSUBSCRIBE 5 como 3.1.1; portanto não processa o Property Length obrigatório nem responde UNSUBACK 5.

Objetivo: aceitar UNSUBSCRIBE MQTT 5 com Property Length zero, remover cada filtro exato e responder um reason code por filtro na ordem recebida: `0x00` quando removido e `0x11` quando inexistente. Preservar UNSUBSCRIBE/UNSUBACK 3.1.1. Uma operação que não remove nada não gera commit; remoções efetivas aguardam commit antes do ACK. Fonte normativa: [OASIS MQTT 5 §§3.10 e 3.11](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html), inclusive MQTT-3.11.3-1/2.

Escopo: codec, roteador, conexão e testes wire/estado; documentação de conformidade, changelog, plano e registro. Rejeitar propriedades não suportadas e filtros vazios/malformados sem aceitar parcial. Não alterar estado persistido, quotas, autenticação ou versão.

Aceite: vetores positivos/negativos 5 e regressão 3.1.1; teste real SUBSCRIBE→UNSUBSCRIBE→UNSUBACK→PUBLISH sem entrega, com motivo de filtro inexistente e contagem de commits. Integração com C62, gates fmt/test/clippy/build e CI. Documentar falha intermitente P118 caso reapareça, sem confundi-la com esta mudança.

Rev2 após o primeiro teste: o decoder ainda bloqueava `0xa2` na lista inicial de pacotes MQTT 5. Acrescentar a operação à lista e repetir o vetor; a falha não indica erro no formato UNSUBSCRIBE.
