# P281 — empacotamento do Broker 0.45.0

2026-11-08, America/Sao_Paulo. [Prompt P281](../broker/281-instaladores-045.md).

- PASS: build oficial `scripts/build-windows.ps1 -Components broker`,
  WiX 7 x64, Cargo `--locked` em worktree limpa de
  `e8712bfcf885e3b12ce59173e1a483f5de58b5b5`. O processo gera
  também o MSI auxiliar do Manager 0.1.1 da mesma fonte.
- PASS: `mqtt-broker --version` retorna 0.45.0. O probe confirmou
  `service_entrypoint=true`. A inspeção do MSI confirmou ProductVersion,
  serviço `xmqr-broker`, ausência de partida automática durante a
  instalação e SHA-256 do executável extraído igual ao manifesto.
- PASS: SHA-256 do MSI
  `8f36f86db1855daf0fdf1fe043260e40413621d3bfc3cdcc9f6c00ecd2a9b99d`.
  O ZIP de entrega contém só o MSI do Broker, manifesto filtrado e
  `SHA256SUMS.txt`. O conteúdo do MSI no ZIP foi verificado pelo mesmo hash.
- BLOCKED: WSL retornou `Wsl/E_ACCESSDENIED`. Docker negou acesso ao
  `dockerDesktopLinuxEngine`. Nenhum `.deb` foi gerado.
- NOT_RUN: instalação, SCM, upgrade e rollback em Windows descartável.
  O MSI é experimental e não assinado. Sem alterações aos serviços,
  tag ou publicação de release.
- PASS estático: o MSI 0.43.0 de `candidate-p246-final-20261021` e o
  0.45.0 têm ProductCodes distintos e o mesmo UpgradeCode
  `{B2DE9967-4A95-4873-87C6-DF2B9F1C07F1}`. `Get-AuthenticodeSignature`
  confirmou `NotSigned` no novo MSI.
