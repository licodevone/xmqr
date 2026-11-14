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

O build e os hashes da revisão são registrados após gerar os novos artefatos.
