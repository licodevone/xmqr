# P271 v1.3 — permitir 500 conexões MQTT simultâneas

## Entrada

Broker 0.44.0 candidato no commit `02097af27efe601ada936dc964d82936e6771e5a`.
A configuração limita conexões e sessões a 64. P270 prepara a medição de
carga. Preservar alterações locais e o histórico das versões publicadas.

## Objetivo e escopo

Permitir a configuração explícita de até 500 conexões MQTT simultâneas
por processo e de até 500 sessões. Aumentar as duas faixas em
`src/configuration.rs` e `src/mqtt/limits.rs`. Manter 64 como padrão
e documentar a configuração em `docs/architecture/configuration.md`
e no README. A admissão continua compartilhada entre listeners.

## Requisitos e compatibilidade

- `max_connections` e `max_sessions` são quotas independentes. Sessões
  persistentes desconectadas continuam contando para `max_sessions`.
- Rejeitar valores acima de 500 na validação da configuração. Preservar
  precedência de ambiente, TLS, autenticação, ACL, filas e semântica de QoS.
- Preservar formato v16, limites por sessão e o limite agregado de bytes
  do documento. A meta vale para sessões que caibam nesse orçamento.
  A configuração anterior permanece válida. Para retorno a um binário
  com teto 64, preservar backup compatível antes do upgrade. Uma quota
  reduzida abaixo do estado existente deve falhar sem descartar sessões.

## Aceite e validação

- Testar limites, defaults, TOML e ambiente nos testes existentes.
- Manter 500 sessões vivas no roteador com persistência real e verificar
  recusa da 501ª e reabertura do estado com quota compatível.
- Em integração TCP loopback, obter CONNACK para 500 clientes distintos
  mantidos conectados, observar a recusa excedente e verificar que os
  clientes admitidos seguem respondendo. Testar reutilização da vaga.
- Rodar fmt, testes e Clippy. Medir reconexões mTLS, latência e throughput
  em Ubuntu separadamente. Contagem de conexões não mede publicações/s.
  Registrar o que foi executado em `prompts/registros/P271-500-conexoes-mqtt.md`
  e aplicar os gates de versão e pacote antes de tag ou release.

## Revisão 1.1

O Clippy 1.99 apontou `assert_is_empty` em um teste de preflight
existente. Comparar diretamente a saída com bytes vazios, preservando a
asserção, e repetir o lint. Registrar à parte os avisos de código
administrativo exclusivo de Unix no build Windows.

## Revisão 1.2

A execução manual da fixture TCP em Windows expirou antes do primeiro
CONNECT. Durante a espera do listener, repetir somente conexão
recusada e propagar demais erros de socket para identificar o bloqueio.

## Revisão 1.3

O Clippy marcou a fixture após explicitar o erro de socket. Simplificar
a preparação do comando do processo de teste e repetir o lint.
