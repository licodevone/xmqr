# P148 — No Local e Retain As Published MQTT 5 no broker

Entrada: P147 aceita Retain Handling 0/1/2, C85 publica os bits No Local e Retain As Published no SUBSCRIBE. O broker ainda rejeita os bits 2/3. Este prompt precede o código P148.

Objetivo: aceitar No Local e Retain As Published por filtro MQTT 5, mantendo rejeição de bits reservados e de QoS/Retain Handling inválidos. Não encaminhar a publicação à assinatura No Local do mesmo ClientID; se houver filtros sobrepostos elegíveis, entregar uma vez, com QoS máximo elegível e RETAIN preservado quando ao menos um filtro elegível tiver Retain As Published. Retained inicial enviado no SUBSCRIBE conserva RETAIN=1. MQTT 3.1.1 mantém comportamento. Persistir as opções que afetam entrega na sessão durável e migrar documento v10 para v11 com padrão desativado, sem abrir estado futuro desconhecido.

Aceite: codec, roteador, overlap, sessão persistente/restart e migração v10→v11; TCP real QoS0/1/2 com client C85 e interop Mosquitto 2.0.22, negativos e regressões P147/P146. fmt/test/Clippy/build/licenças/CI. Checklist apenas após gates. Não declarar fase 6D inteira nem compatibilidade do admin 0.5.0 com documento v11: seu core permanece pinado no broker 0.23.0 e precisará de atualização e novo aceite antes de operar estado v11. Sem release isolada nem ESP32.

Fonte normativa: OASIS MQTT 5 §3.8.3.1, https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html.
