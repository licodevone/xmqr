# P269 v1.1 — preparar a pré-release do Broker 0.44.0

## Entrada

A tag publicada `v0.43.0` aponta para
`db472bc64558bf0e376a902b7780a259247c5149`. O candidato local parte de
`4e7f1ecfedea35cfdf5e604a5d394ec7fbc5376e`, com P265, P267 e P268.
Preservar o histórico diário local e as referências publicadas.

## Objetivo e escopo

Preparar e validar Broker e `mqtt-admin` legado 0.44.0 para distribuição
experimental. Sincronizar os manifestos e lockfiles normal e de serviço
Windows, versão padrão do Dockerfile, changelog e documentação de release.
Vincular o P259 ao candidato sem colocá-lo na matriz publicada antes do
aceite. Os projetos Client/Bridge, Admin independente, Managers e
instalador Oracle preservam seus pins e ciclos de distribuição próprios.

## Compatibilidade

Reutilizar estado v16. O P268 aceita MQTT 3.1.1 e 5 por padrão. Instalações
existentes podem manter a configuração. Ao voltar a 0.43.0, restaurar a
configuração correspondente, sem os seletores `[[listener_protocols]]`.
Validar a atualização e a restauração com cópia privada do estado em
ambiente descartável antes da distribuição.

## Validação e publicação

Conferir versões com Cargo locked, build, fmt, testes, Clippy e inventário.
Executar CI Ubuntu na fonte exata, incluindo o teste TCP/WS do P268 e o
pacote Ubuntu 26.04 amd64. Verificar pacote, serviços e checksums.
Qualificar explicitamente a validação Windows do manifesto de serviço.
Após os gates, criar a tag anotada e imutável `v0.44.0` no commit
validado e publicar a pré-release com notas e artefatos verificados.
Registrar evidências e bloqueios em `prompts/registros/P269-release-0.44.0.md`.

## Revisão 1.1 — ambiente de validação

O inventário local offline foi interrompido antes de comparar o documento
porque o cache não contém `linux-raw-sys 0.4.15`. O acesso ao WSL e ao
Docker está bloqueado neste ambiente. Manter a validação integral prevista
na CI e registrar o escopo dos testes locais.
