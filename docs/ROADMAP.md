# Roadmap do XMQR

## Plano atual P53 — broker e clients, referência Mosquitto

Consulte [inventário e cronograma](evolution-plan.md) para a sequência vigente,
dependências e critérios de saída. P52 implementou TOML no código; ainda não
incluído no pacote publicado0.10.0. P54 configura admissão TCP (1..64), ainda
não lançada. Próxima fatia: quotas duráveis configuráveis e validação de redução.
Os calendários e números de versões abaixo são históricos, não compromissos.

## Estado atual e sequência P51 — 2026-10-11

Broker0.10.0 e client0.5.0 publicados como experimentais. Já existem monitoramento,
segurança dinâmica, backup/restore, parada coordenada e empacotamento Ubuntu26.
As séries abaixo registram planejamento histórico; números antigos não definem
a próxima versão. Em particular, 0.10.0 entregou systemd/deb, não quotas configuráveis.

1. Consolidar regressão e evidência atual; C35 ajusta teste de reconexão QoS1.
2. Implementar [configuração versionada](architecture/configuration.md), conforme
   desenho P51; parser implementado por P52, ainda não lançado em pacote.
3. Propagar limites configuráveis mantendo defaults e validando estado existente.
4. Medir RAM/CPU/latência/mensagens por segundo em carga reproduzível e isolada.
5. Ampliar diagnósticos/perfis do client e negativos externos de TLS/ACL.
6. Testar armazenamento sob disco cheio, falhas de escrita e recuperação.
7. Múltiplos listeners com segurança por listener e migração explícita.
8. MQTT5 por desenho/codec/propriedades/sessões/fluxo; regressão3.1.1 obrigatória.

Cada etapa exige prompt próprio antes de código e aceite antes da seguinte.
Não anunciar capacidade de produção nem calendário/versão sem evidência.
Windows, WebSocket e bridge continuam frentes separadas, não pré-requisitos MQTT5.

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

## Sequência a partir da tag v0.8.0

- 0.7: monitoramento opcional validado localmente.
- 0.8: segurança dinâmica, reload atômico de usuários/ACL e grupos/papéis,
  validada e identificada pela tag v0.8.0.
- 0.9: backup/restore verificável; prompt [P45](../prompts/broker/45-backup-restore.md)
  preparado para a implementação autorizada.
- 0.10: quotas/rate limits configuráveis por identidade, preservando defaults.
- 0.11: WebSocket com limites/TLS/autenticação e regressão TCP existente.
- 0.12: bridge MQTT com identidade própria, reconexão limitada, prevenção de
  loops e política explícita de retenção/QoS; prompt próprio antes do código.
- MQTT5: introdução posterior por recursos negociados e coexistência3.1.1,
  começando por desenho/codec/negativos; sem promessa de versão/data/conformidade.

Referência funcional: https://mosquitto.org/documentation/dynamic-security/
e https://mosquitto.org/man/mosquitto-conf-5.html. Não copiar API/formato/implementação
nem executar todos os marcos de uma vez. MIT preservada; cada marco tem gates
e publicação/revisão próprios.
