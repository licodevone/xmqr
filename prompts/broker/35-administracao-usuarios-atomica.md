# P35 — Auditar o CRUD local de usuários

Tipo: manutenção existente. Leia src/bin/mqtt-admin/main.rs, users.rs,
src/auth/mod.rs e docs/administracao-usuarios.md; siga contrato-base.

## Prompt de trabalho

Audite mqtt-admin user create|list|update-password|delete, entradas e códigos de
saída. Senha interativa confirmada, Argon2id e listagem somente de nomes.
Preserve lock, rejeição de symlink, arquivos privados, limites, temporário validado,
fsync, rename e sync de diretório. Não sobrescrever arquivo inválido nem remover
usuário errado. create cria usuário sem fingerprint para laboratório; não afirmar
que provisiona identidade mTLS ou emite certificados. update preserva campos
existentes. Exclusão em acl-lab exige coerência das regras; política é carregada no
startup, sem revogação instantânea em processo vivo. Não inventar hot reload.
Fora de Unix o código retorna Unsupported: não prometer CRUD nativo Windows.

## Aceite futuro

Testar duplicata, ausente, nome inválido, senha diferente, TOML desconhecido,
symlink, permissões, concorrência, falha antes do rename, exclusão do último usuário,
nenhum hash em list/log e preservação de fingerprint. Usar cópias descartáveis em
Linux/WSL confirmado; nenhum arquivo real de usuários alterado por esta importação.
