# P107 rev1 — implementar canal administrativo local A09

2026-10-15. Entrada broker `41326eb`/0.14.0, ADR 0001 decidido, admin
independente 0.3.0 com editor offline. SIGHUP recarrega política mas não
identifica request. A fase 5 global ainda está aberta.

Implementar Unix socket local opt-in apenas para bundle dinâmico. Configurar
caminho/arquivos de token privado no snapshot de startup; autenticar UID do
peer e papel viewer/operator; request/response JSON v1 limitados, deadlines e
admissão limitada. Mutação `reload` usa exclusivamente a fila/ator existentes,
com expected_generation, request_id e deduplicação durável. Auditoria mínima
durável desde a primeira mutação e consulta limitada. Preparar operações de
sessão/retained no mesmo contrato, sem segundo writer nem payloads por padrão.

Negativos: token/papel errados, caminho/symlink/permissão ruim, request grande,
conexão lenta, fila cheia, concorrência, geração obsoleta, request_id repetido
igual/diferente, falha de storage e restart. Não abrir listener remoto nem
relaxar secure-mtls. Gates Rust, integrações Linux/WSL com processos isolados,
revisão de logs/segredos e compatibilidade de estado antes de aceite/release.

Incrementos parciais devem ser registrados como tais; A09 e fase5 só recebem
checkbox após todo contrato e integração com admin independente.

## rev2 — primeira fronteira sem mutação

Antes de expor `reload`, estabelecer bind Unix e operação de leitura `status`
com UID do peer, token viewer/operator, quotas e deadlines. Um incremento só
de leitura é seguro para validar admissão/limpeza do socket, mas permanece
**A09 parcial**. A primeira mutação exigirá recibo durável e auditoria no mesmo
commit; não reaproveitar SIGHUP como atalho de escrita sem request_id.

## rev3 — prova de startup real

Além de unidade com ator/socket, executar broker binário em `acl-lab` com
bundle vazio em diretório temporário privado e consultar o socket real.
Negativos: token errado, mutação não implementada, request grande e política
estática com canal configurado. Confirmar encerramento/remoção do socket e
ausência dos tokens nos logs. Nada em instância instalada do operador.

## rev4 — primeiro reload online com recibo no WAL

Adicionar `reload` somente para token operator, com `expected_generation`,
`bundle_sha256` e `request_id`. O socket consulta recibo existente antes de
reler o arquivo; o ator revalida o ID sob concorrência. Inserir recibo/auditoria
em documento durável no mesmo commit da reconciliação, antes da publicação da
política. Limitar a tabela de recibos e recusar novos IDs ao esgotar a quota,
em vez de esquecer IDs antigos e permitir replay. Bump de formato com leitura
das versões anteriores e rollback documentado. Falhas de candidato/CAS/quota
não alteram política; commit incerto falha fechado. Testar duplicata com
mesmo ID/corpo, conflito com corpo diferente e restart.

## rev5 — recibo auditável e contrato de recuperação

Registrar no recibo instante UTC em milissegundos, UID, operação, resultado,
hash do bundle e gerações antes/depois, sem segredos. Expor consulta por ID para
viewer/operator. Erro de commit no canal significa resultado desconhecido até
consulta do recibo, pois a falha pode ocorrer após `fsync`. Documentar leitura
do estado v1/v2 e escrita v3, com backup anterior para rollback do binário
0.14.0. Registrar A09 parcial até a CLI independente e operações de
sessão/retained serem aceitas.
