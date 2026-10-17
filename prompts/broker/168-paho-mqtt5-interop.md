# P168 rev1 — interoperabilidade MQTT 5 com cliente externo Paho

Entrada: P166/C97–C99 foram distribuídos em broker 0.30.0 e client 0.27.0. A matriz 6A/M01 pede duas implementações externas; CI já cobre `mosquitto-clients`, mas ainda não exercita o Client Identifier atribuído com outro cliente externo. Este prompt precede o harness e o gate.

Objetivo: acrescentar campanha reproduzível com Eclipse Paho Python 2.1.0, sem dependência de runtime do broker. Exercitar CONNECT MQTT 5 com ID vazio, propriedade `0x12`, Session Expiry finita, desconexão e retomada com Session Present, além de pub/sub QoS0/1/2 e retained. Preservar o gate Mosquitto existente e negativos 3.1.1 de ID vazio; registrar qualquer divergência real sem mascarar ou declarar conformidade MQTT 5 integral.

Aceite: teste isolado com broker de laboratório descartável, timeouts e limpeza dos processos; dependência de teste versionada e instalada em área temporária na CI, sem instalar no WSL do operador. Executar localmente, CI do commit exato e regressões Rust/distribuição proporcionais. Atualizar matriz M01 e checklist com evidência parcial, deixando M02 e aceite global 6A abertos. Sem tag/release isolada.
