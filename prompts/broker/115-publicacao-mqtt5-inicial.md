# P115 rev1 — publicação MQTT 5 inicial

Data: 2026-10-16. Entrada: `main` em `8fdd92b`, broker 0.15.0, P114 aceito. Solicitação: prosseguir na fase 6A com prompt antes do código.

## Resultado observável

Aceitar CONNECT MQTT 5 com Clean Start=1, Session Expiry ausente/zero, Receive Maximum válido opcional, sem Will e sem outras propriedades de CONNECT. Responder CONNACK 5 com sucesso, Maximum QoS=1 e Maximum Packet Size=65536. Aceitar PUBLISH 5 QoS 0/1 sem propriedades, aplicar ACL/limites/retained existentes e responder PUBACK 5 de sucesso para QoS 1. PINGREQ e DISCONNECT simples funcionam. Publicação deve chegar a assinante MQTT 3.1.1. MQTT 3.1.1 permanece compatível.

## Restrições

- Recusar conexões MQTT 5 com Clean Start=0, Will ou propriedades não suportadas com reason code apropriado antes de criar sessão; nunca reinterpretar bytes 5 como formato 3.1.1.
- O broker não anuncia suporte geral a MQTT 5. SUBSCRIBE/UNSUBSCRIBE/recebimento de publicação como assinante MQTT 5, QoS 2, propriedades estendidas e persistência 5 ficam pendentes. Pacotes fora da fatia encerram a conexão; não publicar parcialmente nem corromper estado.
- Preservar autenticação, escopo de client ID, limites, timeout, isolamento de principal, semântica de publicação QoS 1 e unregister.
- Documentar explicitamente o subconjunto; sem migração de estado ou dependências.

## Aceite

Testes de wire independentes do encoder cobrem CONNECT 5, PUBLISH QoS0/1 para assinante 3.1.1, PUBACK, rejeições e regressão 3.1.1. Executar fmt, testes e Clippy, registrar resultado em `prompts/registros/P115-publicacao-mqtt5-inicial.md`; atualizar plano apenas após aceite. Sem tag/release isolada até um marco 6A validado.

Norma: <https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html>.

Rev2: o CONNACK de sucesso anuncia Maximum QoS=1 e Maximum Packet Size=65536, pois os defaults MQTT 5 não refletiriam os limites reais do subconjunto. Session Expiry=0 explícito no CONNECT é aceito como o default.

Rev3: incluir script de verificação reproduzível em Ubuntu/WSL que execute os dois binários reais em loopback isolado, com assinante 3.1.1 e duas publicações MQTT 5 QoS0/1. Registrar o resultado cruzado no aceite.

Rev4: estender a suíte de interoperabilidade já executada na CI, usando `mosquitto_pub -V mqttv5` como publicador independente e `mosquitto_sub -V mqttv311` como assinante. Cobrir QoS0/1 e retained; a máquina local não possui o pacote Mosquitto e o gate externo ocorrerá na CI que já o instala.

Rev5: a CI do commit `a084033` falhou apenas no novo teste externo: `mosquitto_pub -V mqttv5` encerrou com código 131 na primeira publicação QoS0, sem expor stderr no teste. Preservar a falha como evidência, melhorar o diagnóstico do fixture e reproduzir com o mesmo cliente Mosquitto em Ubuntu/WSL para distinguir propriedades CONNECT não suportadas de um erro do script. Corrigir o contrato mínimo ou limitar explicitamente o escopo, repetir os gates e só então marcar P115 aceito.

Rev6: reprodução local capturou `CONNECT` do Mosquitto com propriedade `Receive Maximum=20` (`21 00 14`), valor válido que limita apenas entregas do servidor ao cliente. Como este subconjunto não entrega a assinantes MQTT5, aceitar e validar `Receive Maximum` não zero, uma vez, em qualquer ordem com Session Expiry=0. Manter outras propriedades recusadas; adicionar vetores positivos/negativos e repetir o teste Mosquitto.
