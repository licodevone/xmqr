# P272 v1.0 — verificar o ecossistema XMQR com 500 conexões

## Entrada

Broker 0.44.0, base `02097af` mais P271 local. Client fonte `04189b6`.
Admin base `28fea43` com trabalho A29 no diretório. Managers no repositório
do broker. Preservar o trabalho existente e usar processos isolados.

## Objetivo e escopo

Preparar ensaio reproduzível com 500 conexões MQTT, incluindo um
`mqtt-client` real, e consulta autenticada de `/api/status` do Admin.
Usar harnesses de laboratório existentes e `scripts/verify_suite_500.py`.
Executar testes locais dos Managers Windows/Ubuntu. O inventário de serviços
dos Managers e as sessões de login do Admin têm quotas próprias.
Documentar orçamento de vagas e critérios de capacidade em
`docs/capacity-500.md`. A configuração de runtime mantém a semântica P271.

## Aceite e validação

- Em loopback, manter 499 conexões wire e uma assinatura do Client. Provar
  SUBACK, observar 500 conexões e sessões no Admin autenticado e verificar
  recusa de acesso anônimo e da 501ª conexão MQTT.
- Com o broker cheio, enviar PUBLISH QoS 1 de uma conexão já ativa, confirmar
  PUBACK e validar a entrega no Client. Verificar o reaproveitamento da vaga
  após a saída do assinante. Excluir processos, credenciais e estado de teste.
- Nos Managers, validar inventário e consulta de serviços em fixtures
  existentes. A validação de SCM/systemd reais sob carga requer instalação
  descartável. Admin Console e Bridge usam vagas do broker quando ativos.
- Guardar versões e hashes dos binários. A aceitação mTLS, o máximo de
  publicações/s e os percentis de latência exigem campanha de carga própria.
  Registrar execução e bloqueios em `prompts/registros/P272-aceite-integrado-500.md`.
