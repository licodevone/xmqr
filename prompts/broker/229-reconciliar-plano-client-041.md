# P229 v1.0 — reconciliar plano XMQR com client 0.41.0

## Entrada

Broker `main` em `af78cd3`, release 0.43.0 publicada e fase 6 aceita no
contrato finito de 69 fixtures. Client independente 0.41.0/bridge 0.3.0
publicados em `v0.41.0` da fonte `1d60d38`, com CI final
`39170753201` e seis anexos remotos verificados. Admin independente
0.11.0 permanece. Nenhuma alteração local rastreada no broker.

## Escopo e aceite

Atualizar somente `docs/evolution-plan.md`, `docs/current-releases-wsl.md`
e o estado T02 em `docs/plano-paridade-mosquitto.md`: registrar C137 e
C138 aceitos, versões/hashes/comandos de instalação atuais, sem marcar
fase 8 global como concluída. Preservar itens históricos e os limites:
MQTT 5 de origem QoS 2, propriedades entre brokers, ciclos externos e
transação distribuída ainda faltam. Fases 6 e 7 aceitas não devem ser
reabertas por texto histórico. Verificar links, hashes documentados,
`git diff --check` e estado Git; commit/push documental após revisão.

Não alterar broker, client, admin, serviço, tag ou release neste prompt.
