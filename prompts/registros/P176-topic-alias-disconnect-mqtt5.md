# P176 — Topic Alias inválido recebe DISCONNECT `0x94` parcialmente

O [prompt P176](../broker/176-topic-alias-disconnect-mqtt5.md) foi commitado antes da implementação (`561aa05`). O teste novo passou, mas a regressão histórica P138 falhou por esperar um CONNACK anterior à propriedade Shared Subscription Available. A revisão do prompt (`abdbbd5`) precedeu a correção dessa fixture. Fonte exata `8179b13e0fb9136db4fe4c46c4a3da77b473fa71`: 200 testes de biblioteca PASS/6 ignorados, demais alvos, fmt, Clippy, build release, inventário de licenças e 6 contratos de distribuição PASS localmente. [CI PASS](https://github.com/licodevone/xmqr/actions/runs/39026943254) em Rust e pacote Ubuntu 26.04, incluindo o teste TCP novo.

Topic Alias zero, maior que o máximo anunciado ou não estabelecido agora é classificado sem confusão com I/O/timeout. Após CONNACK MQTT 5, o broker envia `e0 02 94 00` dentro do limite de saída e fecha antes de entregar a publicação. `scripts/verify_mqtt5_alias_error_disconnect.py` retornou `P176_ALIAS_DISCONNECT_PASS` para três negativos, ausência de entrega e alias válido. A regressão `verify_mqtt5_topic_alias.py` passou após correção do CONNACK esperado e incluiu client e Mosquitto. P175 permaneceu PASS.

Sem migração nem tag isolada. Outros casos malformados e aceites globais 6A/6C continuam abertos.
