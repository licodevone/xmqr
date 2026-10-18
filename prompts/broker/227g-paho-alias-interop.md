# P227G v1.0 — interoperabilidade independente de Topic Alias

Preparado2026-10-18 antes do harness. M06 ainda tem limitação externa:
Mosquitto2.0.22 recusa a forma abreviada válida na recepção. Não transformar
reprodução dessa falha eminteropPASS. O PahoPython2.1.0 oficial já isolado
aceita TopicName vazio em MQTT5 e expõe TopicAlias em Properties; não faz
substituição automática do tópico na mensagem entregue ao callback.

Criar scripts/verify_phase6_paho_alias.py com --broker/--report explícitos,
sem instalar biblioteca. Dois peers Paho, conexões loopback/estado nativo
privado, TopicAliasMaximum1, publicação inicial com nome/alias, compacta
QoS0/1/2, rebind de alias de entrada e reconexão com reset do alias de saída.
Verificar bytes/propriedades/ordem, conclusõesQoS e retained. Adaptador
limitado no callback resolve o alias na aplicação, a partir das propriedades
decodificadas pelo Paho. Registrar essa participação explicitamente, sem
anunciar resolução nativa pelo Paho ou homologaçãoMosquitto.

Fonte Paho consultada: checkout oficialv2.1.0 commitaf64a4365c6ac5a7a4d339e7b00f44df91353b35,
client.py publish/_handle_publish; licença original preservada. Requisito
OASIS MQTT5 §§3.3.2.3.4/3.3.4: associação por conexão, alias nãozero e
respeito ao máximo negociado. Não copiar código do Paho para o runtimeXMQR.

Report exclusivo sanitizado, hashes/versões de ELF/harness/biblioteca,
cleanup e markerP227_PAHO_ALIAS_PASS após todos os cenários. FAIL exige
revisão antes do ajuste. Integrar em6C, sem ampliar recursosruntime/quotas
nem mexer em serviços/firmware/firewall/segredos do operador.
