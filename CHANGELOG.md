# Histórico de versões

## 0.9.0 — candidato local, tag sugerida v0.9.0

- P45: `mqtt-admin state backup|verify|restore` para o estado durável MQTT offline.
- Backup compacta o WAL, guarda manifest TOML e SHA-256; verify testa recuperação
  em cópia temporária; restore só publica num diretório novo e nunca sobrescreve.
- Arquivos 0600 e diretórios 0700 em Unix. Bundle dinâmico, TLS e configuração
  externa não estão incluídos; backup/restore durável requer Linux/WSL.
- Evidência: `prompts/registros/P45-0.9.0.md`; gates Linux/WSL aprovados.



O projeto segue versionamento semântico. Enquanto a conformidade e a operação

de produção não passarem pelo gate de release, a série permanece `0.x`.

Mudanças incompatíveis ainda podem ocorrer nela. `1.0.0` exigirá testes de

interoperabilidade independentes, recuperação após falhas, revisão de segurança

e documentação de operação; versões `1.x` manterão compatibilidade prometida,

e `2.0.0` indicará quebra dessa compatibilidade.



## 0.8.0 - marco local validado, sem publicação



- Bundle privado opt-in com usuários, grupos, papéis e ACL; reload Linux por

  SIGHUP com commit antes da publicação da política e reautenticação obrigatória.

- Revogação de assinaturas, filas e Will; preservação de inbound QoS 2 aceito.

- Auditoria sem segredos; mesmos limites, dependências e formato durável.

- Interface e limitações em docs/security/dynamic-security.md; gates no registro P44.



## 0.7.0 - gates aprovados, aguardando publicação



- Monitoramento HTTP opcional, somente loopback: health, readiness por probe

  real do ator/writer e métricas Prometheus com labels finitos.

- Contadores de conexões, mensagens QoS, rejeições, commits/latência/snapshots

  e Will; gauges agregados de filas/sessões/retained. Sem novas dependências.

- HTTP limitado a 16 handlers, header 4096 bytes, read/write 1 s e probe 500 ms.

- Documento durável, quotas e MIT preservados. Não há release 0.7 aprovada;

  resultados e bloqueios estão no registro P43.



## 0.6.0 - tag v0.6.0 local/remota verificada



- Last Will MQTT3.1.1 duravel com QoS0/1/2, payload binario, retain, ACL e

  limite1024 bytes UTF-8. Queda, timeout, protocolo, takeover e cancelamento

  da task publicam; DISCONNECT cancela duravelmente.

- Retained existente revisado: substituicao, exclusao vazia, wildcard e restore.

- Documento MQTT v2 com leitura v1 e pending_wills; WAL/snapshot continuam v1.

  Rollback somente com backup completo anterior; nenhum estado real migrado.

- Cliente proprio recebe --will-topic/message/qos/retain. Script independente

  scripts/verify_last_will.py verifica ciclo de vida, restart e CLI sem Mosquitto.

- Lints assert_is_empty preexistentes de store e teste admin corrigidos.

- Linux/WSL Rust1.99:81 testes e9 integracoes PASS; fmt/Clippy/inventario/build

  PASS. Mosquitto e TLS/mTLS externo nao executados; sem conformidade integral.



## 0.5.0 - tag v0.5.0 verificada



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



## Resultado atual P43



2026-10-08:72 testes Unix, fmt/Clippy/inventário/build e6 integrações monitoring

mais9 regressões Will PASS, com cliente independente baseline26c1019. Seis

recusas de configuração reais também PASS. Histórico de bloqueios anteriores

não descreve o estado atual. Mosquitto/TLS/mTLS externo NOT_RUN. Aguardar

publicação do mantenedor; ver registro P43. Nenhuma implementação0.8 executada.
