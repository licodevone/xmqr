# P90 v1.6 — B07: campanha de fuzzing mutacional limitada

Preparado em 2026-10-13 antes do código, dentro de P89/finalização da fase 3.
Entrada: broker main d467bf3f7f654be6aa133cefe4ad07ff0e6818fb, runtime
0.11.5; somente P89 preparado e trabalhos paralelos autorizados preservados.

## Objetivo e ownership

Executar mutações reais reproduzíveis em framing/codec/UTF-8, filtros e
documentos persistentes; comparar com referências independentes e um modelo
de transições retained/offline/restore. Corpus sintético pequeno versionado,
sem dados do operador. Arquivos: `src/mqtt/fuzz_tests.rs`, declaração somente
cfg(test, unix) em codec.rs, `tests/fuzz-corpus/`, `scripts/run_fuzz.py`,
`docs/fuzzing.md`, registro P90. Sem versão, commit ou publicação pelo agente.
Não ampliar API pública, dependências, quotas ou formatos para permitir testes.
Correções runtime exigem falha minimizada, regressão e revisão deste prompt
antes do fix, com coordenação do proprietário do runtime.

## Método e invariantes

- PRNG determinístico sem dependências novas, seeds declarados e mutações de
  bit/byte, inserção, remoção, truncamento, splicing e preenchimento de limites.
  Entradas nunca excedem 65536 bytes; documentos/candidatos pequenos e bounded.
- Framing: referência com bit weights e classificação de prefixo incompleto,
  pacote demasiado e Remaining Length inválido. Decoder: gramática separada,
  regras de fixed header/IDs/UTF-8/Will/Subscribe; encoder próprio não é oráculo.
- Fragmentação/concatenação exercita FrameReader real sem rede do operador.
  Filtro: validador e referência recursiva por níveis, $, vazios, unicode e
  ausência de normalização; recursão limitada pelo input do harness.
- Estado: mutar candidatos e TOML sintético, comparar validação semântica
  independente, abrir WAL de fixture com writer único e verificar restore
  fechado contra documentos inválidos. Modelo retained/offline compara valores
  e ordem após commit/shutdown/reopen; quotas e candidato recusado sem efeito.
- Testes curtos determinísticos entram no cargo test normal; campanhas largas
  cfg(test)/ignored executadas explicitamente. Reportar contagens reais,
  seed, duração, ambiente, máximo RSS e timeout. Watchdog subprocess Linux,
  teto 512 MiB RSS por processo/grupo e 120s por alvo; matar só grupo próprio.
- Falha: salvar seed/índice/input sintético em diretório ignored dist/fuzz,
  reduzir a reprodução quando possível e não ocultar regressão/corpus.

## Normas, compatibilidade e segurança

OASIS MQTT3.1.1+Errata01 §§1.5.3, 2.2/2.3, 3.1/3.3/3.8/3.10/3.12/3.14,
4.7 confirmada em fonte oficial; teto local pacote65536/topic1024/payload4096,
quotas existentes e política local de unicode explícitas. ClientID vazio é
checagem separada do coordenador, não mudar política de sessão neste harness.
TLS/SAN, auth/ACL deny-by-default, ownership/generation, commit antes de ACK,
perfil e formato durável preservados. FS privado temporário Linux, nenhum
serviço real/secret/firewall/ESP32/instalação global.

## Aceite e limites

fmt/test --locked/clippy all-targets -D warnings/build --bins; pelo menos
dezenas de milhares de mutações reais em três seeds e restaurações limitadas,
resultado e duração em JSON ignorado e registro verificável versionado.
Falha/timeout/oráculo divergente impede B07 aceito. Ruststable disponível;
cargo-fuzz/nightly ausentes: não instalar e não declarar LibFuzzer, ASAN,
cobertura-guided, exaustividade, produção, energia ou conformidade integral.
MIT própria e avisos existentes mantidos. Não executar fases seguintes.

Fonte: [OASIS MQTT3.1.1+Errata01](https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/errata01/os/mqtt-v3.1.1-errata01-os-complete.html).

## Revisão v1.1 — falha de compilação do harness, antes do ajuste

Rust1.99 informou padrão `&&str` incompatível na referência recursiva,
nome incorreto de variante AckKind e import não utilizado. Corrigir apenas
esses itens de teste, sem alterar runtime nem oráculos. Simplificar a captura
de falha para executar cada verificação uma vez. Nenhuma campanha executada
ou PASS inferido pela existência dos arquivos.

## Revisão v1.2 — parser do relatório/watchdog, antes do ajuste

Primeiro alvo executou25000 casos e passou no Rust, mas o driver classificou
FAIL porque libtest imprime o prefixo do teste na mesma linha que o JSON.
Encontrar o marcador na linha, mantendo exatamente um relatório esperado e
validando alvo/seed/contagem; relatório ausente/divergente continua FAIL.
Self-test do watchdog foi sensível a startup concorrente com timeout1s nos
casos normais/RSS: ampliar apenas esses fixtures para5s e suspensão8s,
mantendo teste de hang com deadline1s e orçamento real da campanha120s/512MiB.
Não mudar oráculo, reduzir casos ou enfraquecer gates para aceitar resultado.

## Revisão v1.3 — Clippy e precisão de evidência, antes dos ajustes

Campanha18 execuções/3seeds PASS (300000 casos rápidos,384 documentos e768
transições), mas Clippy reprova máscaras decimais/verbose, if aninhado e
função longa do modelo. Usar máscaras hex, high/low-nibble separados e
apenas allow too_many_lines localizado para manter modelo sequencial audível.
Precisar contadores: tópicos aceitos = ambos tipos válidos; fragmentação
aceitos = streams inteiros válidos, não contador fictício zero; maior payload
do router é observado, não o limite nominal. Driver registra SHA das fontes
antes/depois de compilar/executar e falha se elas mudarem durante a campanha.
Reexecutar os mesmos seeds/tetos/quantidades e gates após esses ajustes.

## Complemento v1.4 — QA de avisos delegada por P92, antes do código

Campanha v1.3 final18/18 e fontes estáveis; registro P90 guarda esse gate.
Coordenador delegou agora dois arquivos novos: `scripts/verify_phase3_notices.py`
e `scripts/test_phase3_notices.py`. Comparar payload.deb e diretório de licenças
nas imagens broker/adminlegado/client com coleta locked original, por textos
e SHA/size/paths, incluindo copyrightMIT no deb e LICENSE no Docker. Não
aceitar só um manifesto autodeclarado dentro do pacote. Recusar symlink/
traversal/duplicação em TAR sem extração em disco; testar tampering/ausência.
Linuxdpkg-deb pelo WSL para Windows, DockerWindowsCLI existente, containers
somente criados para `docker cp`, sem start/volumeoperador/portas/network.
Remover só esses containers próprios. Sem novos agentes, dependency, versão,
commit/tag/release/edições de arquivosmain/imagensantigas. Aguardar artifacts
P92 prontos antes do gate e registrar resultado real, não presumir sucesso.

## Complemento v1.5 — EOL da MIT própria, antes do ajuste QA

Coordenador conferiu diferença real: cópia Windows/LICENSE CRLF temSHA
acfd4bb82db195b2ba0a8a1ea6c5048d2e66c05a0fd0bd843e08d8a46d34b465;
Gitblob/cleanclone Linux LF temSHA
84381e555814f7125a9db5bce4f79b786cfb795b05eaddc2ef31a3a414842fc9.
Conteúdo/copyright/termos iguais. Permitir exclusivamente substituição
CRLF→LF na comparação canônica MIT própria; guardar SHA raw de cada arquivo
no artefato e SHA canônico no relatório. Nenhuma outra alteração de whitespace,
termo/copyright/BOM é aceita. Terceiros permanecem comparação byte-a-byte/SHA
STRICT, sem normalização. Testar ownMIT CRLFPASS, copyright alteradoFAIL e
terceiro EOL alteradoFAIL antes de validar os artefatos reais.

## Complemento v1.6 — limites agregados TAR, antes do reforço QA

Revisão do novo leitor de TAR encontrou teto por arquivo, mas ausência de
teto agregado para notices após descompressão. Reforço somente no harness:
64MiB de dados de notice lidos no total e20000 membros no máximo, além de
arquivo4MiB/archive64MiB existentes. Dois negativos com limites reduzidos
somente em mockunit verificam refusas; não ampliar quotas nem chamar isso
fuzzing de arquivos do broker. Reexecutar unitários e gate de artefatos depois.
