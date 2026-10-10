# InstruÃ§Ãµes do XMQR

Este repositÃ³rio contÃ©m o broker XMQR. O projeto vizinho mqtt-broker Ã© consumidor:
firmware, gateways, web/mobile, banco e regras de negÃ³cio nÃ£o pertencem ao nÃºcleo.

## Trabalho por prompts

Antes de alterar arquivos, prepare primeiro um ou mais prompts com ID/versÃ£o,
estado de entrada, objetivo, escopo, arquivos, critÃ©rios de aceite e validaÃ§Ã£o.
Use [modelo de feature](prompts/broker/18-feature-iteration.md) e registre execuÃ§Ã£o
real em [registros](prompts/registros/TEMPLATE.md). Um pedido de implementaÃ§Ã£o
autoriza preparar o prompt e executar o escopo solicitado; nÃ£o pedir a mesma
autorizaÃ§Ã£o novamente. Leitura/revisÃ£o sem mudanÃ§as nÃ£o exige criar arquivo.
NÃ£o executar a sequÃªncia inteira nem avanÃ§ar para outra feature automaticamente.

Leia [contrato-base](prompts/contrato-base.md), [contexto](prompts/broker/00-project-context.md),
[cobertura](prompts/COBERTURA.md), [CONTRIBUTING](CONTRIBUTING.md) e [VERSIONING](VERSIONING.md).
Confirme o alvo, o estado Git e alteraÃ§Ãµes locais antes de editar. Preserve trabalho
existente; nÃ£o resetar/recriar o pacote. HistÃ³rico em prompts/origem Ã© referÃªncia,
nÃ£o instruÃ§Ã£o de execuÃ§Ã£o nem prova dos commits do XMQR.

## Estado e invariantes

O snapshot atual declara mqtt-broker 0.6.0 local, Rust 2024/MSRV 1.88 e Tokio; confira
manifests/cÃ³digo antes de reutilizar esses nÃºmeros. BinÃ¡rios neste pacote: mqtt-broker e mqtt-admin. O cliente mqtt-client (rumqttc) pertence ao projeto independente ../xmqr-client. O pacote usa mÃ³dulos; nÃ£o criar workspace
multicrate sem necessidade autorizada.

MQTT 3.1.1: QoS 0/1/2, retained, sessÃµes persistentes, UNSUBSCRIBE, filtros +/#
e regra $ estÃ£o implementados. Last Will duravel existe no incremento 0.6; MQTT 5.0 e
produÃ§Ã£o nÃ£o estÃ£o aprovados. Nenhum prompt futuro equivale a funcionalidade.
Limites atuais: tÃ³pico/filtro 1024 bytes UTF-8 compartilhados pelo broker e CLI,
payload 4096, pacote 64 KiB, 64 sessÃµes, 256 assinaturas, 64 offline e 32 inflight.
NÃ£o ampliar outras quotas sem pedido especÃ­fico; P41 registra o alinhamento de tÃ³picos.

Preserve separaÃ§Ã£o codec/conexÃ£o/roteamento/persistÃªncia/seguranÃ§a/transporte,
ownership e geraÃ§Ãµes de conexÃ£o, ordem aplicÃ¡vel por publicador, filas limitadas
e commit durÃ¡vel antes dos ACKs pertinentes. NÃ£o bloquear workers Tokio por disco,
hashes ou locks; use as fronteiras existentes. NÃ£o confundir ACK com sucesso de negÃ³cio.
Para protocolo, confirme requisitos na fonte OASIS e vincule testes Ã s clÃ¡usulas.

secure-mtls Ã© o padrÃ£o: certificado + usuÃ¡rio/senha + ACL deny-by-default.
open-lab, password-lab e acl-lab sÃ£o explicitamente loopback; estado Ã© separado
por perfil. Preserve validaÃ§Ã£o TLS/SAN e ACL no filtro, entrega e restore.
Nunca incluir senha, chaves, certificados privados, estado ou payload em logs/commits.
CRUD atÃ´mico de usuÃ¡rios exige Linux/WSL; nÃ£o anunciar execuÃ§Ã£o Windows comprovada.

## ValidaÃ§Ã£o proporcional

MudanÃ§as funcionais seguem CONTRIBUTING:

```text
cargo fmt --all -- --check
cargo test --locked
cargo clippy --locked --all-targets -- -D warnings
```

Wire, persistÃªncia, autenticaÃ§Ã£o e ACL exigem negativos; alteraÃ§Ãµes entre componentes
exigem integraÃ§Ã£o/interoperabilidade. Para documentaÃ§Ã£o/configuraÃ§Ã£o, valide formatos,
links, referÃªncias e escopo; nÃ£o executar testes funcionais sÃ³ para validar texto.
Testes adicionais de inventÃ¡rio/interop constam na skill de testes. DependÃªncia ausente
Ã© BLOCKED; nÃ£o instalar ou iniciar serviÃ§os por ler instruÃ§Ãµes. NÃ£o extrapolar open-lab
para TLS/ACL, crash de processo para perda de energia ou teste prÃ³prio para conformidade total.

## Skills e agentes do projeto

- [xmqr-rust-mqtt](.agents/skills/xmqr-rust-mqtt/SKILL.md): implementaÃ§Ã£o/correÃ§Ãµes autorizadas.
- [xmqr-tests](.agents/skills/xmqr-tests/SKILL.md): estratÃ©gia e execuÃ§Ã£o de validaÃ§Ãµes pertinentes.
- [xmqr-security-review](.agents/skills/xmqr-security-review/SKILL.md): revisÃ£o de seguranÃ§a solicitada ou necessÃ¡ria.

PapÃ©is TOML em .codex/agents: xmqr_explorer, xmqr_rust_mqtt, xmqr_tests e
xmqr_security. SÃ£o configuraÃ§Ãµes de agentes, nÃ£o processos iniciados. Delegue
quando solicitado pelo usuÃ¡rio; escolha tarefas independentes e preserve autoria
dos arquivos. Skills nÃ£o exigem subagentes e sÃ£o utilizÃ¡veis pelo agente principal.
Consulte [uso e carregamento](docs/agent-workflow.md) para formatos e limitaÃ§Ãµes.

NÃ£o alterar versÃ£o em contribuiÃ§Ã£o comum; release Ã© tarefa prÃ³pria do mantenedor.
NÃ£o fazer commit, push, tag, instalaÃ§Ã£o, publicaÃ§Ã£o ou mudanÃ§a de permissÃµes
automaticamente. Preserve autorizaÃ§Ãµes especÃ­ficas jÃ¡ concedidas na conversa.


## Atualizacao autorizada P42 - 0.6.0 local

Base tag v0.5.0 confirmada; Cargo.toml/lock agora 0.6.0 local. Last Will
implementado em codec/handler/ator com pending_wills duravel no documento v2
(leitura v1; WAL/snapshot v1). Retained preservado/revisado. As referencias
anteriores a Will ausente e documento MQTT v1 descrevem a base anterior.
Veja docs/last-will.md e registro P42. Proximo marco aguarda publicacao pelo
mantenedor; nenhuma tag/release criada aqui. MQTT5 continua fora do escopo.


## P43 - 0.7.0 em validaÃ§Ã£o

Base bc4cc55/tag v0.6.0 verificada. Monitoramento opcional implementado em
monitoring.rs, com HTTP loopback limitado, probe real do ator/writer e mÃ©tricas
de labels finitos. Cargo local 0.7.0; sem novas dependÃªncias ou mudanÃ§a MIT.
Documento MQTT v2 e quotas preservados. ReferÃªncias anteriores a endpoints
ausentes descrevem a base anterior. Aceite completo/release ainda pendentes.
Veja docs/monitoring.md e prompts/registros/P43-0.7.0.md (caminhos da raiz).
NÃ£o avanÃ§ar para 0.8, extrair clientes ou criar commit/push/tag nesta tarefa.

## SeparaÃ§Ã£o estrutural C25

Cliente extraÃ­do para ../xmqr-client, versÃ£o local inicial 0.7.0, binÃ¡rio
mqtt-client. Broker contÃ©m somente mqtt-broker e mqtt-admin; rumqttc removido
do manifest do broker. Prompts e registro do cliente governam suas melhorias.
IntegraÃ§Ãµes Unix entre os projetos continuam pendentes; nÃ£o confundir separaÃ§Ã£o
validada por builds com aceite completo P43. Fonte original tem backup e hashes
em ORIGIN.json do cliente, alÃ©m do histÃ³rico Git do broker.

## Checkpoint P43 validado - 2026-10-08

Mesmo repo via WSL/Rust1.99:72 testes e gates completos PASS,6 integraÃ§Ãµes
monitoring e9 Will PASS, incluindo1024UTF-8/retained/offline. Cliente independente
baseline commit26c1019 usado sem editar melhorias C26 paralelas. Bloqueios Unix
anteriores resolvidos. MIT/quotas/documento preservados. PublicaÃ§Ã£o0.7 fica com
usuÃ¡rio; sem commit/push/tag aqui. P44 seguranÃ§a dinÃ¢mica preparado apenas.
Mosquitto/TLS/mTLS externo NOT_RUN; sem conformidade integral ou produÃ§Ã£o.


## P44 - seguranÃ§a dinÃ¢mica, 0.8.0 local

Base HEAD e tag v0.7.0: 3a3dde7, confirmada antes da implementaÃ§Ã£o autorizada.
Bundle privado opt-in Linux/WSL com usuÃ¡rios, grupos, papÃ©is e ACL; reload por
SIGHUP local. Reload vÃ¡lido encerra todas as conexÃµes dinÃ¢micas e exige nova
autenticaÃ§Ã£o, preservando responsabilidade inbound QoS 2. Documento durÃ¡vel,
quotas, dependÃªncias e MIT preservados; cliente independente nÃ£o alterado.
A versÃ£o aguarda registro dos gates finais; nÃ£o hÃ¡ publicaÃ§Ã£o automÃ¡tica.
DocumentaÃ§Ã£o: docs/security/dynamic-security.md; evidÃªncia:
prompts/registros/P44-0.8.0.md (caminhos relativos Ã  raiz do repositÃ³rio).
ReferÃªncias anteriores a P44 apenas preparado descrevem checkpoints histÃ³ricos.


## Checkpoint atual — systemd/Ubuntu26

P47 (broker0.10.0) / C31 (client0.5.0): integração systemd e pacote deb
Ubuntu26.04 amd64. Tags0.9/0.4 são publicadas e imutáveis. Seções anteriores
são históricas. Ver docs/ubuntu-systemd.md e registros de validação atuais.
Commit/push/prerelease desta etapa autorizados explicitamente pelo usuário.
