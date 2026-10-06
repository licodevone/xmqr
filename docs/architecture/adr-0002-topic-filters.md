# ADR 0002 — filtros MQTT limitados e autorização explícita

Estado: aceito para a série experimental 0.5.

## Contexto

O XMQR 0.4 armazena assinaturas textuais de tópicos exatos. A fatia 0.5 precisa
introduzir `+` e `#` sem permitir wildcard em PUBLISH, ampliar permissões
implicitamente ou alterar a barreira de durabilidade antes de ACKs e fan-out.

## Decisão

- Separar `TopicName` e `TopicFilter` em tipos com construção e desserialização
  validadas; manter serialização textual e formato de estado 1.
- Matcher iterativo, sem recursão, alocação ou backtracking. Preservar níveis
  vazios, Unicode e maiúsculas/minúsculas; seguir a exclusão da raiz `$`.
- Examinar no máximo 64 sessões × 256 filtros, cada um com até 256 bytes.
  Um índice trie fica adiado até existir evidência de gargalo.
- Produzir uma entrega por cliente no maior QoS concedido aplicável, limitado
  pelo QoS da publicação. Deduplicar retained entre filtros do mesmo SUBSCRIBE.
- Exigir a presença literal do filtro solicitado em `subscribe` da ACL.
  Manter `publish` exato; revalidar tópicos concretos na entrega e no restore.
- Remover apenas o filtro idêntico no UNSUBSCRIBE. Nenhum I/O de disco ocorre
  no matcher; o ator continua dono do estado e confirma o commit antes de expô-lo.

## Alternativas e consequências

Inferir autorização por inclusão de filtros exige uma nova linguagem de ACL
e aumenta o risco de privilégio ampliado; não faz parte desta fatia. A busca
linear tem custo limitado, mas não sustenta uma promessa de alta escala.
Os limites existentes são fixos; configuração versionada é uma etapa posterior.

A 0.5 lê o estado anterior. A 0.4 não pode restaurar filtros wildcard:
remova-os antes de retornar ou restaure um backup anterior completo.

## Evidências

Vetores OASIS, propriedades geradas com referência independente, níveis vazios,
Unicode, profundidade máxima, quotas, ACL, recuperação, retained e clientes
Mosquitto. Consulte [matriz MQTT](../conformance/mqtt311-status.md) e
[roteiro](../wildcard-subscriptions.md). Last Will continua fora desta fatia.
