# Prompt — gate de interoperabilidade do cliente e broker 0.2.0

Valide a combinação cliente Rust + broker 0.2.0 sem usar apenas o codec próprio como oráculo.

## Matriz mínima

- Cliente Rust ↔ broker deste projeto.
- `mosquitto_pub/sub` ↔ broker deste projeto.
- Cliente Rust ↔ Mosquitto de versão fixada.
- ESP-MQTT ou outra biblioteca independente ↔ broker deste projeto, quando o ambiente estiver disponível.

## Cenários

CONNECT/autenticação, ACL, QoS 0/1/2, retransmissão, retained, sessão `CleanSession=0`, fila offline, restart, takeover, credencial inválida, tópico negado e limites.

Registre versões, comandos parametrizados, precondições, estímulo, resultado observável e cláusula OASIS. Use certificados diferentes por identidade e não publique chaves/segredos no relatório.

## Gate

Um cenário sem cliente externo disponível é `BLOCKED`. Divergência deve gerar diagnóstico e caso de regressão; não ajuste o teste para aceitar comportamento incompatível sem justificativa normativa.
