# P40 — Auditar inventário de licenças, gates e versão

Tipo: manutenção existente. Leia LICENSE, Cargo.toml/Cargo.lock,
scripts/license_inventory.py, docs/licensing.md, docs/third-party-licenses.md,
.github/workflows/ci.yml (confirme nome real), CONTRIBUTING.md e VERSIONING.md.

## Prompt de trabalho

Preserve MIT no código XMQR e os direitos das dependências. Audite inventário
declarado e --check sem transformar inventário em parecer legal ou auditoria
de vulnerabilidade. Use dependências locais disponíveis, sem instalação automática.
Verifique CI: fmt/test/clippy, inventário, build e interop Mosquitto em Ubuntu.
Configuração de CI não prova execução nem valida Windows.
Mantenha versão 0.5.0 não publicada como estado inspecionado; contribuição comum
não muda versão. Release e tag só sob pedido próprio do mantenedor e após gates.
Inspecione divergências entre código e documentação antes de propor correção.
Sincronização Windows/WSL é explícita por Git com trabalho preservado; abrir pasta
não sincroniza clones. Nunca mudar safe.directory global, permissões, publicar,
fazer push ou pull automaticamente por ler este prompt.

## Aceite futuro

Inventário coerente, gates listados com resultado real quando autorizado,
manifest/lock/versionamento reconciliados e distinção clara entre snapshot e
release. Nenhum segredo, target ou dados operacionais incluídos no diff.
