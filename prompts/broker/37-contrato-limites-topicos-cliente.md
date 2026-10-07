> Atualização: decisão autorizada e executada por [P41](41-topicos-filtros-1024.md).
> O texto abaixo preserva a análise de entrada; o contrato atual é 1024 bytes UTF-8
> no broker e CLI. Evidência em [registro](../registros/P41-topicos-1024.md).

# P37 — Reconciliar os limites de tópico/filtro entre broker e CLI

Tipo: correção proposta, não implementada. Inspeção: src/mqtt/topic.rs aceita
256 bytes; src/bin/mqtt-client/cli.rs aceita 1024. CHANGELOG e documentação do
broker descrevem 256. Não alterar limites só porque existe este prompt.

## Prompt de trabalho

Prepare decisão explícita: manter limite do broker e alinhar a CLI/documentação,
ou ampliar o broker sob novo orçamento comprovado. Confirme os requisitos do
consumidor sem importar seu código ou aumentar capacidade por presunção.
Compartilhe contrato onde apropriado, diferenciando limite local e máximo do
protocolo. Conte bytes UTF-8, não caracteres; evite normalização.
Mapeie decoder, tipos, ACL, restore, documento persistido, matcher, memória e
fan-out. Se aumentar o limite, defina migração e rollback para cópia anterior que
não lê nomes longos. Preserve versões existentes até pedido de release próprio.

## Aceite futuro

Testar fronteiras 255/256/257 e 1023/1024/1025 bytes, Unicode multibyte,
PUBLISH vs SUBSCRIBE, filtros, ACL, retained, offline, restart e rejeição antes
de alocação. Registrar decisão, comportamento CLI/broker e impacto de capacidade.
Qualquer mudança funcional depende de pedido específico; nenhuma foi feita aqui.
