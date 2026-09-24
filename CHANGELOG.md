# Histórico de versões

O projeto segue versionamento semântico. Enquanto a conformidade e a operação
de produção não passarem pelo gate de release, a série permanece `0.x`.
Mudanças incompatíveis ainda podem ocorrer nela. `1.0.0` exigirá testes de
interoperabilidade independentes, recuperação após falhas, revisão de segurança
e documentação de operação; versões `1.x` manterão compatibilidade prometida,
e `2.0.0` indicará quebra dessa compatibilidade.

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
