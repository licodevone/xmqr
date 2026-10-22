# P252 - Manager: cores do simbolo X

Data: 22/10/2026. Subtarefa de fonte/UI do Manager; sem alteracao de versao.

## Comportamento implementado

- `src/icon_pixels.rs` transforma a mascara RGBA fornecida por assets, sem
  acrescentar bolinha, texto ou pixels fora da silhueta original.
- `Color::Green` aplica RGB 35/190/105 e conserva o alpha original. Os demais
  estados aplicam RGB 128/137/148 com alpha reduzido a 3/5; a UI ja representa
  operacao em andamento por `Color::Yellow`, portanto tambem fica apagada.
- `src/ui.rs` usa essa transformacao para o icone da bandeja. A legenda informa
  que verde significa todos os servicos em execucao e que conexao MQTT nao foi
  verificada. Modelo de diagnostico, menus e ocultacao sem instalados preservados.
- `src/main.rs` registra o modulo em Windows e em testes.

## Validacao

Diretorio de trabalho: `tools/windows-manager`. Cache Cargo offline usado:
`C:\Users\licod\AppData\Local\Temp\xp242-cargo`; `CARGO_INCREMENTAL=0`.
Testes usaram diretorio temporario exclusivo para TMP/TEMP.

1. `cargo fmt --all -- --check`: PASS, inclusive apos inclusao do build.rs nativo.
2. `cargo test --locked --offline --release --target x86_64-pc-windows-msvc --target-dir target/windows-msi`:
   PASS, 13 testes, compilacao 54,06 s e execucao 0,76 s. Inclui dois testes de
   preservacao de silhueta/antialiasing e ausencia de verde nos estados apagados.
3. `cargo clippy --locked --offline --release --all-targets --target x86_64-pc-windows-msvc --target-dir target/windows-msi -- -D warnings`:
   PASS em 20,12 s, ja com build.rs nativo presente.
4. `cargo build --locked --offline --release --target x86_64-pc-windows-msvc --target-dir target/windows-msi`:
   PASS em 5,11 s, apos fornecimento do RGBA/ICO e build.rs pelo responsavel pelos assets.
5. `xmqr-manager.exe --version`: `xmqr-manager 0.1.0`; modo de versao sai antes
   de singleton/UI/consulta de servicos.
6. `git diff --check -- src/main.rs src/ui.rs src/icon_pixels.rs`: PASS.

Executavel resultante:
`tools/windows-manager/target/windows-msi/x86_64-pc-windows-msvc/release/xmqr-manager.exe`.
Tamanho: 977920 bytes. SHA-256:
`2EE8CB3EA1B914724896FA91EDF42B813E51A8D3509DEAFB05A5F5ABD086BA2D`.

O asset RGBA fornecido tem 4096 bytes (32x32), 433 pixels com alpha positivo,
591 transparentes e 288 com alpha parcial. Esta verificacao mede a mascara;
nao e prova visual da bandeja, escala DPI ou funcionamento instalado.

Nenhuma janela do Manager foi aberta, nenhum servico foi iniciado/parado e
nenhuma instalacao foi atualizada por esta subtarefa. Auditoria do recurso PE,
preview da imagem, atualizadores e aplicacao instalada pertencem as etapas
de integracao P252 dos respectivos responsaveis.
