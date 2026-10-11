# P55 rev2 — quotas configuráveis do estado MQTT

## Estado de entrada e objetivo

Base de execução: broker HEAD 4fe905a, pacote 0.10.0, árvore limpa na conferência inicial. Preparação rev1 usou 7d5f371 (P54). Confirmar HEAD e alterações locais antes de executar. Client é projeto independente; não assumir seu HEAD nem importar seu crate.

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

Não configurar payload4096, pacote64KiB, tópico1024, document bytes, IDs ou principal nesta entrega. Não implementar MQTT5, listeners adicionais, WS, bridge, rate limits ou quotas por identidade. Nesta fatia manter client, versão, serviços reais e pacotes instalados. Pedido atual autoriza melhorias e criação de tags vinculadas a releases quando os critérios estiverem cumpridos. Preparar marco de versão em tarefa de release após validação completa; não marcar código incompleto nem reescrever tags existentes.

## Validação e critérios de aceite

1. Parser/defaults/precedência e negativos de cada campo; configuração inválida não cria estado nem abre porta.
2. Cada quota aceita exatamente N e rejeita N+1 segundo contrato documentado; valores iguais aos defaults preservam comportamento anterior. Cobrir independência entre conexões e sessões, inbound/outbound inflight e pendências de Will.
3. Criar estado compatível com defaults contendo mais que o limite reduzido de cada quota; reinício deve falhar antes de serviço/replay/mutações. Restaurar limite suficiente e comprovar sessões, retained, filas e QoS íntegros, inclusive v1/v2, crash/restart e Will.
4. Integração em diretórios temporários com broker/client independente, --client explícito quando aplicável; testar QoS0/1/2, retained, offline, retomada, cancelamento, ACL/TLS pertinentes e regressão P54. Mosquitto externo sem pré-requisito disponível é NOT_RUN/BLOCKED, nunca PASS.
5. Executar cargo fmt --all -- --check; cargo test --locked; cargo clippy --locked --all-targets -- -D warnings; cargo build --locked --bins em ambiente confirmado. Usar testes específicos depois de correções; revisar este prompt antes de corrigir falhas.
6. Registrar comandos, ambiente/toolchain, commits dos dois projetos, contagens, códigos de saída e resultados PASS/FAIL/BLOCKED/NOT_RUN em prompts/registros/P55-quotas-estado.md. Atualizar README, changelog, exemplo, configuração, cobertura e plano com limites implementados e lacunas restantes.

Aceite exige gates e recuperação/redução sem perda aprovados. P55 não encerra sozinho fase 1: payload/pacote, validação do client e instalação/upgrade do pacote continuam a avaliar em prompts próprios. Não iniciar fase 2 para ocultar pendências.

## Execução rev2

Pedido atual autoriza implementar P55. Cargo Windows1.98.1 disponível; wsl --list --quiet não retornou distribuições nesta sessão. Gates Unix devem ser registrados BLOCKED se o ambiente continuar indisponível; sem release/tag de aceite nessa condição.

### Ajuste rev2.1 após primeiro gate

Fmt detectou inserção indevida de inicializador no bloco impl Actor. Corrigir somente a inserção sintática e repetir fmt/check antes dos testes.

### Ajuste rev2.2

Check localizou também inicializadores duplicados na declaração Actor e construção de produção. Remover duplicatas, preservando defaults apenas nos testes.

### Ajuste rev2.3

Check apontou parâmetro de quotas ausente na assinatura start_router. Completar propagação; corrigir import Stdio condicionado a Unix para gate Windows.

### Resultado do gate completo Windows

Suíte falhou em 25 testes que exigem fsync de diretório Unix; 37 passaram. Não alterar garantias de persistência para fazê-los passar. Validar testes portáveis específicos e registrar aceite Unix BLOCKED.

### Ajuste rev2.4 após Clippy

Preservar nomes max_* no contrato público e TOML; justificar exceção local struct_field_names. Corrigir marcação Rustdoc InvalidInput e repetir Clippy.


## Retomada rev3 — 2026-10-11

Entrada confirmada: broker HEAD 10e1b59e801b3a1e5a4d79531a801e5c0b4faeb0, árvore com AGENTS.md preexistente modificado, preservado. Retomar somente P55 e fase1. Aplicar xmqr-rust-mqtt/xmqr-tests. Não mudar versão ou publicar marco enquanto aceite Unix pendente.

Escopo adicional: teste Unix de startup real para cada quota nos documentos v1/v2, comparação byte a byte de WAL/snapshot após recusa, observação de listener e reabertura imediata da imagem comprometida; harness isolado scripts/verify_state_limits.py reutilizando fixtures MQTT independentes e client explícito. Gates portáveis serão repetidos; Unix ausente será BLOCKED.

Revisão identificou que falha na publicação de Will por saturação preserva a entrada live e permite tentativa posterior de takeover sobre uma Will pendente. Corrigir para encerrar o ator/conexões sem confirmar, sobrescrever ou descartar a imagem aceita; o restart exige quotas suficientes. Negativos devem comprovar pending Will e fila originais preservadas, fechamento e recuperação posterior sem perda. Na recuperação, aguardar shutdown do writer antes de retornar erro ao publicar Will/commit, permitindo reabertura imediata. Não afrouxar fsync ou invariantes para Windows.

Documentar a política de Will saturada em docs/architecture/configuration.md/README/CHANGELOG e neste registro. O coordenador atualizará docs/evolution-plan.md após resultados reais, mantendo fase1 aberta. Mosquitto/TLS/ACL externo e pacote/upgrade continuam gates próprios, sem alegação nova de aceite.

### Ajuste rev3.1 após gates

Suíte Windows:38 PASS/25 FAIL/1 ignorado;25 falhas exigem fsync Unix e não serão contornadas. Clippy apontou função do novo teste de startup com104 linhas e format_push_string. Extrair montagem da fixture e usar fmt::Write; repetir fmt/Clippy e compilação afetada, sem alterar cenários.

### Ajuste rev3.2 — gate de inventário no Windows

Python3.12.14 encontrado em caminho explícito. ast.parse do harness PASS e sua execução retornou BLOCKED/exit2 fora de Unix. license_inventory.py --check falhou ao ler LICENSE com locale cp1252; repetir com -X utf8, sem alterar conteúdo/licença ou flexibilizar o inventário.

### rev4 — teste executado no Ubuntu26

Teste state_limits falhou antes de chegar à quota porque sua imagem manual
não tinha .mqtt-broker-profile e o broker corretamente tratou-a como segura.
Gravar marcador open-lab na fixture antes de capturar hashes; preservar o
teste de todos os arquivos e a proteção runtime. Repetir12 cenáriosv1/v2 e suíte.

### rev5 — motivo específico na representação de erro

Com marcador, runtime recusou corretamente Limit("sessions"); o teste esperava
Display, mas Termination de main emiteDebug. Aceitar Display ou Debug com o
mesmo motivo específico; não aceitar erro genérico. Preservar checks de porta,
hashes de todos os arquivos e reabertura imediata. Repetir suíte completa.
