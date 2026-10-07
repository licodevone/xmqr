# Roadmap do XMQR

O roadmap indica direção, não promessa de prazo. Cada item precisa de uma fatia
vertical executável, testes e documentação antes de ser considerado concluído.

## Série 0.4 — laboratórios e administração

- [x] laboratório aberto limitado a loopback;
- [x] laboratório com usuário e senha;
- [x] laboratório com ACL deny-by-default;
- [x] CRUD atômico de usuários;
- [x] perfis de estado separados;
- [x] registrar a validação local da base 0.4 com formatação, testes e Clippy;
- [x] automatizar vetores externos do núcleo com clientes Mosquitto na fatia 0.5.

## Série 0.5 - filtros e roteamento, tag v0.5.0 verificada

- [x] implementar e validar `+` e `#` no XMQR;
- [x] validar a regra de tópicos `$`;
- [x] deduplicar filtros sobrepostos e retained;
- [x] validar ACL, UNSUBSCRIBE, quotas e recuperação de sessões wildcard;
- [x] testar QoS 0/1/2 e filtros com clientes Mosquitto;
- [ ] publicar a release após revisão dos gates;
- [ ] benchmarks de fan-out e limites;
- [ ] ampliar clientes independentes e cobertura TLS/mTLS e segurança.

## Próximas fatias MQTT 3.1.1

- [x] Last Will com persistencia e encerramento anormal (0.6.0 local);
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


## Marcos incrementais autorizados

Veja [plano de versoes](incremental-versions.md). Implementacao seguinte espera
publicacao/resolucao do marco atual pelo mantenedor. MQTT5 nao pertence ao escopo.
