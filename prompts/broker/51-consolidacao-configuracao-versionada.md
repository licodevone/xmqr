# P51 rev1 — consolidação e desenho da configuração

Entrada: main d70e6f8, limpa; broker 0.10.0, client independente 0.5.0.
Pedido: avançar as funcionalidades propostas, uma etapa por vez e prompt antes
do código. Objetivo desta entrega: atualizar direção/evidência do roadmap,
desenhar configuração TOML versionada e consolidar regressão no Ubuntu26.

Escopo: docs/architecture/configuration.md, docs/ROADMAP.md, matriz de
conformidade e registro P51. Sem parser TOML novo nesta fatia; desenho explícito
para próxima implementação. Não modificar estado real, secrets, firmware,
serviços permanentes, versões ou formatos WAL/snapshot. Preservar ACL e quotas.

Aceite: desenho com precedência, campos, validação, rollback e testes previstos;
roadmap distingue implementado/proposto. Gates e integrações pertinentes
executados em estado temporário e registrados. C35 trata o cliente em seu repo.
Commit/push autorizados na conversa; nenhuma tag/release automática.
