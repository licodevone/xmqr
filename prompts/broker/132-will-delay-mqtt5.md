# P132 rev1 — Will Delay Interval MQTT 5

Entrada: `main` após P131. MQTT 5 Will ainda é recusado; MQTT 3.1.1 Will publica imediatamente após quebra da conexão.

Objetivo: aceitar Will MQTT 5 com propriedade opcional Will Delay Interval (0x18), agendar publicação durável após desconexão anormal e publicá-lo quando vencer o delay ou a sessão terminar, o que ocorrer primeiro. Reconexão com Clean Start=0 antes do prazo cancela o Will; Clean Start=1 encerra a sessão anterior e publica o Will. DISCONNECT normal cancela o Will. Fonte: [OASIS MQTT 5 §§3.1.2.5 e 3.1.3.2.2](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html).

Escopo: codec CONNECT Will com propriedades vazias ou somente 0x18, ator e armazenamento v8 compatível com v1–v7, recuperação após restart/crash, takeover, timeout e relógio. Will Delay=0 e Session Expiry=0 publicam no encerramento. Não aceitar outras Will Properties neste recorte. Usar o tick do ator, commit antes da entrega, rejeitar duplicatas/truncamento.

Aceite: vetores positivos/negativos, conexão anormal, reconexão antes/depois, Clean Start=1, Session Expiry menor/maior que delay, restart, falha de WAL, interoperabilidade Mosquitto e client C70, fmt/test/Clippy/build e CI verde. Rollback v8 exige backup privado v7.
