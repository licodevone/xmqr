# P275 v1.0 — preparar e publicar o Broker 0.45.0

## Entrada e objetivo

Base `ef5e5da058057db75d5c5a9607f6f25ea0012bac`, candidato 0.44.0
com P274 e teto opt-in de 1.000 conexões e sessões. Por solicitação do
mantenedor, preparar a distribuição 0.45.0 com tag anotada `v0.45.0`
e pré-release experimental. Consulta ao GitHub confirmou que a nova
tag ainda não resolve.

## Escopo e compatibilidade

Alinhar manifestos/lockfiles principal e Windows Service, Dockerfile,
README, VERSIONING, CHANGELOG, notas e prompt P259 de reprodução.
Preservar fonte P274, estado v16, defaults, configuração e dependências.
Os pacotes Broker e `mqtt-admin` legado usam 0.45.0. Client, Bridge,
Admin independente e Managers seguem seus ciclos de distribuição.
Preservar o histórico 0.44.0 e a matriz de versões publicadas.

## Validação e publicação

Verificar metadados locked, versão dos binários e regressões locais.
Congelar o candidato no commit exato e publicar a branch
`release/validation-0.45.0` para acionar a CI Ubuntu. Executar os
gates P269/P273/P274 pertinentes, incluindo TCP/WS, admissão de 1.000
clientes, integração com Client/Admin e pacote Ubuntu 26.04 amd64.
Validar instalação, rollback, checksums e proveniência do pacote.
Registrar a evidência em `prompts/registros/P275-release-0.45.0.md`.

Criar a tag anotada imutável e a pré-release após aceite da fonte e
dos artefatos. Validar os anexos publicados contra seus checksums.
