# Prompt — QoS 1 fim a fim

Execute após `25-durable-mqtt-state-contract.md`. Leia o estado atual e o [OASIS MQTT 3.1.1, §§ 2.3.1, 3.3–3.4, 3.8–3.9, 4.3.2 e 4.4](https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html). Não confunda confirmação do publicador com entrega ao assinante.

## Fatia vertical

1. Amplie o codec com PUBLISH QoS 1, packet identifier não zero, DUP, PUBACK e `SUBSCRIBE`/`SUBACK` de QoS 1. Rejeite QoS=3, flags e tamanhos inválidos antes de alocar. Preserve os testes de fragmentação/concatenação e os limites existentes.
2. Crie máquinas de estados independentes para recepção cliente→broker e envio broker→cliente. Aloque identificadores de saída sem colisão; mantenha inflight até PUBACK correspondente. Na retomada persistente, reenvie PUBLISH não confirmado com o mesmo identificador e DUP=1; não trate DUP como prova suficiente de duplicata no fluxo QoS 1. O QoS entregue é `min(QoS publicado, QoS concedido)`.
3. Integre autorização antes de assumir a publicação. Para `PUBLISH` não autorizado, a especificação MQTT 3.1.1 permite confirmar positivamente ou fechar a conexão (§ 3.3.5); escolha e documente uma política que não roteie o payload. Se houver armazenamento durável para assumir ownership, emita PUBACK somente depois do commit `fsync` configurado. Se ocorrer falha, não confirme sucesso.
4. Preserve ordem por publicador e use fila/inflight limitados. Assinante lento, identifier esgotado e falha de disco devem produzir backpressure/fechamento documentados, sem descarte silencioso de publicação QoS 1 aceita nem lock durante `.await`.
5. Adapte cliente de teste para publicar e assinar QoS 1, mas não use apenas o codec próprio como evidência; teste com `mosquitto_pub`/`mosquitto_sub` e um segundo cliente independente.

## Gate

Inclua vetores wire conhecidos, PUBACK errado/duplicado, perda de PUBACK, reconexão, retransmissão, assinante lento, falha de persistência antes/depois do ACK e ACL negada. Identifique cláusulas em cada teste; execute formatação, lint, testes unitários e integração TLS/mTLS. Relate explicitamente se a entrega garantida após reinício ainda depende de `27-persistent-sessions.md`; não anuncie QoS 1 durável completo antes desse gate.
