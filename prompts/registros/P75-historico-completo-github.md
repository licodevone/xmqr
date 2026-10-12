# P75 — histórico completo com README e prompts por versão

2026-10-12. Prompt75 rev1 preparado antes da embalagem; rev2 ampliou o pedido
para todos os commits, rev3 incorporou análise documental de pendências.
Rev4 corrigiu exportação Git/CRLF; rev5 corrigiu precisão do relatório externo.

## Corte verificado

Fetch --all --tags dos dois repositórios concluído. Foram exportados todos os
commits alcançáveis por referências Git disponíveis (--all), não reflog ou
objetos apagados/inacessíveis:

- xmqr: 50 commits; HEAD629b64b4f654d5e3bd1215b0912787a5e7a2a51d.
- xmqr-client: 28 commits; HEAD6c542814c0199393b1629a4a3b3ac79d9797b43d.

ZIP final local em ../docs/curso-udemy/versoes-github/
todos-os-commits-broker-client.zip, aproximadamente96.7MiB. Arquivo.sha256
acompanha o pacote. ZIP fora do Git; gerador e evidências versionados no broker.
O commit desta embalagem é posterior ao corte e não se inclui recursivamente.

## Entrega

78 pastas identificadas por projeto/ordem/SHA, cada uma com codigo/ íntegro,
README adicional, COMMIT.json (versão, tags exatas, pais, data, assunto,
associações de prompt, modos e SHA-256) e resumo ALTERACOES.txt. README original
preservado em codigo/. Índices HTML/CSV/JSON, SHA256SUMS.txt e PENDENCIAS.md.
Prompts/registros versionados do corte copiados em documentos/ para consulta.

Associações distinguem marco mapeado no índice do curso, documento alterado e
ID citado na mensagem. Não provam autoria exclusiva. Nove commits não têm
associação identificável; nenhum prompt inventado. P73/P74 são responsáveis
pela série didática nova P03/P04/P05, não pelas saídas históricas originais.

Cinco commits intermediários conferidos lendo o registro naquela versão:
b577dd0 preparaçãoP55; 10e1b59/d76c9e9/49edfc2 aceite Unix/fase1 pendente;
5d1f742 preparaçãoC37. P61d7b9d41 registra aceite agregado Ubuntu26/WSL;
C37 6ee5aa8 registra aceite portátil, com Ubuntu/fase1 ainda pendentes naquele
marco. P68 é plano importado, sem comprovação de implementação integral.
Nos demais casos sem classificação explícita, conclusão não determinada por
esta embalagem; não tratar ausência de marcação como feature concluída.

## Validação real

PASS exportação final: 78 commits,13297 arquivos incluindo materiais/indexação.
Todos os arquivos fonte comparados com SHA do blob Git, preservando bytes;
SHA-256 de todos os arquivos ZIP verificado após gravação; CRC ZIP completoPASS.
Verificados caminhos, ausência de links/submódulos/chaves privadas, igualdade
dos arquivos do snapshot com ls-tree. Links locais de78 READMEs e índiceHTML
verificados dentro do ZIP. Cópia externa de pendências usa links GitHub.
git diff --check PASS. Código dos produtos/manifests/snapshots intactos.

Primeira tentativa falhou: git archive converteu LF emCRLF devido à configuração
core.autocrlf=true. Validação recusou antes de entregar ZIP final. Após rev4,
cat-file --batch forneceu os blobs crus, sem alterar configuração Git. Exportação
integral repetida com sucesso. Revisão final rev5 corrigiu frase geral do relatório
e links da cópia externa; ZIP final reexportado e validado.

Não executados builds/testes das78 versões; esta tarefa prova fidelidade e
integridade da exportação, não homologação Windows ou conclusão de todas as
features. Registros históricos não equivalem a novos testes. Nada instalado,
nenhum serviço/credencial alterado. Os dois anexos não commitados do client
foram preservados e excluídos do histórico exportado.

Commit/push do gerador/prompt/registro autorizados na conversa. Sem nova versão,
tag ou release de produto nesta embalagem documental.
