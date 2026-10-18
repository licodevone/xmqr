# P219 — quadros WSS fragmentados e limites

- [Prompt P219](../broker/219-wss-fragmentation-limits.md) precedeu a fixture (`7ea8fad`). Código `582ed7a`; [CI da fonte exata](https://github.com/licodevone/xmqr/actions/runs/39126233420) passou nos jobs Rust e pacote Ubuntu 26.04.
- O broker aceitou CONNECT e PUBLISH binários fragmentados via WSS mTLS em MQTT 3.1.1 e 5; assinatura e entrega ao client do outro lado passaram. Quadro de texto e quadro binário maior que 64 KiB foram rejeitados; novas conexões MQTT 5 saudáveis funcionaram depois (`P219_WSS_FRAMES_PASS`).
- Fixture local cruzada com client 0.36.0, incluindo P218, também passou. Nenhuma configuração ou formato de estado mudou; a campanha não mede carga prolongada, memória de pico nem navegador real. Aceite **parcial** da fase 7.
