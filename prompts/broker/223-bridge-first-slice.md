# P223 — contrato da primeira fatia da bridge

Entrada: fase 7/T01 aceita por P222; fase 8/T02 aberta. Este prompt precede o código da bridge.

Objetivo: iniciar ligação entre dois brokers por um processo sidecar XMQR separado, mantendo a execução do broker isolada. A primeira fatia será unidirecional, TLS/mTLS, um filtro/prefixo de entrada e prefixo de saída, QoS 0, com reconexão limitada e nenhuma promessa de persistência. O sidecar ficará no repositório do client, que já contém o stack MQTT/TLS; um prompt C125 detalhará a implementação.

Segurança: CA/SAN/certificado cliente, credenciais MQTT e ACL continuam requisitos por ponta; configuração privada, sem segredos em logs. Recusar mesma ponta de origem/destino, filtro ou mapeamento inválido e configuração bidirecional implícita. Reconexão limitada deve ser observável; falha fechada na validação. Não injetar ponte no processo do broker nesta fatia.

Aceite parcial: teste real com broker XMQR e Mosquitto nas pontas, publicação e mapeamento, queda/reconexão, negativos TLS/ACL e ausência de loop na topologia suportada. QoS 1/2, retained, duas direções, prevenção de loop entre bridges e recuperação durável ficam para fatias posteriores. Fase 8 permanece `[ ]` até a matriz completa T02; nenhuma tag antes dos gates e empacotamento apropriados.
