# Contexto verificado — XMQR

Estado de entrada: inspeção local em 2026-10-07; não executados testes nesta tarefa.
Nome: XMQR. Licença do código: MIT. Pacote: mqtt-broker 0.5.0, não publicado;
binários mqtt-broker, mqtt-client e mqtt-admin. Rust edição 2024, mínimo 1.88.
Tokio, Rustls/tokio-rustls, rumqttc no cliente, Serde/TOML, Argon2 e Tracing.

Leia [contrato-base](../contrato-base.md) e [cobertura](../COBERTURA.md).
O XMQR é um broker experimental MQTT 3.1.1 usado pelo projeto consumidor
mqtt-broker. O consumidor não é o destino destas alterações.

Existentes: TCP de laboratório, TLS/mTLS seguro, autenticação vinculada ao
fingerprint no modo seguro, ACL, pub/sub QoS 0/1/2, retained, sessões persistentes,
UNSUBSCRIBE, filtros +/# e regra $, WAL/snapshot versionados e CRUD local de usuários.
Não existentes: MQTT 5.0, WebSockets, cluster, API administrativa,
configuração geral versionada/reload e endpoints de métricas/health/readiness.
Não há declaração de prontidão de produção ou conformidade integral.

Limites atuais: tópico/filtro 1024 bytes UTF-8 compartilhados no broker e CLI após P41. Payload 4096; pacote 64 KiB; 64 sessões; 256 subscriptions
por sessão; 64 offline e 32 inflight. Limites fixos, sem capacidade medida garantida.
Persistência MQTT: agregado v1; WAL/snapshot v1. ACK condicionado ao commit.
Configuração: ambiente para servidor; TOML somente usuários/ACL.

Plataforma: evidência documental Linux/WSL; administração atômica de usuários
retorna Unsupported fora de Unix. Abrir a cópia Windows não prova execução nela.
Interop documentada: Mosquitto 2.0.18 em open-lab; ampliar TLS/mTLS, ACL e
clientes independentes. Metas de carga, SLA e requisitos de implantação seguem abertos.
Não assumir IP, diretório pessoal ou certificado de outra máquina.

Origem do contexto anterior: [cópia preservada](../origem/broker/00-project-context.md).


## Atualizacao autorizada P42 - 0.6.0 local

Base tag v0.5.0 confirmada; Cargo.toml/lock agora 0.6.0 local. Last Will
implementado em codec/handler/ator com pending_wills duravel no documento v2
(leitura v1; WAL/snapshot v1). Retained preservado/revisado. As referencias
anteriores a Will ausente e documento MQTT v1 descrevem a base anterior.
Veja docs/last-will.md e registro P42. Proximo marco aguarda publicacao pelo
mantenedor; nenhuma tag/release criada aqui. MQTT5 continua fora do escopo.


## P43 - 0.7.0 em validação

Base bc4cc55/tag v0.6.0 verificada. Monitoramento opcional implementado em
monitoring.rs, com HTTP loopback limitado, probe real do ator/writer e métricas
de labels finitos. Cargo local 0.7.0; sem novas dependências ou mudança MIT.
Documento MQTT v2 e quotas preservados. Referências anteriores a endpoints
ausentes descrevem a base anterior. Aceite completo/release ainda pendentes.
Veja docs/monitoring.md e prompts/registros/P43-0.7.0.md (caminhos da raiz).
Não avançar para 0.8, extrair clientes ou criar commit/push/tag nesta tarefa.

## C25 - projetos separados

Cliente independente em ../xmqr-client, pacote xmqr-client 0.7.0 local,
binário mqtt-client. Broker contém mqtt-broker/mqtt-admin; rumqttc não integra
mais suas dependências. Gates Windows do cliente PASS; check/build/Clippy
all-targets do broker PASS. Integração Unix/monitor e aceite completo P43
pendentes; não declarar release. Prompts históricos continuam referência.
Cada melhoria do cliente segue seus próprios prompts e AGENTS. Ver registro C25.

## Checkpoint P43 validado - 2026-10-08

Mesmo repo via WSL/Rust1.99:72 testes e gates completos PASS,6 integrações
monitoring e9 Will PASS, incluindo1024UTF-8/retained/offline. Cliente independente
baseline commit26c1019 usado sem editar melhorias C26 paralelas. Bloqueios Unix
anteriores resolvidos. MIT/quotas/documento preservados. Publicação0.7 fica com
usuário; sem commit/push/tag aqui. P44 segurança dinâmica preparado apenas.
Mosquitto/TLS/mTLS externo NOT_RUN; sem conformidade integral ou produção.
