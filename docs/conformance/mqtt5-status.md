# MQTT 5 — estado inicial da fase 6A

O XMQR ainda **não aceita sessões MQTT 5**. O broker implementa apenas a recusa
explícita P114 do nível 5: ao receber `CONNECT` com nome `MQTT` e nível 5,
responde `CONNACK` `20 03 00 84 00` (Session Present 0, Unsupported Protocol
Version, propriedades vazias) e fecha a conexão. O pacote é limitado a 64 KiB,
mantém o prazo de leitura existente e não chega à autenticação ou ao ator.

O caminho MQTT 3.1.1 (nível 4) permanece aceito; níveis 0/3/255 seguem com
`CONNACK` 3.1.1 `20 02 00 01`. O teste P114 usa bytes independentes do encoder,
confere a resposta, fechamento e ausência de commit mesmo com um `PUBLISH` em
pipeline. Isso não valida todas as propriedades nem a estrutura completa de um
`CONNECT` MQTT 5, pois nenhuma sessão dessa versão é admitida.

Permanecem pendentes em 6A: codec completo de `CONNECT`/`CONNACK`, propriedades,
reason codes de sucesso e erro, coexistência de sessões 3.1.1/5 e opção de
protocolo no client. Expiração, flow control, assinaturas e AUTH pertencem às
fatias 6B–6D. Nenhum formato durável, configuração ou versão mudou em P114.

Fonte normativa: [OASIS MQTT 5 §3.1.2 e §3.2.2](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html).
Escopo e evidência: [prompt P114](../../prompts/broker/114-recusa-connect-mqtt5.md)
e [registro P114](../../prompts/registros/P114-recusa-connect-mqtt5.md).
