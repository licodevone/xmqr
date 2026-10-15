# ADR 0001 — canal administrativo local

Status: decidido para a fase 5, 2026-10-15. Escopo: Linux/WSL. A implementação
e o aceite A09 são separados desta decisão.

## Decisão

Usar Unix domain socket de stream em diretório privado pertencente ao UID do
broker, com nome configurado antes do startup. O broker cria o socket com
permissão 0600 e recusa caminho preexistente, symlink ou diretório gravável por
grupo/outros. O admin independente fala um protocolo JSON por linha, versão 1,
limitado a 16 KiB por request/response, com deadline absoluto e 16 conexões
simultâneas. O socket não tem listener TCP nem atravessa a fronteira TLS MQTT.

Autenticação combina UID do peer obtido pelo kernel (`SO_PEERCRED`) com bearer
em arquivo privado 0600. Dois arquivos de token independentes conferem papéis
`viewer` e `operator`; `operator` inclui leitura e mutação. O broker lê tokens
somente no startup/rotação administrativa explícita; comparação em tempo
constante, sem conteúdo em logs. O token do painel atual não é reutilizado.
Operações desconhecidas, versão inválida e papel insuficiente falham fechados.

O contrato v1 inclui `request_id` aleatório de 128 bits, `operation`, parâmetros
tipados e `expected_generation` para mutações de política. O broker valida
formato/quotas antes de enfileirar. A admissão usa fila limitada e `try_send`;
`busy` não altera estado. Cada mutação entra no ator MQTT existente, que é o
único writer de WAL. Resposta de sucesso contém geração/revisão após commit;
`rejected` confirma nenhuma mutação; timeout/desconexão significa resultado
**desconhecido** e exige consulta por `request_id` antes de repetir. O ator
mantém deduplicação durável e limitada, com mesmo ID + corpo idêntico retornando
o resultado anterior e mesmo ID + corpo diferente rejeitado. Se a tabela de
deduplicação não puder ser consultada/reconstruída após restart, não executar
repetição automaticamente. Operações de leitura têm paginação e budget.

Auditoria mínima nasce junto com a primeira mutação: timestamp, request_id,
ator local (UID e papel), operação, alvo resumido ou hash, revisão, resultado e
motivo de enum fechado. Sem payload, senha, hash Argon2, token, tópico privado
completo ou conteúdo do bundle. Registros têm rotação/retenção configurada,
acesso do operador e semântica explícita para falha de escrita. Falha de audit
antes de mutação recusa a mutação; resultado incerto após commit é registrado
na recuperação. O canal não promove validação offline a aplicação online.

## Alternativas e consequências

HTTPS remoto exigiria outra fronteira TLS, certificados e exposição de rede
antes de existir necessidade remota. Tópico MQTT reservado misturaria controle
e dados, complicaria ACL, loops, QoS e ownership durável. SIGHUP é preservado
como mecanismo legado local de reload, porém não responde a cada operação nem
oferece RBAC/idempotência. O Unix socket limita a primeira implementação ao
mesmo host e requer caminho privado e limpeza apenas do inode criado pelo
processo. Windows nativo precisa de ADR próprio.

## Testes para A09

Provar peer/token/papel incorretos, socket e parent inseguros, request grande,
conexões lentas, fila cheia, concorrência, corrida de geração, ID duplicado
com corpo igual/diferente, crash antes/depois de commit, reabertura do WAL e
falha de auditoria. Comprovar que reload e operações de sessão/retained usam o
ator, que uma identidade revogada não reconecta e que QoS2 aceito antes da
revogação permanece durável. Revisar logs para ausência de segredos.
