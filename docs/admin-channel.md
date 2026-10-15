# Canal administrativo local — P107 parcial

Com `MQTT_SECURITY_BUNDLE` dinâmico no Linux/WSL, configure antes do startup:

```text
MQTT_ADMIN_SOCKET=/caminho/privado/admin.sock
MQTT_ADMIN_VIEW_TOKEN_FILE=/caminho/privado/view.token
MQTT_ADMIN_OPERATOR_TOKEN_FILE=/caminho/privado/operator.token
```

Os diretórios finais precisam ser reais e modo 0700; os arquivos de token,
regulares, sem symlink, modo 0600 e mesmo UID do diretório/socket, com 64 dígitos
hexadecimais distintos. `xmqr-admin token-init --file NOVO_ARQUIVO` 0.3.0 gera
os arquivos. Não incluir tokens em repositório, URL, argumentos ou logs. O
socket é 0600 e recusa caminho preexistente, configuração parcial ou política
estática. O UID do peer precisa coincidir com o dono do socket.

Cada conexão aceita uma linha JSON v1 de até 16 KiB, com prazo absoluto de 2 s
e no máximo 16 handlers. `request_id` é um ID hexadecimal aleatório de 128 bits.
Tokens `viewer` e `operator` podem consultar `status` e `receipt`; só `operator`
pode executar `reload`.

```json
{"version":1,"request_id":"0123456789abcdef0123456789abcdef","operation":"status","token":"<64 hex>"}
```

`status` retorna `security_generation` da política em memória e `ready` do
probe real do ator/writer. `reload` exige `expected_generation` obtida de
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

`receipt` retorna ID alvo, hash do bundle, UID, operação, resultado
`committed`, timestamp UTC em milissegundos e gerações esperada/aplicada. Não
inclui token ou conteúdo do bundle. Em timeout, desconexão ou
`result_unknown`, consultar o recibo antes de repetir; ausência de resposta
da consulta ainda é resultado desconhecido. A geração de segurança em memória
reinicia após restart; a geração aplicada no recibo é histórica. O ID garante
deduplicação do reload já confirmado mesmo após restart.

O documento durável MQTT passa a **v3** no primeiro commit com este binário:
leituras de v1/v2 continuam aceitas, mas o broker 0.14.0 não abre v3. Para
rollback, fazer backup offline do estado anterior à primeira escrita v3 e
restaurá-lo em diretório de estado novo com o procedimento de backup/restore;
isso perde alterações posteriores ao backup. Não converter ou apagar o WAL
ativo para forçar downgrade. SIGHUP legado continua disponível, sem recibo
administrativo.

A09 permanece parcial: ainda faltam integração da CLI independente, operações
de sessão/retained, consulta/retenção de auditoria ampliada e testes de falha
de armazenamento/concorrência. O [ADR 0001](adr/0001-admin-channel.md)
define o contrato alvo.
