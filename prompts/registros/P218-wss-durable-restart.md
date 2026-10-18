# P218 — retomada WSS após reinício do broker

- [Prompt P218](../broker/218-wss-durable-restart.md) foi publicado antes da fixture (`2b1ddc7`). A implementação da fixture está em `835498f`; [CI da fonte exata](https://github.com/licodevone/xmqr/actions/runs/39126067514) passou nos jobs Rust e pacote Ubuntu 26.04.
- Fixture WSS mTLS efêmera: assinante MQTT 5 com Session Expiry, assinatura QoS 1, saída do assinante, publicação QoS 1 offline, parada limpa e reinício do broker com o mesmo estado. CONNACK retomado indicou Session Present=1; a publicação pendente chegou sem novo SUBSCRIBE e recebeu PUBACK (`P218_WSS_RESTART_PASS`).
- Com o client independente 0.36.0 real, a mesma sequência manteve o manifesto privado e entregou `p218-client-offline` em JSONL após reinício. URL WSS diferente foi recusada sem modificar o manifesto (`P218_CLIENT_WSS_RESTART_PASS` local). O teste cruzado exige o binário opcional do client; o gate padrão da CI executa o vetor wire do broker.
- Aceite **parcial** da fase 7. Crash abrupto, expiração prolongada, múltiplos inflight e navegador real não são demonstrados por este recorte.
