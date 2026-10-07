# Prompt — ampliar cliente para QoS, retained e sessões

Parta do cliente QoS 0 validado nos prompts 19–21 e confirme primeiro o estado real do código. Implemente ou audite o suporte MQTT 3.1.1 existente a QoS 1/2, retained e `CleanSession` sem misturar propriedades MQTT 5.

## Trabalho pedido

1. Exponha `--qos 0|1|2`, `--retain`, `--clean-session` e `--client-id` com validação clara.
2. Mantenha packet identifiers não zero e sem colisão até o ACK terminal.
3. Modele PUBACK e os quatro passos QoS 2, incluindo DUP e retransmissão após reconexão.
4. No subscriber, valide QoS recebido, RETAIN e ordem observável; não trate ACK do broker como confirmação da aplicação.
5. Para sessão persistente, exija `client_id` estável e documente takeover, replay e fila offline.
6. Limite buffers, inflight, payload, reconexões e tempo de espera.
7. Preserve mTLS, verificação de SAN, usuário/senha segura e logs sem segredo.

## Gate

Testes unitários e black-box cobrem perdas/duplicatas de ACK, QoS mínimo, retained, sessão após restart, identificador incorreto, timeout e encerramento limpo. Atualize `docs/mqtt-client.md` conforme o comportamento comprovado.
