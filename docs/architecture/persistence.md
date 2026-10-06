# Persistência durável: implementação inicial

Esta camada chave/valor agora alimenta o ator de sessões MQTT em `src/mqtt/store.rs`. O broker mantém assinaturas de `CleanSession=0`, fila offline QoS 1/2, inflight nos dois sentidos e mensagens retidas. O módulo de WAL público está em `src/persistence`.

Decisão de arquitetura: [ADR 0001](adr-0001-durable-persistence.md).

## Contrato de commit

- Há exatamente um escritor por diretório, protegido por lock de arquivo. Tasks Tokio usam `PersistenceHandle`, cuja fila limitada (256 comandos) aplica backpressure e encaminha as operações a uma thread de disco dedicada.
- `put` e `delete` gravam **um registro completo por operação**, com sequência monotônica e CRC32, e só retornam sucesso depois de `sync_data` no WAL. A aplicação em memória ocorre depois do sync. Assim, cada mutação individual é atômica no replay; **não há transações multichave**.
- O ator MQTT grava um documento versionado único por transição; isso torna atômicas as mudanças de sessão, retained e inflight. `PUBACK`, `PUBREC` e `PUBCOMP` só saem depois do `put`/`fsync` correspondente. Se o resultado do armazenamento for incerto, o ator fecha as conexões e deixa de aceitar mutações até reinício e replay do WAL. QoS 2 registra PUBLISH antes de PUBREC e só roteia uma vez ao registrar PUBREL.
- Falha de escrita envenena a instância: a API assíncrona também recusa leituras após isso, e não há retry no mesmo processo. Feche, investigue o erro e reabra para replay. Falhas de checksum, versão ou lacunas de sequência interrompem a abertura; não são ignoradas.

## Arquivos e recuperação

| Arquivo | Finalidade |
| --- | --- |
| `state.wal` | Cabeçalho com versão; registros de comprimento limitado, sequência, operação, chave/valor e CRC32. |
| `state.snapshot` | Estado completo com versão de formato, sequência e CRC32. |
| `state.snapshot.tmp` | Snapshot em preparação, descartado na recuperação. |
| `state.lock` | Impede dois escritores cooperativos no mesmo diretório. |

Um snapshot é escrito em arquivo temporário, sincronizado com `sync_all`, publicado por rename no mesmo diretório e seguido de `fsync` do diretório **antes** de compactar o WAL. A recuperação usa o snapshot publicado e reaplica apenas registros posteriores à sua sequência. Uma cauda incompleta do WAL é truncada e sincronizada; registro completo com checksum inválido causa erro. Uma interrupção depois da publicação e durante a truncagem do cabeçalho do WAL é recuperável a partir do snapshot já sincronizado.

O diretório de dados deve existir previamente. A garantia de `fsync` do diretório está implementada para Unix; em outros sistemas a abertura falha explicitamente. Arquivos devem residir em um filesystem local que honre `fsync` e rename atômico no mesmo diretório. Esta garantia não cobre hardware que mente sobre flush, filesystems remotos, corrupção arbitrária, perda de todos os arquivos, nem backup externo. CRC32 detecta corrupção acidental; **não autentica dados** contra adulteração maliciosa.

## Limites e evolução

Chaves: 1–1024 bytes; valores: até 1 MiB; estado em memória: até 64 MiB/100 mil entradas; snapshot: até 80 MiB. O agregado MQTT tem quotas mais estreitas: 64 sessões, 256 tópicos retidos, 256 assinaturas por sessão, 64 mensagens offline e 32 inflight por direção/sessão, payload de 4 KiB e documento de 1 MiB. A fila de 256 comandos limita trabalho pendente. O ator faz snapshot a cada 128 commits, mas o WAL não tem quota de disco independente: monitore espaço livre e faça backup. `fsync` do documento inteiro por mutação prioriza durabilidade e é um gargalo conhecido; não há benchmark que sustente uso em alta carga.

O snapshot WAL e o documento MQTT interno mantêm a versão 1. Os filtros
wildcard preservam a representação textual e são validados na desserialização.
Versões desconhecidas falham na abertura; não existe rollback automático.
Sessões MQTT 3.1.1 com `CleanSession=0` não expiram automaticamente.
O roteiro externo verifica QoS 0/1/2, retained e sessão wildcard após queda
do processo. Ainda faltam Will, métricas de quota, cobertura externa completa,
perda real de energia/VM, fuzzing e benchmarks de recuperação/carga antes de produção.

A 0.5 lê o estado 0.4, mas a 0.4 não restaura assinaturas wildcard: antes de
retornar, remova-as com UNSUBSCRIBE ou restaure um backup anterior completo
em diretório separado. Não reverta WAL e snapshot parcialmente.

### Migração e retorno manual

Antes de atualizar uma instância, pare o broker e faça backup **completo** do diretório `MQTT_STATE_DIR` e dos arquivos de usuário/ACL, preservando permissões. Confirme as versões do binário e dos arquivos de estado antes de iniciar a nova versão. A versão 0.1.x não possuía sessões MQTT persistentes; para experimentar 0.2.0, use um diretório de estado **novo e exclusivo**, sem reaproveitar dados de outra instância. Para voltar ao binário antigo, pare primeiro a versão nova e restaure o backup completo correspondente à versão antiga em um diretório separado; não tente abrir ou reverter parcialmente o WAL/snapshot 0.2.0 no lugar. Valide a recuperação em laboratório antes de qualquer mudança na porta 8883. Backups devem ser mantidos fora do diretório ativo e testados por restauração.

## Verificação

`cargo test --all-targets` cobre round trip, substituição/deleção, bloqueio de segundo escritor, cauda truncada, checksums e versões inválidos, WAL ausente após snapshot, transições QoS/retained e interrupções forçadas do processo. Os testes de interrupção usam `process::exit`; validam recuperação após queda do processo, **não simulam perda de energia ou cache volátil de disco**. Uma prova local com clientes Rust validou QoS 1/2, retained e fila offline após reinício em porta de teste separada.
