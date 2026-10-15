# Canal administrativo local — fase 5

Com `MQTT_SECURITY_BUNDLE` dinâmico no Linux/WSL, configure antes do startup:

```text
MQTT_ADMIN_SOCKET=/caminho/privado/admin.sock
MQTT_ADMIN_VIEW_TOKEN_FILE=/caminho/privado/view.token
MQTT_ADMIN_OPERATOR_TOKEN_FILE=/caminho/privado/operator.token
```

Os diretórios finais precisam ser reais e modo 0700; os arquivos de token,
regulares, sem symlink, modo 0600 e mesmo UID do diretório/socket, com 64 dígitos
hexadecimais distintos. `xmqr-admin token-init --file NOVO_ARQUIVO` 0.4.0 gera
os arquivos. Não incluir tokens em repositório, URL, argumentos ou logs. O
socket é 0600 e recusa caminho preexistente, configuração parcial ou política
estática. O UID do peer precisa coincidir com o dono do socket.

Cada conexão aceita uma linha JSON v1 de até 16 KiB, com prazo absoluto de 2 s
e no máximo 16 handlers. `request_id` tem 128 bits hexadecimais; após rotação,
os primeiros 32 codificam `admin_epoch` e os 96 restantes são aleatórios.
Tokens `viewer` e `operator` podem consultar `status` e `receipt`; só `operator`
pode executar `reload`.

```json
{"version":1,"request_id":"0123456789abcdef0123456789abcdef","operation":"status","token":"<64 hex>"}
```

`status` retorna `security_generation` da política em memória, `admin_epoch`,
`broker_version`,
ocupação dos recibos e `ready` do probe real do ator/writer. `reload` exige
`expected_generation` obtida de
`status` e `bundle_sha256` do arquivo privado já editado e validado. O broker
relê o bundle, confere o hash, valida a política e reconcilia sessões no ator.
O recibo de sucesso é gravado no mesmo commit WAL da mudança antes da publicação
da política. Conexões dinâmicas são encerradas e precisam se autenticar de novo.
O inbound QoS2 já aceito conserva sua responsabilidade durável.

```json
{"version":1,"request_id":"fedcba9876543210fedcba9876543210","operation":"reload","token":"<operator hex>","expected_generation":1,"bundle_sha256":"<64 hex>"}
```

O resultado contém `applied_generation` e `replayed`. Repetir exatamente ID,
hash e geração retorna o recibo anterior; mudar qualquer dos dois campos
produz `request_conflict`. Uma geração atual diferente produz
`stale_generation`; arquivo alterado, `bundle_changed`. O limite é de 128
recibos persistidos. Ao atingir o limite, um novo ID recebe
`receipt_capacity`; IDs antigos permanecem consultáveis e nenhuma mutação é
feita. Isto requer manutenção planejada antes de ampliar o uso operacional.

```json
{"version":1,"request_id":"0123456789abcdef0123456789abcdef","operation":"receipt","token":"<viewer ou operator hex>","target_request_id":"fedcba9876543210fedcba9876543210"}
```

`receipt` retorna ID alvo, hash da operação (`request_sha256`), UID, operação, resultado
`committed`, timestamp UTC em milissegundos, época e gerações esperada/aplicada. Não
inclui token ou conteúdo do bundle. Em timeout, desconexão ou
`result_unknown`, consultar o recibo antes de repetir; ausência de resposta
da consulta ainda é resultado desconhecido. A geração de segurança em memória
reinicia após restart; a geração aplicada no recibo é histórica. O ID garante
deduplicação do reload já confirmado mesmo após restart.

O operator também pode consultar `sessions_list` (até 16 por página) e
`retained_list` (até 8 por página), com `limit` opcional e `cursor` lexical
opcional. Respostas têm `items` e `next_cursor`; `null` encerra a listagem.
Sessões trazem client ID, status conectado/persistente e contagens de
assinaturas, filas e QoS2; retained traz tópico, QoS e tamanho do payload,
**sem bytes de payload**. Viewer recebe `forbidden`. As páginas não são um
snapshot estável durante publicações/conexões concorrentes. `retained_delete`
exige `topic` concreto e token operator; remove apenas uma mensagem retained
existente, sem tocar em publicações já entregues. Retorna `deleted` e
`replayed`. ID repetido com o mesmo tópico devolve o recibo, inclusive após
restart; ID usado em operação/alvo diferente é conflito. Tópico ausente dá
`not_found` sem commit. A consulta de receipt mostra somente hash do alvo,
sem payload. `session_disconnect` exige `client_id` exato e token operator;
somente conexão ativa é alvo. A ação equivale a encerramento não gracioso:
Will autorizado é publicado, sessão persistente e inbound QoS2 já aceito
continuam duráveis; sessão clean é removida. Recibo no mesmo commit evita
segundo Will na repetição do ID. Sessão offline/ausente retorna `not_found`
sem mutação. Esta ação não exclui a sessão persistente.

`audit_list` exige operator e lista até 16 recibos por página. `cursor` é o
índice decimal da primeira entrada; `next_cursor` aponta à próxima página.
Cada item contém instante, request_id, UID, operação, resultado, hash do alvo
e gerações; não contém payload, token, senha ou tópico/client ID do alvo.
O registro é append-only na época corrente do documento MQTT v5 e validado na
reabertura do WAL. A tabela tem 128 entradas; ao encher, o broker recusa novas
mutações comuns, mas permite `audit_rotate` com exportação comprovada.

Para rotacionar, use `xmqr-admin channel audit-rotate --socket CAMINHO
--token-file OPERADOR --archive NOVO_ARQUIVO`. A CLI lê todas as páginas,
grava JSON privado 0600 com `fsync` de arquivo/diretório e envia hash SHA256
e contagem. O ator confere os recibos **atuais**; se houve outra mutação,
retorna `archive_changed` e não limpa nada. No commit, conserva um recibo de
rotação, avança `admin_epoch` e só então permite novos IDs da época seguinte.
O arquivo exportado pode ser conferido com `xmqr-admin audit-verify --file
ARQUIVO`; compare o SHA256 impresso ao `request_sha256` do recibo de rotação.
Um ID antigo não pode executar de novo após a rotação: IDs novos trazem a
época nos oito primeiros hexadecimais; IDs legados da época zero ficam em
índice durável de aposentados. O limite desse índice é 256, com recusa segura
se atingido. Conserve o arquivo exportado e backup offline em local privado.

O documento durável MQTT passa a **v5** no primeiro commit com este binário:
leituras de v1/v2/v3/v4 continuam aceitas, inclusive recibos P107 v3, mas o
broker 0.14.0 não abre v5 (nem v3/v4). Para
rollback, fazer backup offline do estado anterior à primeira escrita v3 e
restaurá-lo em diretório de estado novo com o procedimento de backup/restore;
isso perde alterações posteriores ao backup. Não converter ou apagar o WAL
ativo para forçar downgrade. SIGHUP legado continua disponível, sem recibo
administrativo.

O canal integra status/reload/receipt, inventários paginados, auditoria,
rotação, exclusão retained e desconexão de sessão. O [ADR 0001](adr/0001-admin-channel.md)
define o contrato. O aceite A09 vale para Linux/WSL local, com as limitações
e os ensaios no [aceite da fase 5](phase5-acceptance.md).
