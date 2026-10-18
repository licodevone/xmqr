# P228 — candidato043, registro de execução

2026-10-18. PromptP228 precedeu bump. Base funcionalc3713c8/P227E e
fronteirasP227I4a4488b; candidato6b8cf4b alterou Cargo/Docker/VERSIONING/nota.
Cargo check --offline -j1 PASS8,01s gerou lock com única alteração na versão
do pacote raiz042→043; dependências/checksums inalterados. Dockerbuild agora
serialj1, mesma runtime/configuração segura. Nada foi instalado no operador.

## Gates locais da fonte043

Rust1.99/Ubuntu26.04WSL, TMPDIR=/var/tmp, targetpadrão do broker:

- cargo test --locked --offline -j1:exit0/PASS. Compile78s,lib44,88s,
 287libPASS/6campanhasfuzz explícitas ignoradas; mais24testes dos bins e
 integraçõesPASS, total311PASS/0FAIL. Doc-tests0. Não somar filtros dirigidos.
- cargo fmt --all -- --check:exit0 sem alterações.
- cargo clippy --locked --offline --all-targets -j1 -- -Dwarnings:PASS19,83s.
- InventárioMIT: primeira invocaçãoPython em novoWSL semPATHRust falhou
 FileNotFoundError:cargo antes da análise. PromptP228v1.1 precedeu retry
 com PATHexplícito eCargooffline; script original --check PASS, declarações
 e inventário de dependências coincidem. Não houve instalação/configglobal.

Fullsuite foi executada com runtime/manifests6b8cf4b; commits posteriores
neste checkpoint alteram só documentação/prompts, não src/Cargo/Docker.
Buildbins/release, novoELF/congelamento, A21/admin16, CI final, pacote,
upgrade/rollback, imagens e anexos remotos ainda pendentes. Sem tag/release043,
sem aceite global6A–6D ou alegação de produção/certificação/perda de energia.

## Builds e campanha selecionada

Builddebug --locked --offline --bins -j1 PASS34,68s. Fonte pública ba6ef50,
runtime/manifests6b8cf4b; cópias novas congeladas sem substituir os ELFsD:

| ELFdebug | SHA256 |
| --- | --- |
| mqtt-broker-p227e-0.43.0 |fce0b871be72e5cfc7eb5a8dc46d04280075dd21dbbbb5b3677676952c6e9257|
| mqtt-admin-p227e-0.43.0 |6f2de794f67e4f0cf1ed59aaaea933ff7fc31516ac992a49fc2cee1dd27af854|

Ambos--version043PASS. Aceite selecionado6A usando clone limpo ba6ef50,
clienttagfca6fc8/ELFreleasea5ccc e admin010histórico17c3cff:32/32PASS,
83,018s, source_unchanged/binaries_unchanged=true. Relatório externo
../.artifacts/p227-acceptance-e-6a-5.json. Não equivale a6B–6D/admin16.

Buildrelease --locked --offline --release --bins -j1 FAILexit1: os12Cannot
allocate memory ao produzir arquivo temporário rlib. Ao mesmo tempo build
Docker próprio/notices observaram pressão/ENOMEM. P228v1.2 precedeu escolha
de serializar jobs; só o CLI do buildDocker próprio foi cancelado, referência
Buildx terminalError confirmada, nenhum daemon/serviço/stack alheio alterado.
Sem mudança de perfilLTO/RAM/swap ouprune. Cache/log parcial preservados.
Retryrelease aguarda slotadmin liberado, não foi reclassificado comoPASS.

Owneradmin executou A21 real9/9PASS3,1947s eCHANNEL_CLI_PASS com ELFfce43,
legadoDdca15 e admin010 repinado aoba6ef50/ELF6151a680d52356020e496f7f1103298909b2f4f63ff39eff0799f2503f1a8d37.
Esse ELF é candidato distinto do admin010 publicado/pinantigo; não inferir
compatibilidade de leitores só pelo número0.10.0. Admin011 e campanha global
continuam em preparação; relatórios completos ficam no registroA21/A22.
