# P76 rev1 — compilar snapshots históricos e orientar correções

Entrada: brokerHEADa4f9f86, clientHEAD6c54281. P75 exportou78 snapshots íntegros
(50broker/28client), corte broker629b64b/client6c54281. Broker limpo; client tem
dois arquivos.tar.gz/.sha256 não commitados, preservar. ZIP e SHA em
../docs/curso-udemy/versoes-github. Pedido: verificar quais commits compilam e
quais passos são necessários para os que não compilam.

Ambientes confirmados em2026-10-12: Windows Rust/Cargo1.98.1 MSVC; WSL
Ubuntu-26.04, Rust/Cargo1.99.0. Não mudar toolchain/configuração global,
não instalar ferramentas ou alterar serviços/credenciais/estado reais.

Escopo: criar scripts/verify_commit_builds.py, compilar --locked --bins debug
nos dois ambientes, em cópias isoladas dos78 snapshots do ZIP. Incluir pacotes
didáticos Cargo adicionais quando presentes. Conferir SHA dos arquivos extraídos;
fontes/lockfiles originais intactos antes/depois de cada comando. Target separado
por plataforma e compartilhado apenas entre builds da mesma tarefa para cache.
Pode agrupar trabalho Windows/Linux em dois executores independentes, sem agentes.

Usar cacheoffline primeiro; se faltar crate, tentar resolução locked online
sem alterar lock. Falha de rede/ferramenta é BLOCKED, erro de Rust/linker é FAIL.
Registrar comando, ambiente, saída, log, exitcode, duração e identidade das fontes
por snapshot/pacote. Cada snapshot deve receber compilação real, não PASS por
mensagem Git/registro anterior. Não iniciar binários MQTT ou executar testes/
integrações dos serviços nesta tarefa de compilação. Build não prova execução,
aceite funcional, performance, interoperabilidade ou implementação completa.

Relatórios HTML/CSV/JSON/Markdown com todos os commits, prompts relacionados,
status Windows/Ubuntu, diagnóstico e passos concretos por categoria de erro.
Se falhar, analisar logs e código correspondente para propor correções; manter
snapshots e tags históricos intactos. Não implementar mudanças funcionais sem
novo prompt próprio. Revisar P76 antes de corrigir falhas do verificador.

Incluir relatórios e logs em ZIP de resultados e atualizar uma cópia do ZIP
P75 com COMPILACAO.md por versão e índice de resultados, sem alterar codigo/.
Preservar ZIP P75 original; novo pacote 'todos-os-commits-com-compilacao.zip'.
Artefatos em../docs/curso-udemy/versoes-github/compilacao. Gerador/registro no broker;
commit/push autorizados pela conversa, sem nova versão/tag/release de produto.

Aceite:78 snapshots classificados por ambiente, logs reais e arquivos conferidos;
documentar bloqueios sem inventar PASS. Verificar integridade/links dos relatórios
e ZIP final e registrar resultados reais, incluindo limites Windows/Unix.

## Rev2 — cobertura de todos os alvos sem executar testes

Inventário encontrou além das aulas um pacote validation/c27-bootstrap.
Compilar também esse auxiliar, mantendo seu status separado do pacote principal.
Após build dos binários, rodar cargo check --locked --all-targets em cada
pacote/snapshot e plataforma para conferir tipos do código de testes/exemplos.
Check não gera/executa todos os executáveis de teste; reportar distintamente
build e check, sem anunciar testes funcionais aprovados. Reutilizar somente
cópias e targets isolados desta execução, conferindo hashes novamente.
Registrar ajustes locais do perfil (debug0/incremental0/jobs2) no relatório.

## Rev3 — consistência do pacote leve de evidências

Revisão do gerador antes da entrega: COMPILACAO.md referencia logs em
relatorios-compilacao/; o ZIP leve deve manter essa mesma estrutura, com índice
na raiz apontando ao relatório. Usar scripts/report_commit_builds.py para
agregação; verificar links locais tanto no pacote leve quanto no ZIP completo.
Conferir cobertura121 pacotes por ambiente, em cada fase, sem duplicatas.

## Rev4 — CSV sem duplicação CRLF no Windows

git diff --cached --check detectou CR extra no CSV: csv.DictWriter usa CRLF e
Path.write_text aplicou novamente a conversão Windows, gerando CRCRLF. Nenhum
commit final foi criado. Escrever CSV com lineterminatorLF e newlineLF explícito;
regenerar relatórios/ZIPs e conferir stage novamente. Compilações484PASS não
são afetadas; não repetir builds por erro somente na embalagem documental.
