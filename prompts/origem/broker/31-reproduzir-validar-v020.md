# Prompt — reproduzir e validar o broker 0.2.0

Use este prompt depois do gate `setup/08`. O objetivo é comprovar o estado clonado em outro computador, não reimplementar as fatias históricas.

## Estado esperado, sujeito a evidência

- MQTT 3.1.1 sobre TLS/mTLS.
- Usuário/senha vinculados ao certificado e ACL deny-by-default por tópico exato.
- QoS 0, 1 e 2 nos dois sentidos.
- Mensagens retidas.
- Sessões persistentes `CleanSession=0` e fila offline QoS maior que zero.
- WAL/snapshot versionados sob os limites documentados.
- Sem Last Will e sem filtros wildcard na versão 0.2.0.

## Trabalho pedido

1. Confirme versão/commit em `Cargo.toml`, `CHANGELOG.md` e Git.
2. Execute formatação, lint e todos os testes Rust/MCP documentados, sem relaxar validações.
3. Gere credenciais locais novas e configure identidade/ACL para publisher e subscriber distintos.
4. Teste QoS 0/1/2, ACKs, retained novo/substituído/removido e sessão persistente atravessando desconexão e reinício.
5. Teste senha errada, certificado não confiável, tópico negado, packet identifier inválido e pacote acima do limite.
6. Compare pelo menos a fatia suportada com Mosquitto e um cliente independente. Ausência da ferramenta externa resulta em `BLOCKED`, não em `PASS`.
7. Registre sistema, filesystem do WAL, nível de durabilidade, limites, comandos e resultados sem segredo.

## Gate

Produza matriz `capability → cláusula OASIS → teste → evidência → status`. O resultado pode confirmar somente os comportamentos realmente observados. Não declarar conformidade MQTT 3.1.1 completa nem prontidão de produção.
