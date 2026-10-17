# P142 — propriedades de resposta e usuário no PUBLISH MQTT 5

- [Prompt P142 rev1–rev3](../broker/142-publish-request-response-user-properties-mqtt5.md) criado antes do código. Base P141 aceita; fase 6C aberta.
- Broker aceita Response Topic, Correlation Data binária e User Property repetível; valida limites, encaminha para MQTT 5, omite no 3.1.1, e preserva no documento durável v10 (leitura v1–v9). O aceite global da fase 6C ainda exige revisão de fluxo.
- Gates locais parciais: vetores de codec e estado PASS; TCP real QoS0/1/2, retained, offline/restart, client C78, assinante 3.1.1 e publisher Mosquitto 2.0.22 PASS. Regressões P141, P136 e P139 PASS. Sem ensaio físico ESP32.
- Gate completo de testes Rust: 164 testes da biblioteca PASS/6 ignorados, demais suítes de integração PASS. Clippy `-D warnings`, fmt, build release e inventário de licenças PASS.
- Fonte `de6517c249f59153764919c5b36d8f477c362411` em `main`; [CI completa PASS](https://github.com/licodevone/xmqr/actions/runs/39000015530), incluindo pacote Ubuntu26 e unidade. [CI C78 PASS](https://github.com/licodevone/xmqr-client/actions/runs/39000007226). Aceite P142 limitado às propriedades de publicação e à migração v10; fase 6C global aberta.
- Documento v10 não pode ser lido pelo broker publicado 0.21.0 (v8), nem pelo P141 (v9): rollback exige backup privado anterior à primeira gravação em v10, e backup v8 para retorno a 0.21.0. Sem tag/release isolada.
