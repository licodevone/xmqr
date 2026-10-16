# P122 rev1 — QoS 2 MQTT 5 sem propriedades avançadas

Entrada: `main` `85c915b`, versão 0.16.0, árvore limpa. MQTT 5 pub/sub aceita QoS0/1 e CONNACK anuncia Maximum QoS=1; roteador e estado já têm QoS2 para MQTT 3.1.1. P121 completou UNSUBSCRIBE 5. O CI do commit funcional P121 passou; documentação final disparou CI próprio.

Objetivo: permitir PUBLISH/SUBSCRIBE QoS2 MQTT 5 sem propriedades avançadas, incluindo PUBREC→PUBREL→PUBCOMP inbound/outbound, entrega QoS2 e retenção existentes. Remover Maximum QoS=1 do CONNACK para que a ausência anuncie o valor padrão 2 (OASIS MQTT5 §3.2.2.3.4). Recusa ACL de PUBLISH QoS2 envia PUBREC `0x87`, sem commit nem PUBREL, preservando conexão. Fonte: [OASIS MQTT5 §§3.3–3.7 e 4.3.3](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html).

Escopo: codec, conexão e testes wire/estado; documentação de conformidade, changelog, plano e registro. Preservar os identificadores, geração, quotas, ACL/retained, durabilidade do QoS2 e MQTT 3.1.1. ACKs de sucesso podem omitir reason/property; propriedades não suportadas seguem recusadas. Sem migração, bump de versão ou alteração de instalação.

Aceite: vetores CONNACK/QoS2 e negativos de ACL, duplicata, packet ID/ordem e interop broker/client real; teste cruzado com assinante MQTT 3.1.1; fmt/test/clippy/build/CI. Somente marcar PASS real; tratar falha P118 separadamente.

Rev2 após primeiro Clippy: teste ampliado de ACL excedeu 100 linhas; extrair verificação repetida da contagem de commits e repetir. Vetores e cruzamento QoS2→3.1.1 passaram.

Rev3 após suíte completa: 135 testes passaram e um vetor legado ainda exigia rejeição de SUBSCRIBE QoS2, incompatível com esta entrega. Remover apenas esse caso da lista negativa, manter os negativos de ID/propriedade/opção inválidos e repetir toda a suíte/gates.
