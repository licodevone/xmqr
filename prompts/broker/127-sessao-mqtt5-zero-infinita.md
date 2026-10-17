# P127 rev1 — Clean Start e expiração 0/infinita MQTT 5

Entrada: `main` após P126 e tag broker v0.17.0, árvore limpa; fase 6 aberta. O CONNECT 5 só aceita Clean Start 1 e Session Expiry 0, e o CONNACK sempre informa Session Present 0.

Objetivo: desacoplar Clean Start da retenção da sessão para os intervalos normativos 0 e 0xFFFFFFFF, preservar sessão e mensagens offline quando aplicável, e informar Session Present real. MQTT 3.1.1 preserva Clean Session. Fonte: [OASIS MQTT 5 §§3.1.2.4, 3.1.2.11.2 e 3.2.2.1](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html).

Escopo: codec CONNECT/CONNACK, registro no roteador, documentação do subconjunto, testes wire/ator e integração. Intervalos finitos, Will e propriedades não suportadas continuam com CONNACK 0x83 sem alterar estado; não promover 6B inteiro. Preservar formato do estado durável e ACL/principal, limites, geração de conexão e commit antes dos ACKs.

Aceite: combinações Clean Start 0/1 com expiração 0/infinita, retomada real com Session Present e mensagem offline, limpeza explícita, reinício do broker e negativos de propriedade duplicada/truncada/finita; regressão MQTT 3.1.1; fmt, test, Clippy, build e integração Mosquitto/client.
