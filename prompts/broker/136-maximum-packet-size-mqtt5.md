# P136 rev1 — Maximum Packet Size MQTT 5

Entrada: `main` em `0e563cc` após P134; broker 0.19.0, documento durável v8. Fase 6C aberta. O CONNACK já anuncia limite de entrada 65536 bytes, mas CONNECT ainda não aceita `0x27` do client.

Objetivo: validar Maximum Packet Size não zero e único no CONNECT MQTT 5 e aplicar o teto ao pacote MQTT inteiro que o broker envia nessa conexão, inclusive CONNACK, SUBACK, ACKs, PUBLISH vivo/retained/offline/replay e PUBREL. O teto é por conexão e não persiste. Quando um PUBLISH exceder o limite, descartar essa entrega sem enviá-la e concluir sua obrigação QoS durável, sem bloquear as mensagens seguintes; outro pacote essencial que não caiba encerra a conexão sem enviá-lo. CONNACK omite a propriedade informativa de máximo do broker se necessário para caber. Preservar 65536 de entrada, quotas, MQTT 3.1.1, ACL e commit antes de ACK.

Arquivos: `src/mqtt/codec.rs`, `src/mqtt/mod.rs`, `src/mqtt/router.rs`, testes wire/ator, integração TCP, estado MQTT 5, registro e plano. Critérios: 0/duplicata/truncamento; bordas em bytes completos; QoS0/1/2, retained e replay; restarts, limites e CONNACK pequeno; interop client C73/Mosquitto; fmt/test/Clippy/build/CI. Não declarar a fase 6C completa. Fonte: [OASIS MQTT 5 §§3.1.2.11.4, 3.2.2.3.6](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html).
