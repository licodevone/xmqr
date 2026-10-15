# Plano de paridade funcional do XMQR com Mosquitto

Atualizado em 2026-10-13. Fase3 aceita no recorte finito: broker/legadoadmin
0.11.6 eclient0.9.0, prereleases/.deb/Docker publicados e conferidos em P92.
Releases anteriores
0.11.5/0.8.1 preservadas; admin independente0.1.0 publicado e sem repin.
Evidências/limites: [aceite da fase3](phase3-acceptance.md).
O planejamento está completo como backlog
executável; as funcionalidades pendentes não estão implementadas por isso.
O propósito é evoluir um broker MQTT e seus utilitários com contratos próprios,
não reproduzir cada detalhe interno, arquivo ou opção de todas as versões Mosquitto.

## Escopo, referências e estado

Há três repositórios independentes: `xmqr` contém `mqtt-broker` e o legado
`mqtt-admin`; `xmqr-client` contém `mqtt-client`; [xmqr-admin](https://github.com/licodevone/xmqr-admin)
contém `xmqr-admin`0.1.0 (CLI e painel local autenticado de leitura). Somente
o admin legado acompanha a versão do broker. O novo tem versão/tag/release
próprias, reutiliza o core por commit imutável e não substitui os existentes.
ESP32 é consumidor externo, não o alvo do broker atual. Firmware, banco, web e
regras de negócio ficam fora do núcleo. MIT própria preservada; dependências
e arquivos de terceiros conservam suas respectivas licenças.

O [planejamento integrado de broker, client e admin](../../xmqr-admin/docs/planejamento-tres-sistemas.md)
detalha a trilha administrativa U01–U11 inspirada em Dynamic Security e
`mosquitto_ctrl`. Separa o painel de leitura atual da gestão futura de bundle,
revogação, canal autenticado e auditoria. A04 documental do repositório admin
não encerra os IDs A02–A09 desta matriz nem os testes pendentes da fase 3.

Referência de interoperabilidade reproduzível inicial: Mosquitto **2.0.22**,
imagem disponível no ambiente. A documentação online de Mosquitto também
descreve opções 2.1; essas capacidades estão assinaladas como extensões e
exigem campanha numa versão 2.1 escolhida, fixada por versão/digest e registrada
antes de qualquer alegação. Não confundir documentação atual com binário instalado.
OASIS é normativa para MQTT. Opções operacionais Mosquitto são referências,
não requisitos MQTT. Fontes oficiais consultadas em 2026-10-13:

- [MQTT 3.1.1 OASIS](https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/mqtt-v3.1.1.html).
- [MQTT 5.0 OASIS](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html).
- [Configuração Mosquitto](https://mosquitto.org/man/mosquitto-conf-5.html).
- [Publicador Mosquitto](https://mosquitto.org/man/mosquitto_pub-1.html) e
  [assinante Mosquitto](https://mosquitto.org/man/mosquitto_sub-1.html).
- [Administração Mosquitto](https://mosquitto.org/man/mosquitto_ctrl-1.html) e
  [Dynamic Security](https://mosquitto.org/documentation/dynamic-security/).
- [Multi-stage Docker](https://docs.docker.com/build/building/multi-stage/) e
  [publicação de imagem](https://docs.docker.com/reference/cli/docker/image/push/).

Estados: **existente** significa código/documentação local e evidência anterior
identificada; **parcial** indica uma capacidade com fronteiras ainda não aceitas;
**planejado** não autoriza anunciar suporte; **decisão** exige contrato antes de
implementar; **fora do escopo** não bloqueia a paridade prioritária definida aqui.
Registros anteriores não são testes reexecutados nesta revisão. O aceite desta
distribuição está nos registros P78/C42 e nos anexos das respectivas releases.

## Contratos preservados

MQTT 3.1.1 continua utilizável em cada entrega. Quotas de tópico/filtro 1024
bytes UTF-8, payload 4096 e pacote completo 65536 não aumentam por adicionar
MQTT5 ou novo transporte. Os tetos/defaults de conexões, sessões, assinaturas,
offline e inflight só mudam após medição e decisão explícitas. UTF-8 não é
normalizado. Ordenação aplicável por publicador, IDs e gerações de conexão,
ownership de QoS2 e commit durável antes dos ACKs pertinentes são invariantes.

O padrão é mTLS com senha e ACL deny-by-default; TLS/SAN não pode ter fallback
silencioso. Laboratórios sem TLS são somente loopback. Uma opção futura de
TLS sem certificado do cliente será opt-in, com autenticação MQTT e ACL.
Não introduzir listener remoto sem TLS para simplificar testes ou Docker.

Cada alteração de wire, configuração ou estado inclui migração, leitura de
versões anteriores, backup/rollback e negativos. Crash de processo não prova
queda de energia. ACK de protocolo não prova processamento de negócio.
Não usar locks bloqueantes, hash caro ou disco no hot path sem fronteira.

## Matriz de entregas

Cada ID é uma fatia futura de trabalho, não uma tag, versão prometida ou
prompt já executado. Preparar prompt específico no repositório responsável
antes do código. Critérios da coluna final são condições de aceite futuras.

| ID | Responsável e função | Estado / evidência atual | Dependência e aceite específico |
| --- | --- | --- | --- |
| U01 | Admin independente: CLI e painel de consulta | Aceito xmqr-admin0.1.0/P88; A01/A02/A03 locais do novo repo | Loopback autenticado/agregados somente leitura; release/deb/Docker aceitos; não encerra A02/A03/A09 da matriz |
| B01 | Broker: configuração TOML e quotas globais | Existente P52/P54/P55/P61 | Manter regressões de precedência, N/N+1, redução e recuperação sem truncar |
| B02 | Broker: QoS0/1/2, retained, sessões, Will e filtros | Existente P42/P61; matriz 3.1.1 ainda parcial | Vetores independentes e evidência por cláusula; não anunciar conformidade completa |
| B03 | Broker: conexões simultâneas e admissão sob saturação | P80 PASS até teto configurado64; sem SLA | N/N+1/vaga/RSS/CPU/percentis TCP/mTLS; performance-pressure.md |
| B04 | Broker: assinantes lentos, filas e fan-out sob pressão | P80 PASS limitado; shutdown corrigido0.11.4 | Filas4/8 e32/64, restart/QoS1/2, peer e vaga; não é ensaio prolongado |
| B05 | Broker: rate limits e quotas por identidade | Avaliação ADR0006 concluída; runtime adiado | Quotas mantidas; isolamento/fairness multitenant não implementados |
| B06 | Broker: erros de disco, ENOSPC, escrita curta e corrupção | Aceito recorte determinístico P86:54casos; patch0.11.5 | storage-faults.md; sem ACK/fan-out indevido, poison/reopen e WAL inválido preservado; não prova falhas físicas/energia |
| B07 | Broker: fuzzing de codec, estado e filtros | Aceito recorte P90/P95:18processos/seeds/corpus/mutações/watchdog PASS | Preservar corpus/limites/regressões; não LibFuzzer/ASAN/cobertura guiada |
| B08 | Broker/client: matriz externa 3.1.1 | Aceito recorte P91:87interop/19wire/12TLS e6soak>=600s PASS | Manter negativos/falhas históricas; campanha finita não é matriz exaustiva/conformidade completa |
| B09 | Broker: múltiplos listeners | Parcial P96: endpoints mTLS compartilham política/estado/limite; políticas por endpoint pendentes | B04/B08; políticas por endpoint, identidade isolada, sem duplicar roteadores/estado |
| B10 | Broker/client: TLS com senha sem certificado cliente | P97/C48 implementado e integrado, listener único opt-in | B09; CA/SAN obrigatório, senha/ACL e negativos, mTLS padrão inalterado |
| B11 | Broker: rotação de certificado/CA/CRL | Parcial CRL/startup | B09/B10; contrato para conexões ativas, validação antes de swap, rollback e CA expirada |
| B12 | Broker: reload geral da configuração | Decisão P98/ADR-0006: TOML restart-only; bundle/SIGHUP existente; transação obrigatória para eventual reload geral | B09; classificar campos hot-reload/restart-only, transação sem estado parcial |
| B13 | Broker: métricas operacionais e logs | Parcial monitor P43 | B03/B04; cardinalidade finita, sem payload/credenciais, probe do writer/ator |
| B14 | Broker: tópicos $SYS | Decisão | B13/A04; namespace explícito, ACL própria, frequência limitada e custo medido |
| A01 | Admin: CRUD local de usuários e fingerprint/hash | Existente, Unix; novo CLI xmqr-admin0.1.0 compatível e legado preservado | Manter arquivo privado, lock, symlink negativo, arquivo temporário e atualização atômica |
| A02 | Admin: gestão de grupos, papéis e ACL no bundle | Planejado; bundle manual existente | B08; validate/list/create/update/delete, referências inválidas recusadas e permissões mínimas |
| A03 | Admin: habilitar/revogar identidade e aplicar bundle | Planejado, reload conservador existente | A02 e canal A09 aceito para operação online; efeito nas conexões/sessões definido, QoS2 durável e auditabilidade |
| A04 | Admin: contrato do canal administrativo autenticado | Decisão | Contratos de política/revogação A02/A03, não sua execução online; aprovar IPC/HTTPS/MQTT reservado em ADR com RBAC, quotas/idempotência; o ADR não comprova canal implementado |
| A09 | Broker/admin: implementar e aceitar o canal escolhido | Planejado | A04 aprovado; executar pelo ator/fila limitada, autenticação/RBAC, auditoria mínima desde a primeira mutação e concorrência testadas, sem abrir WAL por segundo writer |
| A05 | Admin: consulta e evolução da auditoria sem segredos | Planejado | A02/A09 aceito com auditoria básica; ator/revisão/resultado, consulta, retenção/rotação, integridade e acesso limitado |
| A06 | Admin: backup/verify/restore | Existente P45 | Preservar offline, lock exclusivo, checksums e destino novo; planejar exportação seletiva sem substituir estado ativo |
| A07 | Admin: retenções e sessões administráveis | Planejado | A09 aceito/A06; listar com paginação/budget, excluir retained e desconectar via ator com ACL/admin explícita, sem vazar payload por padrão |
| A08 | Admin: plano de recuperação e diagnóstico | Parcial | A06/B06; dry-run/validação, espaço livre, backup, versões e saídas redigidas |
| C01 | Client: pub/sub, arquivo/stdin/linhas, QoS e JSONL | Existente C28/C39 | Preservar bytes, saída stdout separada de logs e resultado desconhecido após interrupção |
| C02 | Client: retained/Will e filtros de saída | Existente C41 | Regressão --count filtrado, ACKs preservados e diferença entre replay e publicação ao vivo |
| C03 | Client: excluir tópicos recebidos | Planejado | B08/C02; filtros locais, ACKs mantidos e contagem das mensagens exibidas |
| C04 | Client: publicação repetida/intervalo | Planejado | C01/B08; contagem finita, monotonic clock, Ctrl+C, sem reenviar resultado desconhecido |
| C05 | Client: perfis reutilizáveis e precedência | Planejado | B10; CLI/env/arquivo, secret-file, permissões e schema versionado |
| C06 | Client: novos formatos de saída | Decisão | C01/C03; contrato de escaping/binário/timestamp, limites e compatibilidade JSONL |
| C07 | Client: reconexão/backoff e timeout total | Aceito C45/C46:63testes/idle90s real/interop ampliada | Prazos protocolo/idle/total distintos, jitter/cancelamento; QoS1 pode retransmitir, QoS2 interrompido falha explicitamente |
| C08 | Client: Will binário e opções complementares | Decisão | C01/B08; validar tamanho antes de rede, propriedades compatíveis e documentação por protocolo |
| M01 | Broker/client: negociação MQTT5 e reason codes | Planejado | B06/B07/B08; codec separado da máquina de conexão, recusa correta por versão e regressão 3.1.1 |
| M02 | Broker/client: parser de propriedades MQTT5 | Planejado | M01; tipos, multiplicidade/contexto, limites antes de alocar e propriedades desconhecidas recusadas conforme OASIS |
| M03 | Broker/client: Clean Start e Session Expiry | Planejado | M02/A06; estado versionado, relógio e restart/crash, coexistência de sessões 3.1.1 |
| M04 | Broker/client: Message Expiry e Will Delay | Planejado | M03; deadlines duráveis, reconexão/takeover e ausência de entrega após expiração |
| M05 | Broker/client: Receive Maximum e Maximum Packet Size | Planejado | M03/B04; negociação bilateral, quotas por direção e ownership QoS preservado |
| M06 | Broker/client: Topic Alias | Planejado | M05; estado por conexão, reset após reconnect e alias inválido/borda recusados |
| M07 | Broker/client: metadados de publicação | Planejado | M02/M05; Content Type/Payload Format/User Properties/Response Topic/Correlation Data com persistência e budgets |
| M08 | Broker/client: opções de assinatura e identificadores | Planejado | M03/M07; No Local/Retain Handling/Retain As Published/Subscription Identifier, inclusive restore |
| M09 | Broker: assinaturas compartilhadas | Planejado | M08/B04/A04; estratégia de distribuição, QoS, falha de membro e fairness em ADR |
| M10 | Broker/client: autenticação estendida AUTH | Decisão | M02/A04; mecanismo definido, estados/challenges limitados, reautenticação e falha fechada |
| T01 | Broker/client: WebSocket/WSS | Planejado | B09/B10/M01; subprotocolo MQTT, fragmentação/controle, buffers/deadlines, regressão TCP e WSS/SAN |
| T02 | Broker: bridge entre brokers | Planejado | B08/B11/C07; reconexão, prefixos/direção, ACL, prevenção de loops e retained/QoS definidos |
| T03 | Broker: Unix domain sockets | Decisão | B09/A04; permissões, credencial do processo, ACL e portability sem substituir TLS remoto |
| T04 | Broker: TLS PSK e opções TLS avançadas | Decisão | B11; verificar suporte do provider e modelo de identidade antes de prometer implementação |
| X01 | Broker: hooks/plugins | Decisão | B08/A04; fronteira isolada/limitada, ABI/versionamento, falha fechada e nenhuma callback bloqueante no hot path |
| D01 | Todos: .deb, Docker Hub e checksums/proveniência | Existente base P63/C40, atualização P78/C42 | Commit exato, non-root, contexto seguro, versão real, lifecycle, mTLS e digest remoto |
| D02 | Todos: Ubuntu24 e arm64 | Planejado | B06/B08/D01; builders nativos, instalar/upgrade/rollback, units, TLS e matriz por arquitetura |
| D03 | Todos: APT assinado | Decisão | D02; hospedagem/domínio, chave sob custódia, rotação, índices assinados e política de atualização |
| D04 | Broker/admin: Windows nativo | Planejado | B06/A01/D01; abstrações de locks/fsync/rename/sinais, serviço Windows, ACL de arquivos e instalador homologado |
| D05 | Client: Windows e instaladores | Parcial CLI portátil | C05/D01; credenciais/TTY/encoding/Ctrl+C, instalação e upgrade/reversão sem segredos |
| E01 | ESP32 DevKit V1 como consumidor, campanha base | ACCEPTED P85: P83/P84 + Will/reconexão/retained restart/negativos/MosquittoQoS2/memória-probe PASS | Checklist esp32-phase2-checklist.md; escopo curto, não heap total/energia/pcapTLS/produção; não dependeB11 |
| E02 | ESP32: campanha de rotação e revogação | Planejado teste físico | E01/B11 na fase 4; mudança de CA/certificado/CRL, erro e recuperação observados na placa |

Cluster/alta disponibilidade distribuída, dashboard web, app móvel e broker
ESP32 Lite são trilhas separadas, não requisitos para equivaler funcionalmente
a um Mosquitto isolado. APIs de plugins, arquivos de persistência e comando
`mosquitto_ctrl` não terão compatibilidade binária automática com o XMQR.

## Sequência e critérios de encerramento

| Marco | Fatias | Pré-requisito | Evidência mínima de saída |
| --- | --- | --- | --- |
| Distribuição atual | D01; consulta de versão do admin | Base existente aceita | P78/C42, .deb/containers/hash/commit/digest, prereleases experimentais |
| Fase 2 capacidade | B03/B04, decisão B05, E01 e ampliação B08 | P72 | Repetições em máquina identificada, RAM/CPU/p95/p99, cenários lentos, teto observado e fatores limitantes; sem SLA inferido |
| Fase 3 robustez | B06/B07/B08/C07 | Saída fase 2 | Injeção de falhas, corpus, testes prolongados, matriz OASIS 3.1.1 e interop TLS/ACL, todos com resultado reproduzível |
| Fase 4 listeners e perfis | B09/B10/B11/E02, decisão B12, C05 | Saída fase 3 e E01 para E02 | Isolamento por listener, negativos TLS/CA/SAN/ACL, rotação/rollback, placa e precedência de perfis |
| Fase 5 operação | A02/A03, decisão A04, implementação A09, A05/A07/A08/B13, decisões B14/C06, C03/C04/C08 | Saída fase 4 | Canal administrativo implementado/aceito antes de auditoria online/sessões/retained, com autorização, recuperação e pendências explícitas |
| Fase 6A negociação | M01/M02 | Saída fase 5 | Vetores por contexto/propriedade, limites/reason codes, coexistência 3.1.1 e duas implementações externas |
| Fase 6B sessões | M03/M04 | Saída 6A | Migração, expiração, Will Delay, takeover/restart/crash sem perda silenciosa |
| Fase 6C fluxo | M05/M06/M07 | Saída 6B | Negociação bilateral, backlog, QoS0/1/2, alias/reset e propriedades duráveis |
| Fase 6D assinaturas e auth | M08/M09; decisão M10 | Saída 6C | Matriz MQTT5 por requisito e interop, shared/failure/fairness; subconjunto ausente explicitado |
| Fase 7 WebSocket | T01 | Saída fase 6D | Clientes independentes e browser de teste, fragmentação/limites/WSS e regressão TCP |
| Fase 8 bridge | T02 | Saída fase 7 | Mosquitto nas duas pontas, loops, reconnect, remapeamento e negativas de ACL/TLS |
| Fase 9 distribuição estendida | D02/D03/D04/D05; decisões T03/T04/X01 | Saída fase 3 para D02, contratos individuais para demais | Matriz nativa/containers/serviços/upgrade/reversão, versões suportadas e releases completas |

Antecipar D02 após a fase 3 pode evitar bloquear MQTT5 por empacotamento.
Antecipar outra fatia requer registrar mudança de dependência e riscos em ADR;
não misturar MQTT5, WebSocket e bridge numa única implementação. Uma fase pode
gerar várias versões aceitas. Os números futuros de versão não estão reservados.

## Contrato de teste e rastreabilidade

Para cada fatia, o prompt contém: ID/versão, commit de entrada, alterações
locais, objetivo observável, arquivos, exclusões, ameaça/limites, migração,
requisito OASIS quando aplicável e testes de aceite. O registro contém comandos,
códigos de saída, ambiente, hash do commit e resultados PASS/FAIL/BLOCKED/
NOT_RUN/NOT_APPLICABLE. Falha exige revisar o prompt antes da correção.

Camadas de evidência obrigatórias quando aplicáveis:

1. Unitários e negativos independentes do próprio encoder. Identificador da
   cláusula OASIS no caso MQTT, não uma porcentagem genérica de cobertura.
2. Integração de máquina de estados/roteamento/commit/ACL usando estado privado
   temporário. Confirmação somente após durabilidade configurada.
3. XMQR client → Mosquitto e mosquitto_pub/sub → XMQR, com versão/digest da
   referência registrado. Fixtures próprias não substituem essa etapa.
4. Segurança: CA/SAN/expiração/fingerprint/senha/ACL inválidos, restaurar com
   ACL reduzida, revogação, logs sem segredos e arquivos privados.
5. Capacidade: conexão ociosa/ativa, QoS0/1/2, fan-out, retained/offline,
   cliente lento, fila saturada, timeout e crescimento de memória. Relatar
   repetições, duração, percentis e recurso limitante, sem números inventados.
6. Distribuição: fmt/test/Clippy/build/inventário, instalação, upgrade,
   rollback, remoção e persistência, imagens non-root/read-only/caps-none,
   versão/labels, checksums e proveniência do commit.
7. Placa física para E01. Não substituir por screenshot ou simulador.

Cada linha da matriz deve apontar para teste/registro específico ao ser aceita.
Não atualizar checklist apenas pela existência de função, prompt ou CI.
Uma diferença de política permitida por MQTT (por exemplo, quota menor) não
é automaticamente defeito: documentar comportamento e teste de fronteira.

## Gestão, publicação e recuperação

O mantenedor autorizou nesta tarefa commit/push das mudanças aceitas, tags
e releases conforme marcos. Isso não autoriza promover gates pendentes a PASS.
Usar branches de trabalho e arquivos explicitamente selecionados quando houver
trabalho paralelo. Não incluir certificados privados, arquivos de estado,
credenciais, payloads ou artefatos locais preexistentes nos commits.

Código próprio continua MIT; avisos de terceiros ficam nos pacotes/imagens.
Inventário de licenças deve acompanhar a versão. Não copiar código Mosquitto
para buscar paridade nem atribuir MIT às suas dependências ou imagens-base.

Broker/admin e client têm versões independentes. Uma entrega documental não
obriga nova versão de runtime. Nesta revisão o patch acompanha distribuição e
identificação do admin. Mudança de feature geralmente gera minor0.x.0; correção
gera patch, após gates. Formato Debian acrescenta revisão -1 independente.

Fluxo de release: validar fontes → commit/push → conferir commit limpo → build
dos artefatos desse commit → testes dos artefatos → tag anotada imutável → push
da tag → prerelease com .deb/checksums/manifesto/evidência → Docker Hub
versionado → conferir digest remoto. Não mover latest por inferência e nunca
reescrever tags numéricas publicadas. Se a publicação falhar, registrar o
ponto exato; não anunciar entrega concluída e não repetir uploads incertos.

O .deb desta etapa é **Ubuntu26 amd64**; Docker usa **Debian Bookworm** com
binários compilados para seu runtime. .deb e imagem são artefatos diferentes:
não instalar esse .deb Ubuntu no Bookworm nem anunciar Debian/Ubuntu24/arm64
como homologados por existir um container. Admin está no .deb do broker e
tem imagem própria `lepinheiro100/xmqr-admin`, não um serviço de rede.

O parágrafo anterior é do legado `mqtt-admin`. O novo xmqr-admin0.1.0 tem
deb separado `xmqr-admin_0.1.0-1_amd64.deb` e imagem
`lepinheiro100/xmqr-admin-ui:0.1.0`, não-root10001 e SIGTERM. Seu painel local
é somente leitura do monitor; não oferece o canal A09. Dockerloopback não
é exposto por publicar uma porta; laboratório usou namespace compartilhado.
Release/checksums/gates: [P88](../prompts/registros/P88-admin.md).

Para atualização do broker: backup offline verificado, stop coordenado,
preservar volume/configuração, instalar versão aceita, verificar recuperação
e somente então iniciar. Rollback exige compatibilidade da versão do estado;
com migração incompatível, usar backup anterior, nunca sobrescrever estado
ativo. Operações diretas sobre arquivos de estado (backup/verify/restore) são
offline e precisam respeitar locks; backup/restore exigem broker parado.
Operações administrativas online futuras usam exclusivamente o canal A09 e
o ator do broker: não abrem o WAL nem adquirem um segundo writer. O CLI atual
não oferece esse canal online; A04 aprovado sozinho não libera A05/A07.

Releases continuam experimentais. Produção/1.0 exige matriz normativa completa
para o subconjunto anunciado, segurança e operação validadas, campanha longa,
suporte/plataformas definidos e plano de resposta a falhas. Não há prazo fixo
ou desempenho prometido; estimar cada marco após medir a fatia anterior.

## Próxima execução e decisões abertas

P80/C43 completaram software; P83/P84/P85 fecharam E01 físico. Fase2 ACCEPTED,
com limites em phase2-acceptance.md. Próxima etapa é uma fatia de robustez da
fase3 por prompt próprio, ainda não executada. CLI não virou gerador de carga.
Will/reconexão/retained restart/negativos/MosquittoQoS2 e memória-probe medidos
na COM4; não prometer energia/heap total/pcapTLS/produção. [RegistroP85](../prompts/registros/P85-e01-campanha.md).

Decisões a resolver nos respectivos prompts: metas e hardware da campanha;
quotas por identidade; canal administrativo; política de $SYS; expiração e
clock persistente; fairness shared; mecanismos AUTH; suporte TLS PSK no
provider; ABI/plugins; APT/domínio/custódia de chave; garantia de fsync Windows.
São decisões identificadas e com gate, não campos escondidos nem compromisso
de implementação. Planejamento concluído significa que esses pontos têm
responsável, dependência e aceite definidos; execução permanece no checklist.
