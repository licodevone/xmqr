# P274 v1.0 — ampliar para 1.000 conexões MQTT por nó

## Entrada e objetivo

Base `389c4897aeaef143f60a4ff496d320e7e45c2913`, candidato 0.44.0
com P271 (500) e P272 (ensaio integrado). Permitir configurar até
1.000 conexões MQTT e 1.000 sessões em um único processo.

## Escopo e compatibilidade

Ajustar as duas faixas no parser e em `StateLimits`. Manter 64 como
padrão e compatibilidade com a configuração de 500. Preservar o
formato v16, o orçamento agregado de 1.000.000 bytes e as demais
quotas, autenticação, TLS, ACL e confirmações de QoS. Sessões
persistentes offline continuam contando. Ao retornar ao candidato
anterior, usar quotas compatíveis e estado com até 500 sessões.

Atualizar os testes Rust e permitir selecionar 500 ou 1.000 no ensaio
integrado existente. Documentar o uso, descritores e as vagas
consumidas por Client/Bridge/console. Atualizar as notas da fonte
0.44.0 em preparação. O commit exato registrado por P273 é a base
anterior e suas evidências permanecem históricas.

## Aceite

- Validar 500 e 1.000 via preflight e rejeitar 1.001. Confirmar no
  roteador 1.000 sessões simultâneas, recusa da excedente e recuperação
  do estado, incluindo reabertura com quotas compatíveis.
- Executar em Ubuntu integração TCP de 1.000 clientes, recusa e
  reutilização de vaga. O ensaio do ecossistema usa um Client real
  e Admin HTTP com a contagem selecionada.
- Registrar fmt, testes e Clippy em `prompts/registros/P274-1000-conexoes-mqtt.md`.
  Carga sustentada, rajadas mTLS e publicação exigem gates próprios.
