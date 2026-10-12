# P65 — guia de construção desde o início

Data: 2026-10-12. Entrada broker725251b/0.11.2 e client8bb7aaf/0.7.1.
Prompt P65 preparado antes das alterações; rev2 corrige histórico/quotas,
rev3 corrige PATH do verificador e rev4 corrige largura mobile.
Escopo exclusivamente documental e geradores de documentação.

## Entrega

Curso HTML autossuficiente: WSL/Ubuntu e Rust; Cargo e Hello; servidor/client
TCP com explicação humana de cada linha; caracteres contextualizados;
comandos; dependências diretas e features dos dois manifests; módulos;
fatias MQTT 3.1.1, durabilidade, segurança, operação e distribuição.
Inclui referência por tags e percurso de implementação com critérios de aceite.
Não apresenta eco TCP como MQTT nem promete broker novo completo apenas pelos
exercícios iniciais. Fontes completas atuais têm notas assistidas separadas da
análise humana. Gerador versionado usa raiz relativa, manifests e contagens.
Scripts: build_code_guide.py, guide_tutorial.py e guide_line_notes.py.
README aponta para curso e explica regeneração com Python3.11+.

## Validação

PASS: geração85 prompts/27 fontes/12492 linhas (10335broker e2157client),
igualdade de todas as linhas extraídas, numeração e notas não vazias;
IDs únicos e destinos internos existentes.
PASS: Hello e dois projetos Cargo compilados offline com Rust1.99.0 noUbuntu26
em diretório temporário; execução TCP real client→servidor→Resposta:ping.
PASS: Edge headless1440x1000 e390x844; busca, recolhimento, sem erroJS e sem
overflow horizontal após correção. Capturas inspecionadas na pasta temporária.
Primeiras tentativas: verificador diretoWSL sem Cargo noPATH, corrigido com
Bash de login; render mobile excedia largura, corrigido por quebra contextual
e contenção de tabelas. Patch textual inicial recusado sem alterações por
contexto divergente. Prompts revistos antes das correções.
PASS: git diff --check. Nenhum segredo/arquivo de estado/anexoDocker adicionado.
Sem gate funcional do broker/client reivindicado nesta documentação.
Sem alteração de versão, protocolo, configuração real ou serviços.
Arquivos Dockerarchive/hash preexistentes preservados/excluídos.
Commit/push autorizados; sem tag/release documental.
