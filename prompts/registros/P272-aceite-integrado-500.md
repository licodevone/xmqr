# Registro P272 — integração a 500 conexões

Data local: 2026-11-07. [Prompt P272 v1.0](../broker/272-aceite-integrado-500.md).

- Implementado o harness de loopback com processos e estado próprios.
  Sintaxe Python e CLI `--help` PASS. Testes da fixture de pressão: 7 PASS.
- Manager Windows: 20 PASS (Cargo locked/offline). Ubuntu: 42 PASS e 4
  SKIP nos testes Python de inventário, backend e terminal. São fixtures,
  sem homologação de SCM/systemd reais durante o ensaio.
- Admin: parser isolado compilado com rustc, 3 PASS, inclusive métricas
  de 500 conexões e 500 sessões. Cargo do Admin bloqueado pela falta de
  `windows-permissions` no cache offline.
- Client: binário pré-existente 0.43.0 aceitou as opções de assinatura
  da campanha e chegou ao transporte. O binário não contém C153
  (`--check-config`); rebuild/testes Cargo bloqueados pela mesma dependência.
- Ensaio integrado BLOCKED. Sonda TCP retornou WinError 10013. WSL e
  Docker recusaram acesso. A execução Ubuntu com os três binários, a
  carga mTLS e a taxa sustentada de publicações continuam pendentes.
- Documentado o orçamento de vagas MQTT, requisições HTTP do Admin e
  componentes locais do Manager. Os executáveis dos produtos não ganharam
  novos limites nesta etapa de validação.
