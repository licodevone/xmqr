# P224 — contrato QoS 1 da bridge T02

Entrada: P223/C125 entregou sidecar TLS unidirecional QoS 0, fase 8 aberta. Este prompt precede a segunda fatia.

Objetivo: no sidecar do client, permitir QoS 1 por ponta com uma publicação em voo. PUBACK da origem só pode ser enfileirado após PUBACK do destino; falha ou timeout do destino não deve confirmar a origem. Manter identidade e sessão persistentes na origem para redelivery após reinício. Duplicatas após crash entre confirmações são permitidas e devem ser documentadas como at-least-once, sem alegação de exactly-once.

Retained: preservar o sinalizador na publicação de saída quando o modo QoS 1 estiver habilitado; testar atualização e replay. Falhas de ACL/TLS, restart e retomada precisam ser observáveis. Não introduzir bidirecionalidade, MQTT 5 User Property/loop guard ou pacote de release nesta fatia. Prompts/implementação C126 no client; fase 8 permanece aberta até T02 completo.
