# Registro P86 v1 — B06 e patch de recuperação

Pedido: continuar evolução por prompts, testes, commit/push e distribuições
aceitas. Data2026-10-13; base8e3f57cbee416279475a6cf9d32576e52c1d38e6,
branchcodex/p86-disk-faults. Broker limpo; clientd9d97d5/0.8.1 com seus dois
artefatos0.7.1 não rastreados preservados, sem alterações nesta etapa.
Skills locais Rust/MQTT, testes e segurança utilizadas; sem subagentes.

P86 criado antes do código; P87 antes do bump0.11.5. Injeção por instância
apenas cfg(test); Reader controlado revelou EIO convertido emUnexpectedEof
após leitura curta do tamanho, cujo replay permitia truncar a cauda. Extração
preservou a semântica inicial; teste RED exit1, raw_os_error=None em vez de5.
Correção propaga o erro; GREEN na suíte. Nenhuma mudança especulativa de quotas,
durabilidade, ACL, mTLS, dependências, MIT ou formato. Revisor principal percorreu
as fronteiras de commit/snapshot, dispatch, fechamento, replay e secrets/contexto.

## Gates realmente executados — Ubuntu26/WSL/Rust1.99

- cargo fmt --all -- --check: PASS exit0.
- cargo test --locked --quiet:123PASS (104lib+4admin+4main+1backup+2adminCLI+
  5config+1quotas+2version), sem skips/ignored. Doze testes novos/54subcasos.
- cargo clippy --locked --all-targets -- -D warnings: PASS exit0 após reparos.
- cargo build --locked --bins: PASS exit0.
- python3 scripts/license_inventory.py --check: PASS exit0; sem dependência nova.
- python3 scripts/test_distribution.py:5PASS exit0, contrato Docker/contexto.
- Client:fmt/54Rust/clippy/build/inventárioPASS exit0; runtime/árvore preservados.

Execuções intermediárias: o primeiro filtro `--exact` sem caminho completo
rodou0testes, NÃO foi considerado evidência. Repetição com filtro correto
produziu RED. Fmt aplicado. Clippy recusou similar_names, ponto-e-vírgula e
toomanylines do dispatch por inclusão da injeção; nomes/terminador corrigidos
e injeção test-only processada no loop do ator, sem relaxar lints. A segunda
recusa101/100 foi resolvida consolidando Stop/Inject no braço test-only. Alguns
patches de contexto recusados não alteraram arquivos. Sem falha final omitida.

## Aceite e limites

B06 aceito no recorte determinístico descrito em [campanha](../../docs/storage-faults.md).
Todos os testes usam recursos temporários; não preenche disco, não toca dados,
serviço, certificados de produção ou ESP32. EIO/ENOSPC são simulados; erro de
fsync completo pode recuperar commit não confirmado. Testes TCP são open-lab
loopback; mTLS externo é gate separado dos artefatosP87. Fase3continua parcial.

Registro anterior ao commit de código: não inventarSHA próprio. P87 identificará
commit exato, nova tag/deb/imagens e digests somente após publicação verificável.
