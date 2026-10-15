# Canal administrativo local — incremento de leitura P107

O canal v1 está **parcial**. Com `MQTT_SECURITY_BUNDLE` dinâmico no Linux/WSL,
configure as três opções antes do startup:

```text
MQTT_ADMIN_SOCKET=/caminho/privado/admin.sock
MQTT_ADMIN_VIEW_TOKEN_FILE=/caminho/privado/view.token
MQTT_ADMIN_OPERATOR_TOKEN_FILE=/caminho/privado/operator.token
```

Os diretórios finais precisam ser reais e modo 0700; os dois arquivos de token
precisam ser regulares, não symlink, modo 0600, mesmo UID do diretório/socket,
com 64 dígitos hexadecimais distintos. Não coloque tokens no repositório,
variáveis de ambiente de valor, URL ou argumentos. O socket é criado modo 0600
e recusará caminho preexistente. Configuração parcial ou política estática
impede startup.

O `xmqr-admin token-init --file CAMINHO_NOVO` da versão 0.3.0 pode gerar cada
arquivo no diretório privado, executado sob o mesmo UID do broker. Use dois
caminhos novos separados, um por papel.

Uma conexão por request, JSON terminado em `\n`, até 16 KiB, timeout absoluto
de 2 s e no máximo 16 handlers simultâneos. O UID do peer deve ser o do
socket. Request de leitura:

```json
{"version":1,"request_id":"0123456789abcdef0123456789abcdef","operation":"status","token":"<64 hex>"}
```

O resultado informa `security_generation` em memória e `ready` do probe real
do ator/writer, além do papel `viewer`/`operator`. O token nunca aparece na
resposta. Nenhuma mutação é aceita neste incremento; `reload` responde
`unsupported_operation`. SIGHUP antigo permanece como antes. A09, auditoria,
deduplicação, sessões/retained e a fase 5 global continuam abertos. O contrato
final previsto está no [ADR 0001](adr/0001-admin-channel.md).
