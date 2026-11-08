# Registro P270 — preparação da campanha de desempenho

Data local: 2026-11-07, America/Sao_Paulo.
[P270 v1.0](../broker/270-performance-baseline-044.md).
Base `02097af27efe601ada936dc964d82936e6771e5a`.

- Preparado roteiro reproduzível para a linha de base do candidato 0.44.0.
  Revisados os três harnesses, conferidos os argumentos via `--help` e
  confirmada a presença da fixture na revisão indicada do client.
- Testes dos harnesses no Windows: 3 PASS e 1 SKIP em fan-out, 7 PASS
  em pressão. O teste omitido exige Linux. São verificações dos scripts.
- Campanha de carga BLOCKED. WSL recusou acesso, Docker recusou acesso
  ao pipe e um teste mínimo de socket local retornou WinError 10013.
  Git Bash também retornou acesso negado ao iniciar o verificador de
  sintaxe. Resultados de capacidade, throughput e latência da 0.44.0
  seguem pendentes.
- Escopo concluído: preparação e verificação documental. Runtime, manifesto,
  tag e release do broker continuam no estado de entrada.

### Nova tentativa — limite e socket local

- O binário debug informou `mqtt-broker 0.44.0`. Com TOML temporário,
  `--check-config` aceitou `max_connections=64` (saída 0) e recusou
  `65` (saída 2). A verificação não criou estado.
- O log de startup confirmou o listener open-lab isolado. A primeira
  conexão TCP retornou WinError 10013, assim como a sonda independente.
  WSL e Docker também recusaram acesso. Admissão MQTT e carga continuam
  BLOCKED. O processo e os arquivos de teste foram descartados.
