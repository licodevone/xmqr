# Prompt — interoperabilidade

Monte testes black-box com `mosquitto_pub/sub` e ao menos duas bibliotecas clientes independentes, cobrindo MQTT 3.1.1 e 5.0 quando suportadas. Inclua connect, auth, publish/subscribe, wildcards, QoS, retained, Will, sessões, reconnect e limites.

Execute o mesmo cenário contra este broker e um Mosquitto de versão fixada. Compare comportamento no wire e resultado do cliente, aceitando diferenças apenas quando permitidas e documentadas.

Capture versões e comandos exatos. Transforme divergências em casos pequenos com referência normativa; não “corrija” apenas para imitar comportamento não normativo do broker de referência.

