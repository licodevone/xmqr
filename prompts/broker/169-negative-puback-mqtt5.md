# P169 rev1 — PUBACK negativo de assinante MQTT 5

Entrada: P126 só decodifica motivos de sucesso nos ACKs recebidos. Um assinante MQTT 5 pode responder a PUBLISH QoS1 com PUBACK negativo; hoje o broker encerra a conexão e conserva a entrega como não reconhecida. O [MQTT 5 OASIS](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html) define os códigos PUBACK e torna o Packet Identifier reutilizável após PUBACK. Este prompt precede o código.

Objetivo: aceitar PUBACK MQTT 5 com códigos válidos enviados por cliente (`0x00`, `0x80`, `0x83`, `0x87`, `0x90`, `0x91`, `0x97`, `0x99`) e propriedades opcionais Reason String única e User Property repetida. Rejeitar o `0x10` reservado para servidor, códigos/propriedades desconhecidos, duplicata/truncamento e manter MQTT 3.1.1 inalterado. Tratar PUBACK negativo como término da tentativa QoS1, liberar inflight/quota e registrar apenas o código, sem payload/credenciais; não alegar que o assinante aceitou a mensagem nem prometer redistribuição em grupos compartilhados nesta parcela.

Aceite: vetores de codec positivos/negativos, TCP real com assinante que envia `0x80` e continua recebendo outra mensagem, persistência/retomada sem replay da entrega rejeitada, regressão MQTT 3.1.1, Rust/fmt/Clippy/distribuição e CI do commit exato. Documentar limite do recorte e checklist parcial M01/M02. Sem migração de estado ou release isolada.
