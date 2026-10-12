# P76 — compilação real dos78 snapshots históricos

2026-10-12. PromptP76 rev1 antes do verificador; rev2 ampliou a conferência
para check de todos os alvos e pacote auxiliar; rev3 alinhou links/estrutura
do ZIP leve. Nenhuma fonte histórica, manifest ou lockfile corrigido/alterado.

## Entrada e execução

BrokerHEADa4f9f86, clientHEAD6c54281. ZIPP75 SHA-256:
f83e93a2988f88dcc2ab68b4d3520b10aa8235192ee354bed3f1108211ead3d5.
78 snapshots (50broker/28client), corte629b64b/6c54281; não inclui os commits
posteriores de embalagem/verificação. Todos os Cargo.toml presentes conferidos:
78 pacotes principais,18 ocorrências de pacotes didáticos e25 do auxiliarC27.

Execução p76-20261012-01, fontes extraídas e conferidas com SHA-256 antes/depois
de cada comando. WindowsRust/Cargo1.98.1 hostx86_64-pc-windows-msvc; WSL
Ubuntu26.04/RustCargo1.99.0 hostx86_64-unknown-linux-gnu. PythonWindows3.13 e
WSL3.14.4. Target e cópias isolados, jobs2/devdebug0/incremental0; nenhuma
configuração global alterada. Cache offline disponível em todos os comandos.
Windows/Linux executados independentemente, sem subagentes.

Comandos por pacote:

```text
cargo build --locked --offline --bins --jobs 2
cargo check --locked --offline --all-targets --jobs 2
```

Build gerou binários; check conferiu biblioteca, testes, exemplos e benchmarks
existentes sem codegen/link final de todos esses alvos. Features padrão apenas.
Não executar programas MQTT/testes/serviços é escopo explícito desta verificação.

## Resultados reais

| Ambiente | Build dos121 pacotes | Check dos121 pacotes | Falhas/bloqueios |
| --- | --- | --- | --- |
| WindowsMSVC/Rust1.98.1 |121PASS/exit0|121PASS/exit0|0|
| Ubuntu26WSL/Rust1.99.0 |121PASS/exit0|121PASS/exit0|0|

484 comandos aprovados,121 em cada uma das quatro combinações. Os programas
principais dos78 commits compilam em ambos os ambientes. Extras classificados
como didático/auxiliar sem misturar seu status com o produto principal.
125 comandos emitiram avisos; imports/constantes não usados em versões antigas
Windows, entre outros diagnósticos, estão nos logs. Aviso não foi classificado
como erro de compilação. Ajuste opcional documentado em branch nova e com
cfg(unix) quando apropriado; não afrouxar garantias de durabilidade/permissão.
Nenhum build exigiu tentativa online ou alteração de lock.

Revisão de stage detectou CRCRLF no CSV gerado por tradução dupla Windows;
P76rev4 revisado antes da correção. Gerador passou a gravar LF explicitamente,
relatórios/ZIPs reexportados e stage conferido novamente. Não foi falha dos
snapshots compilados; nenhum build repetido por essa correção documental.

Conclusão: nenhum erro de compilação requer correção nos ambientes/alvos
verificados. Os cinco commits intermediários P75 também compilam: pendência
de implementação/aceite não implica erro de construção do programa.

## Evidências e entrega

Artefatos locais:

- ../docs/curso-udemy/versoes-github/compilacao/p76-20261012-01/
  Windows/Ubuntu JSON, logs por comando, resumo, resultadosCSV/JSON, RELATORIO.md
  e indexHTML pesquisável por commit/prompt/versão.
- resultados-compilacao.zip: pacote leve de relatórios/logs e COMPILACAO.md
  por versão, com índice na raiz.
- ../docs/curso-udemy/versoes-github/todos-os-commits-com-compilacao.zip:
  todas as fontesP75 preservadas,78 COMPILACAO.md, relatórios e checksums.
  AbrirCOMPILACAO.html após extrair. ZIPP75 original preservado.
- docs/results/p76-compile-summary.json e p76-compile-matrix.csv:
  resumo/matriz versionados para consulta no GitHub.

Gerador exige cobertura dos121 pacotes em cada fase/plataforma, unicidade,
execução finalizada, inputZIP idêntico, logs existentes e PASS coerente com
exit0. CRC dos dois ZIPs finais, SHA-256 de conteúdo completo e links locais
de78 COMPILACAO.md/índice verificadosPASS. Bytes do ZIPP75 mantidos, incluindo
READMEs e prompts originais. ZIPs excluem targets/binários gerados/caches.

UI emEdge headless:78 linhas, pesquisa por10e1b59 (1 resultado), consulta sem
resultado (0), restauração (78), campo de busca em390px e nenhum erroJS:PASS.
git diff --checkPASS. Código/versões dos produtos intactos; anexos não commitados
do client preservados. Nenhum serviço real, credencial ou estado tocado.

## Limites e reprodução

Não executados testes,fmt/Clippy dos78 snapshots ou integrações MQTT; não feita
matriz release/all-features/MSRV1.88, Ubuntu24, arm64 ou outras distribuições.
Compilar Windows não homologa operações de persistência/administração Unix.
Aceite funcional P55/C37 e demais recursos permanece documentado nos registros
da época, com marcos posteriores de fechamento. Não anunciar MQTT5/WebSockets
ou produção por build aprovado.

Para repetir, executar scripts/verify_commit_builds.py com novo --run-id no
Windows e Ubuntu26; depois --phase check com o mesmo ID em ambos. Agregar com
scripts/report_commit_builds.py --run-id ID. Logs brutos ficam fora do Git;
resumo/matriz/geradores/prompt/registro podem ser commitados e enviados conforme
autorização persistente. Sem nova versão/tag/release de produto.
