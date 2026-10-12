# P75 rev1 — reunir versões didáticas anteriores em um ZIP

Entrada: HEAD 629b64b, árvore limpa. P03/P04/P05 estão nos commits
2dbeb84, af64337 e e3e4a23 e têm ZIPs individuais validados por P74.
Pedido: entregar algumas versões anteriores dentro de um único arquivo ZIP.

Escopo: reunir esses três projetos didáticos cumulativos, cada um em uma pasta,
preservando arquivos, comentários, guias, diffs e proveniência dos ZIPs atuais.
Criar scripts/build_previous_versions_bundle.py e registro P75. Destino:
../docs/curso-udemy/serie-didatica/versoes-anteriores-P03-P05.zip.
Incluir LEIA-ME.html, LEIA-ME.txt e manifesto com commits e hashes dos arquivos.
Não confundir etapas didáticas com tags ou releases do broker MQTT completo.
Sem alterar código, versões, serviços, toolchain, snapshots ou repositório client.
Sem nova tag/release; preservar autorização de commit/push da conversa.

Aceite: ZIP único com P03/P04/P05 completas; guia explica extrair, abrir cada
etapa, executar broker/client pelo Cargo no PowerShell e porta loopback 18830.
Validar CRC, caminhos seguros, hashes individuais e fonte contra Git em cada
commit. Recusar links, paths externos, target, executáveis e arquivos privados.
Não repetir testes Rust: código preservado e gates P74 anteriores identificados
como históricos. Revisar este prompt antes de corrigir falha, registrar resultado.

## Rev2 — ampliação solicitada: todos os commits e README por versão

Usuário ampliou o pedido para todos os commits e identificação dos prompts,
com README próprio para cada versão. Substitui o escopo inicial de três etapas.
Após fetch --all --tags: 50 commits no xmqr e 28 no xmqr-client, alcançáveis
pelas referências Git disponíveis (--all). Não recuperar commits apagados nem
inventar passos anteriores ao primeiro commit. Client tem dois anexos locais
não commitados; excluir e preservar. Leitura do client não altera seus arquivos.

Gerador scripts/build_commit_versions_bundle.py: ZIP único de 78 snapshots,
cada um com codigo/ íntegro, README.md adicional, COMMIT.json e ALTERACOES.txt.
Preservar README original em codigo/. Índices HTML/JSON/CSV e checksums globais.
Destino ../docs/curso-udemy/versoes-github/todos-os-commits-broker-client.zip.

Identificação: versão de Cargo.toml, tags exatas, SHA, data, pais, assunto e
arquivos alterados. Prompts: distinguir marco mapeado no índice histórico,
prompt/registro alterado no commit e ID citado na mensagem. Nenhum desses
indícios sozinho demonstra que todas as linhas foram geradas por um prompt.
Incluir cópia dos prompts/registros versionados na referência de corte para
consulta quando ainda não existiam no snapshot. IDs P03/P04/P05 da série nova
não são entregas históricas originais; associar P73/P74 como tarefa da série.
README explica limites de autoria e execução, links para documentos disponíveis
e ausência de associação quando não há evidência. Primeiro broker já era0.3.0.

Validar todos os arquivos de cada snapshot contra blobs Git (inclui modo),
CRC, SHA-256 e caminhos seguros. Rejeitar chaves privadas, links/submódulos e
arquivos sensíveis. Incluir artefatos distribuídos já versionados sem executá-los.
Não executar builds/testes de 78 versões nem declarar compatibilidadeWindows;
broker real tem requisitos Unix/WSL conforme documentação de cada versão.
Registrar o corte do histórico; commit desta embalagem ocorre após esse corte.
Commit/push do gerador, prompt e registro autorizados pela conversa; ZIP fora
do Git, sem nova tag/release. Manifests atuais e código dos produtos intactos.

## Rev3 — pendências por commit e evolução posterior

Pedido adicional: identificar commits anteriores à conclusão de uma feature.
README de cada snapshot deve separar associação de prompt e aceite funcional.
Consultar os registros na versão daquele commit; não tratar notas históricas
preservadas em registro posterior como falha atual. Classificar explicitamente
somente casos com evidência lida: preparação P55/C37, aceite Unix pendente P55
e preparação de fechamento fase1; apontar marcos posteriores P61/C37 aceitos.
Para outros commits: conclusão integral não determinada por esta embalagem,
com links para registros pertinentes. Adicionar PENDENCIAS.md no pacote.
P68 foi somente plano importado: sem registro de implementação completa,
nunca anunciar entrega do capítuloIA por existir o prompt. Classificação aqui
é documental, não nova auditoria funcional/teste de todas as versões.

## Rev4 — preservar blobs sem conversão de fim de linha

Primeira exportação recusada no primeiro snapshot: git archive converteu LF
para CRLF por core.autocrlf=true; hashes dos bytes exportados não eram os blobs
Git. Nenhum ZIP final foi publicado. Ler arquivos por git cat-file --batch,
que retorna os blobs originais, mantendo verificação de SHA do objeto e SHA-256
dos anexos. Não alterar configuração Git global/local nem reescrever fontes.
Reexecutar exportação integral e validar todos os links locais dos READMEs.

## Rev5 — precisão do relatório externo

Conferência final: relatório geral dizia que todos os demais commits tinham
conclusão indeterminada, embora P61 e C37 tenham aceite histórico explícito.
Restringir essa frase aos casos sem classificação de aceite. A cópia externa
de PENDENCIAS.md deve usar links GitHub para registros; dentro do ZIP continuar
com links relativos para leitura offline. Reexportar e verificar integridade.
