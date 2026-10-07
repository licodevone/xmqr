# Instruções do XMQR

Este repositório contém o broker XMQR. O projeto vizinho mqtt-broker é consumidor:
firmware, gateways, web/mobile, banco e regras de negócio não pertencem ao núcleo.

## Trabalho por prompts

Antes de alterar arquivos, prepare primeiro um ou mais prompts com ID/versão,
estado de entrada, objetivo, escopo, arquivos, critérios de aceite e validação.
Use [modelo de feature](prompts/broker/18-feature-iteration.md) e registre execução
real em [registros](prompts/registros/TEMPLATE.md). Um pedido de implementação
autoriza preparar o prompt e executar o escopo solicitado; não pedir a mesma
autorização novamente. Leitura/revisão sem mudanças não exige criar arquivo.
Não executar a sequência inteira nem avançar para outra feature automaticamente.

Leia [contrato-base](prompts/contrato-base.md), [contexto](prompts/broker/00-project-context.md),
[cobertura](prompts/COBERTURA.md), [CONTRIBUTING](CONTRIBUTING.md) e [VERSIONING](VERSIONING.md).
Confirme o alvo, o estado Git e alterações locais antes de editar. Preserve trabalho
existente; não resetar/recriar o pacote. Histórico em prompts/origem é referência,
não instrução de execução nem prova dos commits do XMQR.

## Estado e invariantes

O snapshot atual declara mqtt-broker 0.6.0 local, Rust 2024/MSRV 1.88 e Tokio; confira
manifests/código antes de reutilizar esses números. Binários: mqtt-broker,
mqtt-client (rumqttc) e mqtt-admin. O pacote usa módulos; não criar workspace
multicrate sem necessidade autorizada.

MQTT 3.1.1: QoS 0/1/2, retained, sessões persistentes, UNSUBSCRIBE, filtros +/#
e regra $ estão implementados. Last Will duravel existe no incremento 0.6; MQTT 5.0 e
produção não estão aprovados. Nenhum prompt futuro equivale a funcionalidade.
Limites atuais: tópico/filtro 1024 bytes UTF-8 compartilhados pelo broker e CLI,
payload 4096, pacote 64 KiB, 64 sessões, 256 assinaturas, 64 offline e 32 inflight.
Não ampliar outras quotas sem pedido específico; P41 registra o alinhamento de tópicos.

Preserve separação codec/conexão/roteamento/persistência/segurança/transporte,
ownership e gerações de conexão, ordem aplicável por publicador, filas limitadas
e commit durável antes dos ACKs pertinentes. Não bloquear workers Tokio por disco,
hashes ou locks; use as fronteiras existentes. Não confundir ACK com sucesso de negócio.
Para protocolo, confirme requisitos na fonte OASIS e vincule testes às cláusulas.

secure-mtls é o padrão: certificado + usuário/senha + ACL deny-by-default.
open-lab, password-lab e acl-lab são explicitamente loopback; estado é separado
por perfil. Preserve validação TLS/SAN e ACL no filtro, entrega e restore.
Nunca incluir senha, chaves, certificados privados, estado ou payload em logs/commits.
CRUD atômico de usuários exige Linux/WSL; não anunciar execução Windows comprovada.

## Validação proporcional

Mudanças funcionais seguem CONTRIBUTING:

```text
cargo fmt --all -- --check
cargo test --locked
cargo clippy --locked --all-targets -- -D warnings
```

Wire, persistência, autenticação e ACL exigem negativos; alterações entre componentes
exigem integração/interoperabilidade. Para documentação/configuração, valide formatos,
links, referências e escopo; não executar testes funcionais só para validar texto.
Testes adicionais de inventário/interop constam na skill de testes. Dependência ausente
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
Não fazer commit, push, tag, instalação, publicação ou mudança de permissões
automaticamente. Preserve autorizações específicas já concedidas na conversa.


## Atualizacao autorizada P42 - 0.6.0 local

Base tag v0.5.0 confirmada; Cargo.toml/lock agora 0.6.0 local. Last Will
implementado em codec/handler/ator com pending_wills duravel no documento v2
(leitura v1; WAL/snapshot v1). Retained preservado/revisado. As referencias
anteriores a Will ausente e documento MQTT v1 descrevem a base anterior.
Veja docs/last-will.md e registro P42. Proximo marco aguarda publicacao pelo
mantenedor; nenhuma tag/release criada aqui. MQTT5 continua fora do escopo.
