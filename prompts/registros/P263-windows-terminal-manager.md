# P263 - Manager terminal Windows

2026-11-03. Prompt ../broker/263-windows-terminal-manager.md v1.1.
Pedido de frontend local futuro em Windows, adicional ao P262Linux; alteracoes
preexistentes preservadas. Sem Rust/Cargo/MSI/SCM/ACL/instalacao alterados.

## Entrega

PowerShell7 XMQR-Terminal.ps1 com menu/status/start/stop/restart/logs, filtro
de alvo, DryRun e privilegio administrativo explicito. Reutiliza diagnostico e
helpers do Manager publicado0.1.1. Caminhos/argv como dados, sem shell/elevacao
automatica; janela oculta do helper. Controle geral delegado ao backend
original que revalida HKLM64/SCM/ExecStart/ordem e aborta falha parcial.
Snapshot JSON tem schema/limites/IDs/states/units validados, CLI sem servico
nao vira alvo, alias client inequivoco e estado final reconsultado.

Busca eventos SCM com correspondencia exata em XML Data, limites temporais e
numericos; nao abre arquivos privados de log ou payloads dos componentes.

## Evidencia

- Parser PowerShell PASS, help/version PASS.
- Primeira suite FAIL no primeiro caso por array encapsulado duas vezes;
  prompt v1.1 preparado antes de corrigir enumeracao em snapshot/seletores.
- Suite final15/15PASS com invocador/estado/privilegio simulados. Negativos
  root, injecao, unidade externa, snapshot desconhecido, inventario falho,
  CLI-only, client ambiguo, helper falho, pos-condicao e helper hash errado.
  Nenhuma acao real start/stop/restart executada. EventLog real NOT_RUN.
- Build local encontrado com SHA19e171... diverge do oficial; NAO utilizado
  como helper e nao relaxado pin. Pacote oficial anterior em dist/releases/
  p256-verify/windows SHA481bbb... e exeSHA3c4e... conferidos contra registroP256.
- Novo ZIP154arquivos inclui o helper original, todas licencas/notices e
  proveniencia, mais frontend/readme/checksums. Sem rebuild do helper.
  Dois ZIPs temporarios identicos byte-a-byte PASS, todos hashes internos e
  hash do exe conferidos PASS. Artefato e checksum na raiz do agrupamento.
- Uso SCM administrativo real, UAC, EventLog e reboot NOT_RUN; nao inferir
  funcionamento instalado por testes simulados. Sem commit/push/tag/release.

## Pedido concomitante sobre painel Oracle

GitHub consultado em2026-11-03: ultimo release Admin v0.11.0, sem A23/A24/A25.
CI do HEADlocal28fea432 possui run39811883105 concluido FAILURE; nao promover
esse HEAD nem a fonte dirtyA29 para release aceita. Necessario diagnosticar
gates Linux, selecionar fonte validada, criar pacote/versionamento apropriado
e provisionar console/perfis mTLS/usuarios na VPS. Nenhum upgrade executado.
