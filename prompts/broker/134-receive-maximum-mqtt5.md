# P134 rev1 — Receive Maximum MQTT 5

Entrada: `main` após P133. CONNECT MQTT 5 valida Receive Maximum 0x21 mas descarta seu valor; broker ainda usa só limite global de inflight. Fase 6C aberta.

Objetivo: aplicar o Receive Maximum do assinante a PUBLISH QoS1/2 enviados pelo broker durante a conexão, inclusive mensagens retidas, offline e replay após reconexão. Valor ausente=65535; zero/duplicata são erros. O limite não afeta QoS0 nem PUBREL/PING/ACKs, não é persistido na sessão e reinicia em cada conexão. Enfileirar excedente duravelmente, liberar quota após PUBACK/PUBCOMP e evitar replay acima do limite. O limite global configurado continua valendo; MQTT 3.1.1 não muda.

Aceite: vetores de CONNECT, 1 e 2 vagas, QoS1/QoS2, retained/offline, reconexão com valor menor, restart, interop wire com client C72/Mosquitto, negativos e limites; fmt/test/Clippy/build/CI. Fonte: [OASIS MQTT 5 §§3.1.2.11.3, 4.9](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html).
