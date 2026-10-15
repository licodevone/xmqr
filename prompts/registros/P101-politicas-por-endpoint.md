# P101 — isolamento de políticas por endpoint

- Prompt [P101](../broker/101-politicas-por-endpoint.md) antes do código, após
  integração P100. `[[endpoint_policies]]` exige mapeamento completo do bind
  primário e adicionais, arquivos de usuários/ACL próprios, sem bundle ou
  arquivos globais misturados. O modo compartilhado anterior é preservado.
- Principal e client ID recebem escopo interno por endpoint. O roteador usa a
  visão global para revalidar ACL no publish/subscribe/entrega/replay/Will;
  listener autentica somente seu escopo. Perfil durável separado
  `secure-mtls-scoped` recusa migração silenciosa de estado compartilhado.
- Ubuntu26/WSL `verify_scoped_endpoints.py` PASS: mesmo usuário e client ID em
  dois endpoints sem takeover, QoS1 entre endpoints, ACLs diferentes, senha
  incorreta, retained do primário no secundário após restart, mapeamentos
  incompletos/duplicados/estranhos, bundle misturado e estado legado recusados.
  Regressões P96/P100/P97 PASS após a implementação.
- Gates Rust Ubuntu26/WSL finais antes do bump: 114 testes lib PASS/6 campanhas
  explícitas ignoradas, demais binários/integrações PASS; fmt, Clippy
  `-D warnings`, build, inventário e `test_distribution.py` 6/6 PASS. TLS é
  comum aos endpoints; não há CA distinta por bind. Ciclo de distribuição do
  marco conjunto P100/P101 em P103.
