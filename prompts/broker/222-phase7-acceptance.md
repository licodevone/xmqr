# P222 — aceite da fase 7 no contrato de transporte

Entrada: WS local, WSS mTLS local/remoto, allowlist de `Origin`, client independente, outbox/assinatura duráveis por URL, navegador Chromium, fragmentação/limites e reinício/crash já têm aceites parciais. As fases MQTT 5 6A–6D permanecem abertas. Este prompt precede qualquer marcação global da fase 7.

Objetivo: decidir se a fase 7 satisfaz seu contrato de transporte T01: WebSocket/WSS no broker e client, navegador real, subprotocolo MQTT, fragmentação/limites, segurança e regressão TCP/TLS. Não inferir conformidade MQTT 5 integral, prontidão de produção ou bridge.

Escopo: executar em fonte exata a suíte Rust e pacote Ubuntu; fixtures WS, WSS e Chromium; integração cliente independente MQTT 3.1.1/5, QoS e ACL; TCP/TLS e Mosquitto; reinício limpo/crash com estado durável; negativos de certificado/CA/SAN/senha/Origin/tópico; lifecycle e imagens já publicados como evidência das versões. Registrar matriz por requisito com links e PASS/FAIL, lacunas e ambiente. Fazer ADR explícita para a antecipação de T01 antes do aceite global de 6D, delimitando dependências. Sem tag/release apenas por documentação; novas funcionalidades requerem prompt próprio.

Aceite: somente marcar a fase 7 após CI da fonte exata, matriz íntegra sem requisito ausente e ADR. Se faltar cobertura ou houver falha, manter `[ ]` e corrigir em outra fatia. Limites de carga prolongada, múltiplos inflight e power loss podem permanecer documentados como não pertencentes ao contrato T01, sem declarar qualidade de produção.
