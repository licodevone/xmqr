# Evolução do broker e dos clients — referência Mosquitto

Planejamento P53, 2026-10-11. Base broker 7da894a, versão publicada 0.10.0;
client independente 0.5.0. Estimativas para uma sequência de desenvolvimento
com dedicação regular, contadas do início da execução, não datas prometidas.
Cada fase depende do aceite anterior; recalcular prazo após medições e falhas.
O objetivo é paridade funcional relevante com Mosquitto, não copiar internals,
formatos privados ou prometer o mesmo desempenho. Este inventário agrupa
capacidades; não substitui auditoria opção por opção de uma versão Mosquitto.

## Base existente

Broker: MQTT3.1.1 QoS0/1/2, retained, sessões persistentes, filtros +/# e regra $,
UNSUBSCRIBE, keepalive, takeover e Last Will durável; TLS/mTLS, senha e ACL;
bundle de segurança com grupos/papéis e reload SIGHUP; WAL/snapshot, backup,
monitor HTTP opcional loopback, shutdown, systemd, Docker e deb Ubuntu26 amd64.
TOML geral P52 está no código, ainda fora do pacote publicado. Esses recursos
têm regressões locais, mas isso não prova conformidade completa nem produção.
Client CLI: publicação/assinatura, QoS, TLS/mTLS, retained/Will, reconexão,
diagnósticos e integração systemd/deb. Confirmar cobertura de cada nova opção
antes de anunciar equivalência com mosquitto_pub/mosquitto_sub.

## Lacunas frente à referência

| Área | Situação no XMQR | Entrega necessária |
| --- | --- | --- |
| Configuração e quotas | TOML implementado, quotas fixas | Limites globais coerentes, depois por identidade/listener; timeouts e rate limits documentados |
| Capacidade | Sem teto de produção medido | RAM/CPU, conexões, mensagens/s, latência p95/p99 e fan-out com TLS/QoS/persistência |
| Robustez | Recuperação e backup existentes, cobertura incompleta | Disco cheio, erro de escrita, pressão de filas, fuzzing, testes prolongados e matriz3.1.1 |
| Listeners | Um listener por processo/perfil | Múltiplos listeners, políticas por listener e TLS com senha sem exigir certificado cliente quando configurado |
| Administração | CRUD de usuários e bundle/SIGHUP | Gestão segura de grupos/papéis/ACL, auditoria e contrato administrativo; plugins são trilha posterior |
| Métricas/logs | Monitor básico e tracing | Métricas operacionais, formatos/exportação definidos e decidir suporte MQTT $SYS |
| MQTT5 | Ausente | Codec/propriedades, negociação, sessões/expiração, fluxo, assinaturas e autenticação estendida |
| WebSocket | Ausente | WS/WSS no broker e conexão correspondente no client |
| Bridge | Ausente | Ligação entre brokers com TLS, reconexão, mapeamento de tópicos e proteção de loops |
| Distribuição | Deb26 amd64; sem APT próprio | Ubuntu24 validado, arm64, repositório APT assinado e política de upgrade |
| Windows nativo | Não homologado | Persistência/locks/CRUD/sinais adaptados, serviço Windows, instalador e testes |
| Clients | CLI própria, sem paridade exaustiva | Matriz de opções pub/sub, perfis, saída/filtros/timeouts e MQTT5; firmware ESP32 validado como consumidor |
| Extensibilidade | Sem API de plugins equivalente | Avaliar hooks de autenticação/ACL e integração externa depois de estabilizar o núcleo |

TLS PSK, sockets Unix, opções avançadas de TLS/logs, API de controle e políticas
administrativas são backlog explícito de paridade; definir demanda e testes
antes de adotar. Alta disponibilidade/cluster é estudo separado e não condição
para igualar um broker Mosquitto isolado.

## Cronograma recomendado

| Fase | Janela estimada | Broker | Client/consumidores | Critério de saída |
| --- | --- | --- | --- | --- |
| 1 | Semanas1–2 | Quotas via TOML; validar redução frente ao estado existente; publicar P52 junto ao marco aprovado | Mensagens claras para limites, testes de payload/pacote/fila e configuração de conexão | Defaults preservados; negativos; redução sem truncar estado; pacote instalado/upgrade testado |
| 2 | Semanas3–4 | Harness de carga, métricas de saturação e limites por identidade conforme necessidade | Gerador de carga separado da CLI; matriz Mosquitto e ESP32 | Relatório reproduzível em hardware identificado, TLS/QoS/fan-out; sem estimativas de RAM sem medição |
| 3 | Semanas5–7 | Falhas de disco, fuzzing, pressão de filas e fechamento da matriz MQTT3.1.1 | Reconexão/backoff, cancelamento, diagnóstico e testes contra Mosquitto | Recuperação comprovada nos cenários; negativos; interop automatizada; pendências normativas listadas |
| 4 | Semanas8–10 | Listeners com políticas por endpoint, modos TLS e reload de certificados definido | Perfis de conexão, rotação e erros de certificado/credenciais | Isolamento de ACL; TLS/mTLS; rotação/rollback; nenhum laboratório remoto implicitamente habilitado |
| 5 | Semanas11–12 | Administração de bundle, auditoria, métricas e ciclo de release | Paridade prioritária pub/sub e documentação sincronizada | Operação sem editar segredos manualmente em casos cobertos; release com anexos/checksums e rollback |
| 6A | Semanas13–15 | Desenho MQTT5, codec, validação de propriedades e reason codes | Escolha explícita3.1.1/5; vetores e testes de negociação | Negativos normativos e coexistência3.1.1; apenas subconjunto5 anunciado |
| 6B | Semanas16–18 | Clean Start, Session Expiry, Message Expiry, Will Delay e estado versionado | Testes de expiração/reconexão; opções correspondentes | Crash/restart, migração e relógio/expiração tratados sem perda silenciosa |
| 6C | Semanas19–21 | Receive Maximum, Maximum Packet Size, Topic Alias e propriedades de publicação | Flow control, User Properties, Content Type, Response Topic/Correlation Data | Negociação bilateral, limites, QoS0/1/2 e persistência testados |
| 6D | Semanas22–24 | Opções de assinatura, Subscription Identifier, shared subscriptions e AUTH conforme contrato | No Local, Retain Handling/As Published, assinaturas compartilhadas e autenticação5 | Matriz5 por cláusula, interop externa, recursos ausentes declarados; sem alegação integral prematura |
| 7 | Semanas25–27 | WebSocket/WSS com limites e segurança equivalentes | Transporte WS/WSS e testes de browser quando existir consumidor | Regressão TCP/TLS, fragmentação, limites e desconexão aprovados |
| 8 | Semanas28–31 | Bridge incremental | CLI de diagnóstico; testes com Mosquitto nas duas pontas | Reconexão limitada, loops, QoS, retenção e ACL explícitos |
| 9 | Semanas32–35 | Windows nativo e extensões de paridade escolhidas | Serviço/instalador Windows e CLI homologada | Instalar/upgrade/remover, recuperação e permissões testados em Windows |

Reservar 20–30% de folga adicional; as 35 semanas são uma hipótese inicial de
planejamento, não previsão validada. MQTT5 pode exigir mais tempo após desenho
do estado durável. Não fixar tags0.11/0.12 antecipadamente; cada versão descreve
o conjunto efetivamente aprovado. Uma fase pode gerar várias entregas menores.

Distribuição Ubuntu24/26 e arm64 começa depois da fase3, com estimativa adicional
de 2–3 semanas. APT assinado depende de hospedagem/domínio, chave de assinatura
e política de manutenção; é publicação própria, distinta de GitHub Releases.
Pode ser antecipado sem bloquear MQTT5 quando houver disponibilidade.

## Sequência de execução de cada entrega

1. Criar e apresentar prompt no repositório responsável, com estado de entrada,
   escopo, requisitos normativos, migração, testes e critério de saída.
2. Implementar uma fatia utilizável no broker; implementar no client as opções
   necessárias para exercitá-la. Consumidores ESP32 permanecem fora do núcleo.
3. Validar unitários, negativos, integração broker/client e cliente independente
   Mosquitto; para texto, validar links/formatos sem repetir testes funcionais.
4. Se falhar, registrar o resultado, revisar o prompt antes de corrigir e repetir
   os checks afetados. Nenhuma etapa seguinte começa para esconder falhas.
5. Atualizar README, changelog, matriz de paridade e registro de evidências.
6. Commit/push após aceite. Tag imutável e prerelease apenas com binários/pacotes
   testados, notas, hashes e procedimento de upgrade/rollback. Versões independentes.

Próxima execução recomendada: [P55 — quotas do estado](../prompts/broker/55-quotas-estado.md),
segunda fatia da fase1, após P54 (admissão TCP). Não iniciar MQTT5, WebSocket e bridge juntos. Reavaliar este cronograma
ao encerrar cada fase e registrar desvios nos prompts correspondentes.

## Fontes e evidências

- [Configuração oficial Mosquitto](https://mosquitto.org/man/mosquitto-conf-5.html): referência de listeners, quotas, TLS, plugins e bridges.
- [MQTT5 OASIS](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html): contrato normativo; não usar opções Mosquitto como especificação MQTT.
- [Configuração XMQR](architecture/configuration.md), [registro P52](../prompts/registros/P52-configuracao-toml.md) e [matriz3.1.1](conformance/mqtt311-status.md).

Estado baseado na leitura do código/documentação e nas evidências P52 anteriores;
esta tarefa de planejamento não executou novos testes funcionais.


## Retomada após P54 — 2026-10-11

Commit local 7d5f371: admissão TCP configurável por TOML/ambiente, default64,
faixa1..64, restart necessário. Quotas duráveis permanecem fixas. Registro
[P54](../prompts/registros/P54-limite-conexoes.md) informa 92 testes e gates WSL
aprovados, recusa/liberação TCP e 4 integrações C27. Revisão desta retomada
conferiu código e evidências, sem reexecutar testes ou verificar publicação remota.

[P55](../prompts/broker/55-quotas-estado.md) está preparado, não implementado:
sessões, retained, assinaturas, offline e inflight configuráveis com rejeição de
redução incompatível sem truncar dados. A fase1 continua aberta; payload/pacote,
client e instalação/upgrade precisam de avaliação própria antes do aceite.


## Execução local P55 — aceite pendente

Quotas lógicas implementadas localmente; validação portável Windows aprovada.
Recuperação durável e integração Linux/WSL pendentes: não há distribuição WSL
visível nesta sessão. A fase1 segue aberta e nenhuma tag/release de aceite foi criada.
Veja prompts/registros/P55-quotas-estado.md e retome gates Unix antes de avançar.
