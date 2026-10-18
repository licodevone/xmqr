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

## Retry nativo serial e fonte final da distribuição

O retry release, sem build Docker simultâneo nem alteração de perfil Cargo,
passou em107s (`cargo build --locked --offline --release --bins -j1`).
As cópias congeladas novas, sem substituir os artefatos anteriores, são:

| ELF release local | SHA256 |
| --- | --- |
| mqtt-broker-native-p228-0.43.0 | 5ba7c5bb09dc2a59caf7bbc3f7ba780c08f5e19d6581ddbb1f6c3f8d92cf5519 |
| mqtt-admin-native-p228-0.43.0 | d0cfcf978f5ef1242d51025befaa022c085ec51eed787d4e37ab5041a0b058e4 |

Ambos --version0.43.0PASS. O FAILENOMEM anterior permanece preservado.
Esses ELFs locais não são declarados idênticos bit a bit aos de outra build.
O pacote selecionado para publicação deverá ser o da CI39164202189,
fonte exata `db472bc64558bf0e376a902b7780a259247c5149`, com hashes e
lifecycle repetidos pelo ownerP228B. A campanha global remota ainda está
em execução; este registro não autoriza antecipar tag, Hub ou release.

## Gates finais aceitos e início da publicação

CI padrão39164202189 e CI integrada39164217059 SUCCESS na fonte congelada
db472bc64558bf0e376a902b7780a259247c5149. Esta última exercitou client040 e
admin011 em69fixturesPASS com13JSON baixados/conferidos; detalhes emP227.
Broker/adminrelease do build-provenance da CI integrada coincidem com os
ELFs1ee611b0/3081297f extraídos do pacote oficial da CI padrão.

Pacote selecionado:2.953.782bytes,SHA256
`c2341ab3a341b1854e85ebb2f0bec9535968374b226a12a60cee58aa7cef3d4e`.
Lifecycle finalP228B:5etapasPASS27,3274s com pacote/sourceCI reais. Imagens
Bookworm buildcache de runtime inalterado, VCS_REFdb, gatesmTLS/WSS/admin
e166pacotes/323notices originaisPASS. IDs locais475b31c8/673a062c.

Export original executado em checkout limpoEXATOdb, não na branch de merge:
manifestoSHA256499c409f3d3a0b8bcbdfd2de9bb6d6b97dd7869d17fe7d1aef780b3146cb1859.
Root repetiu comparações de tamanho/hash dos três artefatos do manifesto e
rótulos/UID10001 das duas imagens. Oito anexos originais maisSHA256SUMS e
ZIP13JSON/sidecar totalizam11anexos preparados, ainda sem anúncio remoto.
Publicação foi liberada ao ownerP228B somente depois do SUCCESS final;
reconferir tagGit/Hub/release antes de escrever e não moverlatest/tagsantigas.
