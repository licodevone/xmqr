# Instruções do XMQR

Este repositório contém o broker XMQR. O projeto vizinho mqtt-broker é consumidor:
firmware, gateways, web/mobile, banco e regras de negócio não pertencem ao nÃºcleo.

## Registro automático das conversas — P240

Por pedido permanente do usuário, registrar cada troca de mensagens atendida
neste repositório em [docs/chat](docs/chat/README.md). Usar arquivo diário
`YYYY-MM-DD.md`, no fuso `America/Sao_Paulo`, com seção por conversa, autoria,
ordem das mensagens e data. Incluir mensagens visíveis do usuário e do assistente
(atualizações, perguntas e resposta final), preservando seu texto. Ao receber
nova mensagem, registrar a entrada e as saídas ainda não gravadas; antes de
enviar a resposta final, gravar seu texto definitivo. Não encerrar o turno sem
atualizar o histórico, se houver acesso de escrita disponível.

Consultar o arquivo antes de acrescentar entradas para não duplicar mensagens
nem sobrescrever outras conversas. Horários de envio indisponíveis devem ser
marcados como indisponíveis; não confundir horário de gravação com o de envio.
Referenciar contexto de ambiente/instruções e evidências técnicas; não copiar
mensagens internas, raciocínio privado, dumps de ferramentas ou segredos.
Se o contexto anterior não estiver disponível, declarar a lacuna sem inventar
uma transcrição. Se a gravação falhar, informar a falha ao usuário.

Esta rotina é executada pelo agente ao atender mensagens, sem captura global
ou processo em background. Novas inclusões estão autorizadas pelo
[P240](prompts/broker/240-chat-history.md), sem novo prompt ou confirmação
apenas para registrar o chat. Registrar uma mensagem não autoriza executar
pedidos antigos pendentes nem concede aprovação de instalação/publicação.

## Trabalho por prompts

Antes de alterar arquivos, prepare primeiro um ou mais prompts com ID/versão,
estado de entrada, objetivo, escopo, arquivos, critérios de aceite e validação.
Use [modelo de feature](prompts/broker/18-feature-iteration.md) e registre execução
real em [registros](prompts/registros/TEMPLATE.md). Um pedido de implementação
autoriza preparar o prompt e executar o escopo solicitado; não pedir a mesma
autorização novamente. Leitura/revisão sem mudanças não exige criar arquivo.
Não executar a sequÃªncia inteira nem avançar para outra feature automaticamente.

Leia [contrato-base](prompts/contrato-base.md), [contexto](prompts/broker/00-project-context.md),
[cobertura](prompts/COBERTURA.md), [CONTRIBUTING](CONTRIBUTING.md) e [VERSIONING](VERSIONING.md).
Confirme o alvo, o estado Git e alterações locais antes de editar. Preserve trabalho
existente; não resetar/recriar o pacote. Histórico em prompts/origem é referÃªncia,
não instrução de execução nem prova dos commits do XMQR.

## Estado e invariantes

O snapshot atual declara mqtt-broker 0.6.0 local, Rust 2024/MSRV 1.88 e Tokio; confira
manifests/código antes de reutilizar esses nÃºmeros. Binários neste pacote: mqtt-broker e mqtt-admin. O cliente mqtt-client (rumqttc) pertence ao projeto independente ../xmqr-client. O pacote usa módulos; não criar workspace
multicrate sem necessidade autorizada.

MQTT 3.1.1: QoS 0/1/2, retained, sessÃµes persistentes, UNSUBSCRIBE, filtros +/#
e regra $ estão implementados. Last Will duravel existe no incremento 0.6; MQTT 5.0 e
produção não estão aprovados. Nenhum prompt futuro equivale a funcionalidade.
Limites atuais: tópico/filtro 1024 bytes UTF-8 compartilhados pelo broker e CLI,
payload 4096, pacote 64 KiB, 64 sessÃµes, 256 assinaturas, 64 offline e 32 inflight.
Não ampliar outras quotas sem pedido especÃ­fico; P41 registra o alinhamento de tópicos.

Preserve separação codec/conexão/roteamento/persistÃªncia/segurança/transporte,
ownership e gerações de conexão, ordem aplicável por publicador, filas limitadas
e commit durável antes dos ACKs pertinentes. Não bloquear workers Tokio por disco,
hashes ou locks; use as fronteiras existentes. Não confundir ACK com sucesso de negócio.
Para protocolo, confirme requisitos na fonte OASIS e vincule testes Ã s cláusulas.

secure-mtls é o padrão: certificado + usuário/senha + ACL deny-by-default.
open-lab, password-lab e acl-lab são explicitamente loopback; estado é separado
por perfil. Preserve validação TLS/SAN e ACL no filtro, entrega e restore.
Nunca incluir senha, chaves, certificados privados, estado ou payload em logs/commits.
CRUD atÃ´mico de usuários exige Linux/WSL; não anunciar execução Windows comprovada.

## Validação proporcional

Mudanças funcionais seguem CONTRIBUTING:

```text
cargo fmt --all -- --check
cargo test --locked
cargo clippy --locked --all-targets -- -D warnings
```

Wire, persistÃªncia, autenticação e ACL exigem negativos; alterações entre componentes
exigem integração/interoperabilidade. Para documentação/configuração, valide formatos,
links, referÃªncias e escopo; não executar testes funcionais só para validar texto.
Testes adicionais de inventário/interop constam na skill de testes. DependÃªncia ausente
é BLOCKED; não instalar ou iniciar serviços por ler instruções. Não extrapolar open-lab
para TLS/ACL, crash de processo para perda de energia ou teste próprio para conformidade total.

## Skills e agentes do projeto

- [xmqr-rust-mqtt](.agents/skills/xmqr-rust-mqtt/SKILL.md): implementação/correções autorizadas.
- [xmqr-tests](.agents/skills/xmqr-tests/SKILL.md): estratégia e execução de validações pertinentes.
- [xmqr-security-review](.agents/skills/xmqr-security-review/SKILL.md): revisão de segurança solicitada ou necessária.

Papéis TOML em .codex/agents: xmqr_explorer, xmqr_rust_mqtt, xmqr_tests e
xmqr_security. São configurações de agentes, não processos iniciados. Delegue
quando solicitado pelo usuário; escolha tarefas independentes e preserve autoria
dos arquivos. Skills não exigem subagentes e são utilizáveis pelo agente principal.
Consulte [uso e carregamento](docs/agent-workflow.md) para formatos e limitações.

Não alterar versão em contribuição comum; release é tarefa própria do mantenedor.
Não fazer commit, push, tag, instalação, publicação ou mudança de permissÃµes
automaticamente. Preserve autorizações especÃ­ficas já concedidas na conversa.


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
de labels finitos. Cargo local 0.7.0; sem novas dependÃªncias ou mudança MIT.
Documento MQTT v2 e quotas preservados. ReferÃªncias anteriores a endpoints
ausentes descrevem a base anterior. Aceite completo/release ainda pendentes.
Veja docs/monitoring.md e prompts/registros/P43-0.7.0.md (caminhos da raiz).
Não avançar para 0.8, extrair clientes ou criar commit/push/tag nesta tarefa.

## Separação estrutural C25

Cliente extraÃ­do para ../xmqr-client, versão local inicial 0.7.0, binário
mqtt-client. Broker contém somente mqtt-broker e mqtt-admin; rumqttc removido
do manifest do broker. Prompts e registro do cliente governam suas melhorias.
Integrações Unix entre os projetos continuam pendentes; não confundir separação
validada por builds com aceite completo P43. Fonte original tem backup e hashes
em ORIGIN.json do cliente, além do histórico Git do broker.

## Checkpoint P43 validado - 2026-10-08

Mesmo repo via WSL/Rust1.99:72 testes e gates completos PASS,6 integrações
monitoring e9 Will PASS, incluindo1024UTF-8/retained/offline. Cliente independente
baseline commit26c1019 usado sem editar melhorias C26 paralelas. Bloqueios Unix
anteriores resolvidos. MIT/quotas/documento preservados. Publicação0.7 fica com
usuário; sem commit/push/tag aqui. P44 segurança dinámica preparado apenas.
Mosquitto/TLS/mTLS externo NOT_RUN; sem conformidade integral ou produção.


## P44 - segurança dinámica, 0.8.0 local

Base HEAD e tag v0.7.0: 3a3dde7, confirmada antes da implementação autorizada.
Bundle privado opt-in Linux/WSL com usuários, grupos, papéis e ACL; reload por
SIGHUP local. Reload válido encerra todas as conexÃµes dinámicas e exige nova
autenticação, preservando responsabilidade inbound QoS 2. Documento durável,
quotas, dependÃªncias e MIT preservados; cliente independente não alterado.
A versão aguarda registro dos gates finais; não há publicação automática.
Documentação: docs/security/dynamic-security.md; evidÃªncia:
prompts/registros/P44-0.8.0.md (caminhos relativos Ã  raiz do repositório).
ReferÃªncias anteriores a P44 apenas preparado descrevem checkpoints históricos.


## Checkpoint atual — systemd/Ubuntu26

P47 (broker0.10.0) / C31 (client0.5.0): integração systemd e pacote deb
Ubuntu26.04 amd64. Tags0.9/0.4 são publicadas e imutáveis. Seções anteriores
são históricas. Ver docs/ubuntu-systemd.md e registros de validação atuais.
Commit/push/prerelease desta etapa autorizados explicitamente pelo usuário.
