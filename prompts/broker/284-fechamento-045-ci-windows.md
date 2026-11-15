# P284 v1.1 — fechamento da 0.45.0 em Windows descartável

Entrada: Broker `809a1e3`, com P283 implementado e MSI r2 gerado. Preservar
o histórico local e os registros existentes. WSL/Docker e rede nativa
continuam indisponíveis nesta sessão. A integração GitHub recusou escrita.

Objetivo: tornar executáveis no GitHub Actions os gates pendentes do Windows,
usando runner hospedado descartável. A validação Ubuntu existente continua
obrigatória. Alvos: `.github/workflows/windows-release.yml`,
`scripts/verify_windows_msi_upgrade.py`, documentação e registro P284.

- Compilar e empacotar o Broker atual e uma base 0.43.0 construída do
  commit fixo `36f340facbbccc9ac4746f5ad4bd84ff2d33387a`.
- Reusar os ensaios nativos de processo e SCM existentes. Acrescentar um
  ensaio do MSI real que confirme dados e configuração preservados,
  atualização 0.43.0 → 0.45.0 e rollback automático após falha inserida
  na cópia descartável do MSI, depois de RemoveExistingProducts.
- Com o Broker do MSI ativo, permitir o ensaio SCM existente do Client
  pareado, com configuração e saída JSONL sintéticas e ACLs privadas.
- O ensaio de instalação exige flag explícita, Windows elevado, identificação
  de VM, ambiente de runner hospedado e ausência inicial do serviço/produto.
  As cópias com falha são exclusivamente material de teste.
- Validar sintaxe e pré-condições localmente e testar a cópia de falha
  somente por inspeção de tabelas MSI. Execução local em produção é recusada.
- Fazer commit/push da fonte de validação, acompanhar a CI quando houver
  acesso e registrar falhas antes de corrigir. Tags e release somente depois
  dos gates reais. Ausência de execução em VM não equivale a aprovação.

A configuração de laboratório e o estado do ensaio são sintéticos e
restritos a loopback. O formato MQTT v16 e as credenciais reais não migram
como consequência desta infraestrutura de validação.

Revisão local: a primeira checagem de sintaxe identificou uma string de
registro terminada por barra invertida. Corrigir esse literal e conferir
também a delimitação dos scripts PowerShell embutidos antes dos demais gates.
