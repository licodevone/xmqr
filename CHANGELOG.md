# Histórico de versões

O projeto segue versionamento semântico. Enquanto a conformidade e a operação
de produção não passarem pelo gate de release, a série permanece `0.x`.
Mudanças incompatíveis ainda podem ocorrer nela. `1.0.0` exigirá testes de
interoperabilidade independentes, recuperação após falhas, revisão de segurança
e documentação de operação; versões `1.x` manterão compatibilidade prometida,
e `2.0.0` indicará quebra dessa compatibilidade.

## 0.5.0 — em desenvolvimento, ainda não publicada

- Filtros MQTT 3.1.1 `+` e `#`, níveis vazios e tópicos `$` explícitos;
  nomes de publicação e filtros são tipos distintos, validados também no restore.
- Uma entrega por cliente para filtros sobrepostos, no maior QoS aplicável,
  incluindo deduplicação de mensagens retidas no mesmo SUBSCRIBE.
- ACL exige literalmente o filtro solicitado; tópicos concretos são
  revalidados no fan-out e na recuperação de filas offline/inflight.
- Script reproduzível com clientes Mosquitto para QoS 0/1/2, retained,
  reinício, sessão persistente, UNSUBSCRIBE e pacotes inválidos, incorporado ao CI.
- Inventário verificável das licenças declaradas das dependências, mantendo
  o código XMQR sob MIT e os direitos dos componentes de terceiros.
- O formato de estado permanece na versão 1. A 0.4 lê estados antigos,
  mas não entende assinaturas wildcard produzidas pela 0.5: antes do retorno,
  remova-as com UNSUBSCRIBE ou restaure um backup completo anterior.
- Tópicos e filtros aceitam até 1024 bytes UTF-8, com limite compartilhado
  entre broker e CLI; fronteiras ASCII/multibyte, wire, ACL e restore têm testes.
  O formato v1 permanece, mas snapshots anteriores com limite 256 não restauram
  nomes longos: preserve backup anterior completo para retorno.
- Limites continuam explícitos: 1024 bytes por tópico/filtro, 256 assinaturas
  por sessão e 64 sessões. Last Will, escala e operação de produção continuam pendentes.

## 0.4.0 — 2026-09-24

- Etapas didáticas `password-lab` e `acl-lab`, sem TLS e restritas a loopback,
  para introduzir autenticação e autorização separadamente.
- Usuários de laboratório podem usar somente senha, sem fingerprint ou
  certificado; `secure-mtls` continua exigindo os três fatores.
- `mqtt-admin user create|list|update-password|delete` com lock, arquivo
  temporário `0600`, validação, rename atômico e sincronização durável.
- Roteiro executável para acesso aberto, senha, ACL, tópico permitido/negado e
  administração de usuários; TLS permanece etapa posterior.

## 0.3.0 — 2026-09-24

- Modo didático explícito `MQTT_MODE=open-lab`, limitado a loopback, para
  demonstrar MQTT 3.1.1 QoS 0 sem TLS, autenticação ou ACL.
- Cliente de laboratório com `--open-lab`, sem certificados ou prompt de senha.
- Separação dos diretórios de estado por perfil, impedindo que o laboratório
  aberto reutilize ou remova sessões do modo seguro.
- Roteiro inicial de três terminais para publicar e receber dados manualmente.

## 0.2.0 — 2026-09-23

- MQTT 3.1.1: QoS 1/2 nos dois sentidos, `PUBACK`/`PUBREC`/`PUBREL`/`PUBCOMP`,
  `UNSUBSCRIBE`, mensagens retidas e sessões persistentes com `CleanSession=0`.
- Estado MQTT versionado no WAL existente; commit com `fsync` antes dos ACKs
  que transferem responsabilidade, quotas e snapshots periódicos.
- Cliente de laboratório com `--qos`, `--retain` e `--clean-session`.
- Não é uma declaração de conformidade MQTT 3.1.1 completa ou prontidão de
  produção: Will, filtros wildcard, testes externos de interoperabilidade,
  escala e operação ainda precisam de trabalho.

## 0.1.0 — base inicial

- Transporte TLS/mTLS, autenticação usuário/senha com vínculo ao certificado,
  ACL de tópicos exatos e fluxo MQTT QoS 0.
