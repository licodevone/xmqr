# Prompt — mensagens retidas

Execute após o contrato durável `25`; para entrega em QoS 1/2, integre também `26`–`28`. Referência: [OASIS MQTT 3.1.1, §§ 3.3.1.3 e 3.8.4](https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html). Retained é estado por **tópico**, não parte da sessão de um cliente.

## Entrega

1. Um PUBLISH com RETAIN=1 substitui a última mensagem e seu QoS. Payload de zero bytes com RETAIN=1 remove a mensagem retida, mas ainda segue a entrega normal aos assinantes ativos. RETAIN=0 não altera o estado retido. Publique somente depois da autorização ACL e do commit exigido; não envie PUBACK/PUBREC de uma alteração durável antes de `fsync`.
2. Ao criar ou substituir SUBSCRIBE, entregue a última mensagem retida correspondente, com RETAIN=1; publicações para assinatura já estabelecida têm RETAIN=0. O QoS entregue é `min(QoS armazenado, QoS concedido)`. Defina ordenação entre SUBACK, replay retained e publicação simultânea sem perda nem duplicata indevida. Não reenvie retained apenas por reconectar uma sessão existente sem nova assinatura.
3. Preserve ACL deny-by-default também na leitura de retained. Tópicos exatos permanecem o escopo atual; se wildcard continuar ausente, recuse esse filtro conforme § 3.8.3, nunca o trate como match aproximado.
4. Imponha limites de número de tópicos, tamanho de payload, bytes totais e espaço em disco. Defina política de falha ao esgotar quota. Armazene separadamente de sessão, versionado, com recuperação/snapshot e migração explícitos.

## Gate

Teste substituição, remoção por payload vazio, RETAIN=0, novo SUBSCRIBE, substituição de SUBSCRIBE, reconnect sem nova assinatura, ACL negada, QoS 0/1/2, restart, snapshot e crash antes/depois do commit. Inclua interoperabilidade com `mosquitto_pub/sub` e clientes independentes; cite cláusulas nos testes. Não trate “retained” como histórico de mensagens ou fila offline.
