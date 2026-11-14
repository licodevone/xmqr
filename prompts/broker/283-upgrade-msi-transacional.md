# P283 v1.0 — atualização transacional do MSI 0.45.0

Entrada em 2026-11-14: Broker `a4ffe7687947ea84ebb6c1cc20eb870bc361002b`,
0.45.0 em validação, com histórico de chat editado localmente. O P282
identificou a remoção de 0.43.0 antes de InstallInitialize no MSI P281.
Client independente em `46f96b5`, 0.44.0, com registros locais preservados.

## Objetivo e arquivos

Corrigir o agendamento de MajorUpgrade em `packaging/windows/Product.wxs`
e `Manager.wxs`. O primeiro é compartilhado pelos instaladores Broker,
Client e Admin. Usar `Schedule="afterInstallInitialize"` para incluir a
remoção no escopo de rollback do Windows Installer. Manter identificadores
de upgrade, configuração permanente, controles de serviço e versões.

Ampliar `scripts/verify_windows_packaging.py` para verificar a política
e `scripts/verify_windows_installer_ui.ps1` para conferir a tabela de sequência
efetivamente compilada nas fixtures MSI, aberta somente para leitura. Documentar a revisão
nas notas 0.45.0 e em `packaging/windows/README.md`. A fonte Rust e o estado
v16 não exigem migração para esta correção.

## Aceite e execução

1. Demonstrar a regressão no agendamento anterior e executar os contratos
   de empacotamento, incluindo fixtures compiladas e decompiladas por WiX.
2. Gerar novos MSIs pelo builder oficial com lockfiles, fontes identificadas,
   probes e hashes. Confirmar no pacote Broker real que InstallInitialize
   precede RemoveExistingProducts e que este precede ProcessComponents.
3. Executar upgrade 0.43.0 → 0.45.0 e falha induzida após a remoção em
   Windows descartável elevado, quando disponível. A sequência compilada
   não substitui a execução de rollback e do serviço como LocalService.
4. Reavaliar os bloqueios Linux, GitHub e Client sem mudar permissões do host.
   Registrar resultados reais em `prompts/registros/P283-upgrade-msi-transacional.md`.
   Publicar tag/release somente após os gates completos do P279.

## Reprodução antes da correção

O novo teste de política falhou no template anterior, que não tinha Schedule.
O verificador de tabelas também recusou o MSI P281 por remover a versão
anterior antes de InstallInitialize. Os dois resultados são regressões
esperadas que demonstram o defeito antes da alteração dos templates.
