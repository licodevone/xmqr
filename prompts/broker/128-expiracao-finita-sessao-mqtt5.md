# P128 rev1 — Session Expiry finita MQTT 5

Entrada: `main` após P127 (`5f56065`), v0.17.0 publicada, CI de P127 ainda em execução. Broker aceita somente expiração 0/infinita; documento durável v5 não guarda relógio da sessão.

Objetivo: aceitar Session Expiry Interval 1..0xFFFFFFFE em CONNECT MQTT 5, manter sessão até o prazo após desconexão, expirar por transição durável e responder Session Present 0 após o vencimento. Migrar documento v5 para v6 com campos opcionais, preservando sessões MQTT 3.1.1 e MQTT 5 infinitas. Fonte: [OASIS MQTT 5 §§3.1.2.11.2 e 3.1.4](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html).

Escopo: codec, ator, armazenamento e migração, testes de relógio/recovery, docs, integração client. Não incluir Message Expiry, Will Delay ou alteração de expiração via DISCONNECT; permanecem negados. Em crash com conexão ativa e instante de fechamento desconhecido, iniciar contagem na recuperação para evitar descarte silencioso e registrar limite. O intervalo é preservado no estado; o deadline de desconexão é wall-clock UTC em milissegundos. Recusar relógio indisponível e overflow; commit antes de observar expiração.

Aceite: sessão finita viva, desconexão e retomada antes/depois do prazo, expiração automática mesmo sem novas conexões, reinício e leitura de documento v5, intervalo máximo, negativos de propriedade duplicada/truncada e relógio inválido; regressão MQTT3/expiração0/infinita, fmt/test/Clippy/build e integração com Mosquitto.
