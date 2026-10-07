# Prompt — primeira fatia funcional MQTT 3.1.1 pub/sub

Objetivo: fazer dois clientes MQTT 3.1.1 trocarem mensagens QoS 0 pelo listener mTLS existente, sem declarar o broker completo. Leia `AGENTS.md`, `prompts/broker/00-project-context.md`, `prompts/broker/04-wire-codec.md`, `prompts/broker/05-connection-state-machine.md`, `prompts/broker/06-subscriptions-and-routing.md` e o código real. Use a [especificação OASIS MQTT 3.1.1](https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/mqtt-v3.1.1.html) como fonte normativa.

## Sequência obrigatória

1. Defina limites antes do parser: pacote, tópico, payload, tempo para completar CONNECT e cada frame, número de clientes, assinaturas e mensagens pendentes por cliente. O buffer inicial de 4 KiB do transporte é somente a primeira leitura, não um pacote MQTT completo. Faça leitura incremental que preserve bytes concatenados e aceite frames fragmentados sem alocar pelo Remaining Length não validado.
2. Implemente CONNECT 3.1.1 (nível 4, flags e strings válidas) e CONNACK; antes de CONNECT, rejeite outros pacotes. Mantenha um único dono da conexão, identidade associada ao certificado e política de Clean Session explícita. Exija a política confirmada em `23-certificate-identity-and-acl.md`: certificado mTLS **mais** usuário/senha vinculados a esse certificado **mais** ACL.
3. Implemente SUBSCRIBE/SUBACK para um filtro exato e QoS 0, depois PUBLISH QoS 0, fan-out e DISCONNECT. Use PINGREQ/PINGRESP e prazo de Keep Alive. Não prometa QoS 1/2, retained, Will, wildcard, persistência ou MQTT 5.0 nesta fatia.
4. Separe codec, estado de conexão, registro de assinaturas e autorização. Use filas limitadas por cliente; assinante lento deve ser desconectado ou sofrer política de descarte documentada, sem bloquear publicadores nem segurar lock durante `.await`. Remova assinaturas ao fim da sessão limpa.
5. Teste vetores de bytes independentes do encoder, frames partidos/concatenados, pacotes fora de ordem, Remaining Length hostil, flags inválidas, SUBACK recusado, assinante lento, reconexão e cliente que não envia CONNECT. Registre a cláusula OASIS exata por comportamento testado.

## Gate de segurança e aceite

O servidor só deve aceitar CONNECT e operar pub/sub se mTLS, usuário/senha e ACL de `23-certificate-identity-and-acl.md` estiverem configurados e aplicados com deny-by-default. A conclusão exige também `24-pubsub-interoperability-gate.md`: cliente Rust `sub`, cliente Rust `pub` e clientes Mosquitto devem demonstrar interoperabilidade no escopo anunciado. Relate limites e funcionalidades ainda não implementadas.
