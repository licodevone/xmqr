# Roadmap do XMQR

O roadmap indica direção, não promessa de prazo. Cada item precisa de uma fatia
vertical executável, testes e documentação antes de ser considerado concluído.

## Série 0.4 — laboratórios e administração

- [x] laboratório aberto limitado a loopback;
- [x] laboratório com usuário e senha;
- [x] laboratório com ACL deny-by-default;
- [x] CRUD atômico de usuários;
- [x] perfis de estado separados;
- [ ] publicar evidências externas de interoperabilidade da série.

## Série 0.5 — filtros e roteamento, ainda não publicada

- [ ] publicar a implementação já em validação de `+` e `#`;
- [ ] publicar a regra de tópicos `$`;
- [ ] publicar a deduplicação de filtros sobrepostos;
- [ ] benchmarks de fan-out e limites;
- [ ] testes com clientes independentes.

## Próximas fatias MQTT 3.1.1

- Last Will com persistência e encerramento anormal;
- keep-alive e timeouts com matriz de conformidade;
- testes de interoperabilidade automatizados com Mosquitto;
- fuzzing do codec e testes property-based;
- métricas, health checks e shutdown gracioso;
- configuração versionada com validação e migração;
- recuperação e operação sob falhas de disco;
- benchmarks e capacidade documentada.

## MQTT 5.0

MQTT 5.0 só será introduzido depois que o núcleo MQTT 3.1.1 tiver matriz de
conformidade e regressão suficiente. Cada recurso 5.0 deverá ser negociado por
versão e não poderá alterar silenciosamente o comportamento 3.1.1.
