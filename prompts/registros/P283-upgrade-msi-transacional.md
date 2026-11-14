# P283 — atualização transacional do MSI

2026-11-14, America/Sao_Paulo. [Prompt P283](../broker/283-upgrade-msi-transacional.md).
Base `a4ffe7687947ea84ebb6c1cc20eb870bc361002b`.

- Reprodução: teste de política recusou o template sem Schedule e o
  verificador de tabelas recusou o MSI P281. Ambas as falhas ocorreram
  antes de corrigir os templates.
- Correção: Product.wxs e Manager.wxs usam afterInstallInitialize.
  O template Product é compartilhado pelos componentes Windows.
  Versões, UpgradeCodes e proteção de configuração foram preservados.
- PASS: `python scripts/verify_windows_packaging.py --wix`, 18 testes,
  incluindo as quatro fixtures compiladas e a inspeção somente leitura
  das tabelas InstallExecuteSequence pelo verificador PowerShell.
- PASS: `cargo fmt --all -- --check` e diff-check dos arquivos da correção.
- BLOCKED: WSL retornou E_ACCESSDENIED, Docker recusou o named pipe Linux
  e Git falhou ao resolver github.com. A CI e o pacote Ubuntu continuam
  pendentes. A instalação, o SCM e o rollback real exigem Windows descartável.

## Artefato revisado

- Commit da correção do instalador: `448ab7393564c5e41e1aba33ad87a8eb854410a1`.
- PASS: MSI Broker 0.45.0 r2 gerado por WiX 7 a partir de uma worktree
  limpa desse commit. Os contratos de UI e a ordem transacional passaram
  também no pacote real. A extração confirmou a versão, o UpgradeCode e
  o hash do executável instalado, idêntico ao executável validado P281.
- MSI `xmqr-broker-0.45.0-windows-x64-experimental-r2.msi`, SHA-256
  `5b04091d0465789809737837b89f094b13a3945bcea97d11999e6c63f408c64f`.
  ZIP, manifesto, LEIA-ME e SHA256SUMS estão em `dist/p283-broker-045-r2`.
- O executável foi reutilizado do build P281, fonte `e8712bf`, SHA-256
  `433c391e1a469a8a55b90057f339ec18a77288f2d0f0960a4027f09996f8f433`.
  `git diff --exit-code` confirmou igualdade de src, vendor, Cargo.toml,
  Cargo.lock e packaging/windows-service entre e8712bf e 448ab73.
  Esta etapa recompilou o MSI. O manifesto registra runtime_rebuilt=false.
- BLOCKED de compilação: Cargo do Manager encontrou link.exe indisponível.
  O prompt foi revisado para permitir o reempacotamento rastreável do Broker.
  Nenhum novo MSI do Manager foi incluído nessa entrega.
- BLOCKED de publicação: push de 448ab73 para release/validation-0.45.0
  falhou por DNS. O envio da árvore pela integração GitHub retornou HTTP 403,
  Resource not accessible by integration. Nenhuma tag ou release final criada.
- NOT_RUN: instalação, SCM e falha induzida para confirmar rollback em VM.
  Get-AuthenticodeSignature confirmou NotSigned. O pacote continua experimental.
