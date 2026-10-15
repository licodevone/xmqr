# P108 rev1 — inventário e ações administrativas de sessões/retained

2026-10-15. Entrada: broker `7c25e3f` P107, socket status/reload/receipt;
admin CLI `01565ec`. Fase 5/A07/A09 ainda abertos. Criar primeiro esta fatia,
preservando o ator como único escritor e o documento durável MQTT v3.

Adicionar leituras paginadas, limitadas e sem payload de sessões e retained
pelo canal local operator. Cada item de sessão traz ID, estado conectado,
persistência e contagens finitas; retained traz tópico e QoS, sem payload.
Cursor lexical, budget de itens/resposta, sem snapshot de WAL pelo admin.
Exigir token operator por sensibilidade dos metadados. Não expor ao viewer.

Depois das leituras, avaliar ações `retained_delete` e `session_disconnect`.
Qualquer mutação deve ter request_id, deduplicação/auditoria no mesmo commit,
resultado desconhecido tratável por receipt e negativo de quota/storage.
`session_disconnect` deve definir Will e QoS2 antes de alterar estado.
Não executar exclusão de sessão durável por atalho; preserve ownership.

Arquivos: `src/admin_channel.rs`, `src/mqtt/router.rs`, testes, docs,
registro e matriz. Negativos: cursor inválido, viewer, página grande, tópico
inválido, concorrência com publish/reload e restart. Validar fmt/test/Clippy,
processo isolado e integração admin. A07/A09 só fecham após ações, testes
de falha/concorrência e aceite global; inventário sozinho é parcial.
