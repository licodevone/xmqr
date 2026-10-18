# ADR 0003 — aceite de transporte WebSocket antes do MQTT 5 global

Estado: aceito em 2026-10-18. Decisão registrada durante P222, depois das fatias P210–P221; não é alegação de que a exceção foi documentada antes de sua implementação.

O [plano de paridade](../plano-paridade-mosquitto.md) ordena T01 (WebSocket/WSS) após o aceite global da fase 6D (MQTT 5). Na prática, WS e WSS foram implementados incrementalmente enquanto 6A–6D continuavam abertas. O transporte encaminha pacotes MQTT 3.1.1/5 ao mesmo codec, router, sessão e ACL dos listeners TCP/TLS; a ausência de propriedades MQTT 5 ainda não implementadas não é resolvida por WSS.

**Decisão:** avaliar T01 como contrato de transporte independente da conformidade global MQTT 5. O aceite de T01 exige, em fonte e artefatos identificados, client independente e navegador real, subprotocolo `mqtt`, WSS mTLS com origem explícita, negativos CA/SAN/certificado/senha/ACL, fragmentação e limites, estado durável por URL com reinício/crash, regressões WS/TCP/TLS e CI. O resultado declara somente os pacotes e funções MQTT já aceitos por seus próprios registros; não declara MQTT 5 completo, cluster, bridge nem prontidão de produção.

**Motivo:** o mesmo broker e client precisam oferecer WebSocket utilizável para aplicações web sem esperar a matriz normativa integral MQTT 5. O isolamento do transporte permite verificar regressões sem relaxar segurança ou reinterpretar o protocolo. A matriz P222 documenta o escopo exato e os riscos residuais.

**Consequências:** 6A–6D permanecem `[ ]`; qualquer novo recurso MQTT 5 precisa de prompt, testes em TCP/TLS e WS/WSS quando aplicável. Carga prolongada, power loss e múltiplos inflight continuam como limites operacionais explícitos, não como prova de produção. A fase 8 conserva seus próprios critérios e não é aceita por esta decisão.
