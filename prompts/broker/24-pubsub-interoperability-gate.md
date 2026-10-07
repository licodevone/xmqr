> **Adaptação XMQR — 2026-10-07.** Histórico de escopo da origem, sem prova de execução no XMQR. Não reaplicar sobre o código existente. Para validar o snapshot atual, usar broker/36 e clients/24.
> Leia primeiro [o contrato comum](../contrato-base.md) e a matriz [de cobertura](../COBERTURA.md).
> Origem literal preservada: [arquivo original](../origem/broker/24-pubsub-interoperability-gate.md). Nenhum agente, skill ou MCP externo é requisito instalado.
> O contrato comum prevalece sobre instruções históricas de versão, ambiente e execução. Leitura não autoriza implementação nem execução automática.
# Prompt — gate de interoperabilidade do MVP pub/sub

Execute somente após os prompts `22-mqtt311-qos0-pubsub-mvp.md` e `23-certificate-identity-and-acl.md`. Teste o listener mTLS em `127.0.0.1:8883` primeiro, sem abrir acesso à LAN. Os comandos do cliente Rust e os caminhos PEM estão em `docs/mqtt-client.md`.

## Casos mínimos

1. Cliente Rust `sub` espera; cliente Rust `pub` envia `teste/mensagem`; exatamente uma mensagem chega com os bytes esperados. Inverta com `mosquitto_sub` e `mosquitto_pub` para evitar validar apenas o próprio codec. Registre as versões e os comandos reais.
2. Certificado ausente, CA não confiável, certificado expirado ou revogado: handshake mTLS falha. Senha errada ou usuário não vinculado ao certificado: CONNECT recusado. Identidade válida sem ACL de `publish` ou `subscribe`: operação negada sem encaminhar payload. Tópico não autorizado, filtro wildcard não suportado e QoS fora do escopo não viram permissões implícitas.
3. CONNECT parcial, Remaining Length excessivo, pacotes concatenados, frame fragmentado, cliente silencioso e assinante lento: sem pânico, alocação descontrolada ou travamento do listener. Conexões independentes continuam operando.
4. Cliente desconectado: assinaturas de Clean Session saem do registro. PINGREQ/PINGRESP e tempo de Keep Alive funcionam com limites configurados. Erros não vazam credenciais nem payload nos logs.

Rode `cargo fmt --check`, `cargo test --locked`, `cargo clippy --all-targets --locked -- -D warnings` e testes de interoperabilidade com certificado válido/negado. Se o lint geral falhar em código preexistente, separe a evidência da fatia nova e registre o débito sem declarar sucesso total. Atualize a documentação de uso e a matriz normativa apenas para comportamentos observados. Não declarar o broker compatível com MQTT 3.1.1 inteiro após esta fatia QoS 0.
