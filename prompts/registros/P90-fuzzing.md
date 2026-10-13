# P90 — B07: fuzzing mutacional limitado, aceite local

Prompt [P90 v1.3](../broker/90-fuzzing-limitado.md), subordinado a P89.
Pedido autorizado: finalizar fase3, com agentes paralelos e prompts antes
de código. Execução2026-10-13, Ubuntu26.04/WSL, Rust1.99/Python3.14,
mesma árvore Windows em acmebr-projects/acmebr-broker-client/xmqr.
Base main d467bf3f7f654be6aa133cefe4ad07ff0e6818fb/runtime0.11.5;
release preparada pelo coordenador0.11.6 e P93 concorrente preservados.

## Escopo e revisão

Novos arquivos `src/mqtt/fuzz_tests.rs`, `tests/fuzz-corpus/codec.hex` e
`topics.txt`, `scripts/run_fuzz.py`, dois fixtures/testes Python de watchdog,
`docs/fuzzing.md` e prompt/registro. codec.rs tem declaração cfg(test,unix)
do módulo somente; nenhuma API runtime, quota, dependência ou formato foi
alterado pelo P90. P93 tem alterações runtime separadas do coordenador.
MIT própria e avisos existentes preservados. Nenhuma credencial ou instância
do operador, firmware, serviço, firewall ou diretório de estado real usado.

Revisão P93 somente leitura: nomeMQTT antes de erro tipado de nível; known
level4 malformado fecha sem CONNACK; IDs recusados antes de auth/registro;
pipeline não gera commits; TLS permanece antes do handler e write limitado.
P92 avisos/Docker/deb inspecionados: escopo de metadata locked, textos
originais recursivos, hash e falha fechada; sem achado demonstrado no recorte.

## Falhas reais e correções do harness

- Primeiro compile FAIL: padrão &&str, variante AckKind inexistente e import
  unused. P90v1.1 preparado antes do ajuste; corrigidos apenas testes.
- Primeiro driver FAIL apesar de Rust frame25000/seed151195649 PASS: libtest
  põe marcador JSON na mesma linha do nome do teste. P90v1.2 preparado antes
  do parser corrigido; aceita exatamente um relatório de alvo/seed/count.
- Self-test inicial do watchdog:2 de4 FAIL por deadline1s de startup/RSS
  durante builds concorrentes. v1.2 aumenta só fixtures normal/RSS para5s,
  preserva hang deadline1s e campanha real120s/512MiB;4/4 depois PASS.
- Campanha intermediária18/18 PASS; Clippy FAIL por máscaras/if/function
  length do harness. v1.3 preparado antes dos ajustes e da precisão dos
  contadores/SHA-fonte. Sem regressão/runtimefix descoberto pelo fuzzing.

## Campanha final realmente executada

Comando (saída0):

```sh
python3 scripts/run_fuzz.py --iterations 25000 --state-iterations 128 --router-iterations 256 --output dist/fuzz/p90-final.json
```

Seeds151195649/305419896/11400714819323198485, seis alvos por seed,
18 execuções PASS com sources unchanged=true. Watchdog real por grupo
próprio:120s/RSS512MiB, amostragem20ms; input≤65536 e sem instalaçãoglobal.
Duração driver8.3600s incluindo coleta da evidência; tempos abaixo são soma
de subprocessos por alvo, não capacidade de produção nem benchmark.

| Alvo | Casos nos3seeds | Aceitos pelo oráculo indicado | Maior input observado | Soma segundos | Maior RSS amostrado bytes |
| --- | ---: | ---: | ---: | ---: | ---: |
| Framing/RL | 75000 | 63145 cabeçalhos completos | 65536 | 0.4466 | 6979584 |
| Decoder/UTF-8/flags | 75000 | 7356 corpos | 65536 | 0.5171 | 7372800 |
| Fragmentação/concatenação | 75000 | 2170 streams completos | 429 | 0.6480 | 7335936 |
| Tipos/matcher de tópicos | 75000 | 13857 pares válidos | 2047 | 0.4519 | 7008256 |
| TOML/restore | 384 | 30 documentos | 1439 | 0.8658 | 9650176 |
| Router retained/offline | 768 | 709 transições | 31 payload | 1.2231 | 10059776 |

Total300000 casos rápidos,384 documentos restaurados mais384 candidatos
semânticos verificados,768 transições/59 recusas/48 epochs do modelo com
shutdown/reopen/drain. Zero panic/divergência de oráculo/timeout/RSS-limit
na campanha real. O self-test que excede RSS é fixture deliberada, não broker.
JSON contém SHA das fontes/manifest/lock/driver/corpus; escrita/edição desses
inputs durante compile/campanha impede PASS.

Evidência local ignorada `dist/fuzz/p90-final.json`:
SHA256 `0add91f83e8e03d32fc75c34b4f99564682545e4b26725463060e8d93aacb32e`.
Executável libtest:
SHA256 `0fe5062b49b93a902a133fd6abe3ea125bfb9dc56ac15046dde061a3e59dd4a6`.
Corpus codec SHA256 `774c4c7e56b003df0455e947bd0acde6978f89d30291daad5236ffaf285ddd8f`;
topics SHA256 `9161787ef8eb3059031d842d89d476d229170147fffc6c9ab7b9222445eeb2cb`.
Arquivo ignored não é prova pública por si; conservar/publicar JSON com os
artefatos do marco e reexecutar no commit exato sob P92.

## Outros gates realmente executados

- `cargo test --locked --lib deterministic_fuzz -- --nocapture`:0,2/2
  smoke PASS no harness final. Campanhas6 estão ignored no teste normal.
- `cargo fmt --all -- --check`:0.
- `cargo clippy --locked --all-targets -- -D warnings`:0 (2.77s final).
- `python3 -m unittest discover -s tests -p fuzz_watchdog_test.py`:0,4/4
  PASS em1.383s final. Fixture normal exit0; hang kill≈1.02s; RSS kill
  com68.7MB observados/acima32MiB; falha exit19 não é PASS.
- `python3 -m py_compile scripts/run_fuzz.py tests/fuzz_watchdog_test.py tests/fuzz_watchdog_fixture.py`:0.
- `git diff --check`:0, warnings históricos de conversão LF/CRLF sem alteração
  adicional desses arquivos pelo agente. Gates completos129Rust/release
  são responsabilidade de P92/coordenador e não inferidos por estes2smokes.

## Aceite e limites

B07 aceito localmente no recorte mutacional descrito, fontes finais estáveis;
integração de release/commit exato/publicação ainda P92, sem commit/push/tag
feito pelo agente. Rastreabilidade OASIS no prompt/guia; parser TOML da mesma
dependência e semântica de referência independente, não parser duplicado.
Framer fragmentado exercitado em memória; deadlines de rede reais são P91.
WAL recebe documento mutado com CRC válido; corrupção binária WAL pertence
a B06/P86, não inventar fuzzing de CRC. Modelo router cobre open-lab/QoS1,
retained/quota/offline; QoS2/TLS/ACL são gates separados. RSS amostrado não
é instrumentação instantânea. LibFuzzer/ASAN/cobertura-guided/nightly não
executados/instalados; ausência não é PASS. Sem exaustividade/conformidade
integral/produção/SLA/energia/Windows/arm64/MSRV1.88 exato inferidos.
Fase3 inteira não é concluída só pelo B07; B06+B08+C07 precisam de aceite real.

## Complemento QA de distribuição P92 — posterior ao freeze B07

P90v1.4/v1.5 foram preparados antes de criar/ajustar apenas
`scripts/verify_phase3_notices.py` e `scripts/test_phase3_notices.py` por
delegação do coordenadorP92. Não alteram as fontes da campanha B07 aceita.
TAR lido em memória, sem extract; containers novos somente create/cp/rm,
sem iniciar serviço e sem volumes/rede do operador. Esperado é coleta de
fonte locked externa ao pacote: conferir bytes/paths/SHA, MIT e copyright.

Diferença real MIT própria informada pelo coordenador: CRLF na cópia Windows
SHAacfd4bb82db195b2ba0a8a1ea6c5048d2e66c05a0fd0bd843e08d8a46d34b465;
LF Gitblob/clone SHA84381e555814f7125a9db5bce4f79b786cfb795b05eaddc2ef31a3a414842fc9.
Comparação aceita apenas CRLF→LF, reportando SHA raw por artefato e canônico;
termos/copyright diferentes são FAIL. Terceiros permanecem byteSTRICT,
inclusive EOL. Não é relicenciamento nem parecer jurídico completo.

9 testes iniciais Linux PASS; após ajuste EOL, nova chamada WSL não iniciou:
Wsl/Service/0x8007274c, exit1 externo, nenhuma falha de código inferida.
Sem reiniciar WSL/Docker/serviços. Fallback proporcional autorizado para
unitários puros: Python3.13 Windows existente,12/12 PASS em0.014s e
py_compile0. Fixtures cobrem MIT CRLF, termos alterados, terceiro EOL alterado,
texto adulterado/ausente/extra, manifesto trocado, copyright ausente,
TAR symlink/traversal/duplicado e regular in-memory.

Gate real deb+imagens: aguardando artefatos P92, NOT_RUN neste complemento.
Não marcar distribuição concluída por unitários. Resultados reais serão
registrados pelo coordenador/agente após recebê-los, sem publicar antes.

P90v1.6 precedeu reforço de limites agregados no leitor TAR do QA:64MiB de
conteúdo de notices e20000 membros; sem mudar quotas do broker. Dois mocks
negativos adicionais passam junto dos anteriores:14/14 WindowsPython3.13
PASS em0.019s, py_compile0. Gate real ainda aguarda artefatos/coordenador.
