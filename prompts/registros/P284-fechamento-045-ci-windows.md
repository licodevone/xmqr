# P284 — fechamento Windows preparado

2026-11-14, America/Sao_Paulo. [Prompt P284](../broker/284-fechamento-045-ci-windows.md).
Base `809a1e3`. Mantidas as alterações anteriores do histórico de chat.

- Implementado workflow Windows em runner hospedado 2022 com MSVC, WiX 7,
  build locked da base 0.43.0 fixada em 36f340facbbccc9ac4746f5ad4bd84ff2d33387a
  e build do Broker/Client pareados. Reusa os testes de processo e SCM.
- Implementado ensaio MSI real com falha intencional depois da remoção,
  recuperação automática da base, preservação de configuração/dados,
  upgrade e retorno operacional usando cópia privada de estado sintético.
- O Client pareado usa o helper SCM existente com configuração privada,
  saída JSONL e Broker instalado ativo. A cópia de falha não é anexada ao
  artefato de pacotes do workflow.
- FAIL inicial de sintaxe: literal terminado por barra invertida. Prompt
  revisado antes da correção e demais checagens repetidas após corrigir.
- PASS local: py_compile, YAML dos dois workflows e sintaxe dos 20 blocos
  PowerShell dos workflows e do ensaio. As duas pré-condições recusaram
  execução do instalador no host antes de criar a pasta de saída.
- PASS local: preparo e leitura de uma cópia descartável do MSI P283 r2,
  com ProductCode independente e erro intencional inserido por tabela.
  Isso verifica a preparação da fixture, sem executar o Windows Installer.
- PASS local: nova execução dos 18 contratos de empacotamento com WiX,
  incluindo a compilação e inspeção das quatro fixtures MSI.
- BLOCKED: Git/DNS, crates.io/DNS, WSL/E_ACCESSDENIED e Docker/named pipe
  continuam indisponíveis. Os jobs Windows/Ubuntu e o rollback real não
  foram executados nesta sessão. Nenhuma release ou tag final criada.

A CI roda ao enviar os commits para branches `release/**`. O job do Broker
usa o Client 46f96b5 por SHA. Enviar primeiro a branch do Client disponibiliza
esse ancestral. Somente resultados reais da CI podem fechar os gates P279.
