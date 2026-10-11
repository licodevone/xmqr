# P55 rev1 — quotas configuráveis do estado MQTT

## Estado de entrada e objetivo

Base inspecionada: broker HEAD 7d5f371 (P54), pacote 0.10.0; confirmar HEAD, branch e alterações locais antes de executar. Há alteração preexistente em AGENTS.md: preservar integralmente. Client é projeto independente; não assumir seu HEAD nem importar seu crate.

P52 fornece TOML version=1; P54 configura apenas admissão TCP (1..64, default64). Registro P54 informa 92 testes e gates WSL aprovados, além de 4 integrações C27; esses resultados não foram reexecutados na preparação P55. Fase 1 de docs/evolution-plan.md permanece aberta.

Objetivo: configurar quotas lógicas do estado por processo e propagá-las coerentemente ao ator e store. Reduções incompatíveis com estado recuperado devem recusar inicialização antes de expor listeners ou efetuar transições MQTT, sem truncar sessões, filas, retained ou inflight.

## Leitura e escopo

Ler AGENTS.md, contrato-base, contexto, COBERTURA, CONTRIBUTING, VERSIONING, docs/architecture/configuration.md, docs/evolution-plan.md e registros P52/P54. Aplicar skills locais xmqr-rust-mqtt e xmqr-tests quando executar implementação/validação. Confirmar cláusulas OASIS se alterar comportamento de protocolo.

Nesta preparação: atualizar checkpoint documental/contexto e registrar revisão P54, sem código funcional. Na execução futura: src/configuration.rs, src/main.rs, src/mqtt/{mod,router,store}.rs, testes pertinentes, script isolado de validação e documentação/exemplo packaging/broker.toml.example. Novo módulo de limites é permitido se evitar duplicação. Preservar APIs existentes com defaults quando necessário.

## Contrato proposto

Adicionar a [limits], com defaults iguais aos tetos atuais e apenas reduções positivas:

| Campo TOML | Override explícito | Faixa/default |
| --- | --- | --- |
| max_sessions | MQTT_MAX_SESSIONS | 1..64 / 64 |
| max_retained | MQTT_MAX_RETAINED | 1..256 / 256 |
| max_subscriptions | MQTT_MAX_SUBSCRIPTIONS | 1..256 / 256 por sessão |
| max_offline | MQTT_MAX_OFFLINE | 1..64 / 64 mensagens por sessão |
| max_inflight | MQTT_MAX_INFLIGHT | 1..32 / 32 por direção por sessão |

Não aceitar zero como ilimitado nem ampliar tetos sem medição. Defaults < TOML < ambiente explícito; override inválido não faz fallback. Rejeitar tipos errados, negativos, overflow, não Unicode e campos desconhecidos sem expor valores sensíveis. Validar configuração antes de criar estado/listeners.

Usar uma representação tipada de quotas, validada uma vez e compartilhada entre validação do store e decisões do router. max_sessions não é max_connections: não impor igualdade; documentar independência. Pending Wills mantêm vínculo/limite coerentes com sessões. max_inflight limita separadamente inbound QoS2 e outbound, não sua soma.

Aplicar quotas na recuperação e antes de cada commit, incluindo retained, assinaturas, offline e ambos inflights. Verificar imagem recuperada antes da limpeza de clean sessions, publicação de Wills, replay ou snapshot. Encerrar corretamente o writer se a abertura for recusada. Não usar mudanças de configuração para descartar dados. Testar que nenhuma transição/regravação/snapshot altera o estado lógico no startup recusado; se recuperação física modificar WAL por mecanismo existente, documentar precisamente e comprovar preservação dos registros comprometidos.

Preservar backpressure e semântica atual de saturação; definir e documentar comportamento de cada quota por operação. Não reconhecer sucesso MQTT antes do commit nem descartar responsabilidade QoS já aceita. Não introduzir eviction, ACK enganoso, bloqueio de Tokio ou reconexão infinita. Separar filas duráveis das capacidades internas COMMAND_CAPACITY/DELIVERY_CAPACITY, que ficam fixas nesta fatia.

## Compatibilidade e exclusões

Configuração imutável por processo, aplicada no restart; SIGHUP continua exclusivo do bundle de segurança. Preservar MQTT3.1.1, TLS/SAN, ACL, gerações, ordenação e MIT. Manter documento MQTT v2 com leitura v1, chave e WAL/snapshot existentes; quotas não são novos campos persistidos. Rollback seguro: restaurar defaults/limites compatíveis, nunca editar o estado para fazê-lo caber.

Não configurar payload4096, pacote64KiB, tópico1024, document bytes, IDs ou principal nesta entrega. Não implementar MQTT5, listeners adicionais, WS, bridge, rate limits ou quotas por identidade. Não modificar client, versão, serviços reais, pacotes instalados, tags ou release. Não fazer commit/push automaticamente; autorização histórica do P54 não se transfere.

## Validação e critérios de aceite

1. Parser/defaults/precedência e negativos de cada campo; configuração inválida não cria estado nem abre porta.
2. Cada quota aceita exatamente N e rejeita N+1 segundo contrato documentado; valores iguais aos defaults preservam comportamento anterior. Cobrir independência entre conexões e sessões, inbound/outbound inflight e pendências de Will.
3. Criar estado compatível com defaults contendo mais que o limite reduzido de cada quota; reinício deve falhar antes de serviço/replay/mutações. Restaurar limite suficiente e comprovar sessões, retained, filas e QoS íntegros, inclusive v1/v2, crash/restart e Will.
4. Integração em diretórios temporários com broker/client independente, --client explícito quando aplicável; testar QoS0/1/2, retained, offline, retomada, cancelamento, ACL/TLS pertinentes e regressão P54. Mosquitto externo sem pré-requisito disponível é NOT_RUN/BLOCKED, nunca PASS.
5. Executar cargo fmt --all -- --check; cargo test --locked; cargo clippy --locked --all-targets -- -D warnings; cargo build --locked --bins em ambiente confirmado. Usar testes específicos depois de correções; revisar este prompt antes de corrigir falhas.
6. Registrar comandos, ambiente/toolchain, commits dos dois projetos, contagens, códigos de saída e resultados PASS/FAIL/BLOCKED/NOT_RUN em prompts/registros/P55-quotas-estado.md. Atualizar README, changelog, exemplo, configuração, cobertura e plano com limites implementados e lacunas restantes.

Aceite exige gates e recuperação/redução sem perda aprovados. P55 não encerra sozinho fase 1: payload/pacote, validação do client e instalação/upgrade do pacote continuam a avaliar em prompts próprios. Não iniciar fase 2 para ocultar pendências.
