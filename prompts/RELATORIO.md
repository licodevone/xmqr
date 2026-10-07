# Resultado da organização documental — 2026-10-07

P-DOC-01 preparado antes da cópia/adaptação. Projeto alvo: D:\projects\my-project\xmqr.
Git status inicial limpo, verificado por leitura com o usuário proprietário;
nenhum safe.directory global foi alterado. prompts/ não existia.

Importação: 31 prompts broker e 5 clients, com cópias originais byte a byte e
manifesto SHA-256. Dois catálogos gerais da origem preservados somente como contexto.
As 36 cópias de trabalho receberam status/proveniência e remoção de dependências
obrigatórias de agentes/skills/comandos inexistentes. Contexto, orquestrador e
template de feature foram reescritos para XMQR. Gates 0.2.0 preservados como
históricos; P36 é a validação do snapshot atual. Sequência corrigida: wildcard
já implementado não depende de implementar Will. Versionamento respeita
CONTRIBUTING e não promove versão automaticamente em PR comum.

Novos: P34 perfis/estado; P35 CRUD; P36 validação atual; P37 limite broker/CLI;
P38 Client ID/deadlines; P39 persistência/resiliência; P40 licenças/CI/release;
C24 CLI atual/credenciais. Índice, contrato, cobertura e template de registro criados.

Validação documental registrada em VALIDACAO.json: hashes da origem e cópias,
links locais das cópias ativas, referências de evidência e escopo do destino.
Catálogos arquivados da origem podem citar trilhas que deliberadamente não foram
importadas; não são documentos ativos. Os originais não foram atualizados nem executados.

Nenhuma instalação, build, teste Rust, execução de serviço, commit, publicação,
mudança de código, manifest, configuração ou CI realizada. Estes arquivos
documentam cobertura e propostas, não entregam novas funcionalidades.

Cobertura incerta: interop TLS/ACL ampla, fuzzing, benchmarks, falhas reais de
energia, operação/produção, execução Windows e comprovação histórica dos prompts.
Inconsistências fora do escopo registradas em COBERTURA.md, sem alterá-las.
