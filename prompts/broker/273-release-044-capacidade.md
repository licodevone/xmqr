# P273 v1.0 — congelar candidato 0.44.0 com capacidade de 500 conexões

## Entrada e objetivo

Broker candidato no commit `02097af27efe601ada936dc964d82936e6771e5a`.
P270–P272 acrescentam medição, quota opt-in de 500 conexões e sessões,
e ensaio de interoperabilidade com Client e Admin. A consulta remota
da tag `v0.44.0` retornou ausência. Preparar a pré-release autorizada
no escopo do Broker e do admin legado incluído no mesmo pacote.

## Escopo e compatibilidade

Versionar as alterações do Broker, scripts e evidências P270–P272.
Atualizar `CHANGELOG.md`, `VERSIONING.md` e `docs/releases/0.44.0.md`.
Preservar manifestos 0.44.0, tags publicadas, trabalho de outros
repositórios e histórico diário local. Client, Admin independente e
Managers mantêm seus ciclos próprios.

Estado persistente v16, padrão de 64 e configuração anterior compatível.
Ao retornar a um binário com teto de 64 sessões, usar configuração
compatível e, se necessário, restaurar backup com até 64 sessões
em diretório separado com o serviço parado.

## Validação e publicação

Conferir formatação, configuração/versão, sessão durável e scripts.
Congelar a fonte em commit e usar branch `release/validation-0.44.0`
para a CI Ubuntu. A fonte exata deve passar os gates do P269 e os
testes TCP/WS do P268 e de admissão do P271. Executar o P272 em
Ubuntu antes de declarar compatibilidade integrada em 500 conexões.
Capacidade sustentada e rajadas mTLS exigem resultados de carga próprios.

Após aceite da fonte e do pacote, criar tag anotada e imutável
`v0.44.0`, publicar pré-release com artefatos e checksums verificados
e registrar evidências em `prompts/registros/P273-release-044-capacidade.md`.
