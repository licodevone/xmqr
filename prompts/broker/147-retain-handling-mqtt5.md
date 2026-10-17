# P147 — Retain Handling 0/1/2 na assinatura MQTT 5

Entrada: P146 em validação e fase 6D aberta. O broker aceita apenas as opções padrão de SUBSCRIBE MQTT 5. Este prompt precede o código P147.

Objetivo: aceitar Retain Handling 0, 1 e 2 por filtro MQTT 5. Zero envia retained no SUBSCRIBE; um envia apenas se o filtro ainda não existia na sessão antes deste SUBSCRIBE; dois não envia retained no SUBSCRIBE. Preservar o QoS concedido, ACL e deduplicação por tópico. A escolha é transiente do SUBSCRIBE e não altera o formato durável v10; após restart, a existência da assinatura persistida governa a opção 1. Rejeitar valor 3 e bits reservados, manter No Local/Retain As Published explicitamente fora do recorte e preservar MQTT 3.1.1.

Aceite: negativos de opções inválidas antes de mutar estado, testes de filtro novo/existente, múltiplos filtros, retained QoS0/1/2 e restart com sessão persistente; TCP real broker/client e Mosquitto 2.0.22 como referência; regressões de assinatura/retained/QoS/ACL, fmt/test/Clippy/build/licenças/CI. Atualizar checklist após aceite. Sem release isolada ou ensaio ESP32.

Fonte normativa: OASIS MQTT 5 §3.8.3.1 e §3.3.1.3, https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html.
