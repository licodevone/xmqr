# Administração de usuários sem certificados

Estes comandos gerenciam o arquivo usado pelos modos `password-lab` e
`acl-lab`. Eles não criam nem exigem certificado, fingerprint ou
`cert_sha256`.

> **Atenção:** nesses dois modos a senha MQTT trafega sem criptografia. Use
> somente em `127.0.0.1` para aula. Nunca use em produção, rede pública ou LAN.

## Preparação

```bash
cd /caminho/para/xmqr
export CARGO_TARGET_DIR="$HOME/.cache/mqtt-broker-target"
cargo build --locked --release --bin mqtt-admin
mkdir -p "$HOME/.config/mqtt-broker"
```

O arquivo usado nos exemplos será:

```bash
export MQTT_LAB_USERS="$HOME/.config/mqtt-broker/lab-users.toml"
```

## Criar usuário

```bash
"$CARGO_TARGET_DIR/release/mqtt-admin" user create \
  --users-file "$MQTT_LAB_USERS" \
  --username 'aluno'
```

A senha é solicitada duas vezes sem aparecer na tela. Resultado esperado:

```text
Usuario criado: aluno
```

O arquivo é criado com permissão `0600`. O registro possui somente nome e hash
Argon2id; não possui `cert_sha256`.

## Listar usuários

```bash
"$CARGO_TARGET_DIR/release/mqtt-admin" user list \
  --users-file "$MQTT_LAB_USERS"
```

Somente os nomes, em ordem, são mostrados. Hashes e senhas nunca aparecem.

## Atualizar a senha

```bash
"$CARGO_TARGET_DIR/release/mqtt-admin" user update-password \
  --users-file "$MQTT_LAB_USERS" \
  --username 'aluno'
```

Resultado esperado depois de informar a nova senha duas vezes:

```text
Senha atualizada: aluno
```

## Excluir usuário

Antes de excluir um usuário do modo `acl-lab`, remova também sua regra do
arquivo ACL. Uma ACL que referencia usuário inexistente faz o broker falhar
fechado ao reiniciar.

```bash
"$CARGO_TARGET_DIR/release/mqtt-admin" user delete \
  --users-file "$MQTT_LAB_USERS" \
  --username 'aluno'
```

Resultado esperado:

```text
Usuario excluido: aluno
```

É permitido excluir o último usuário. O arquivo permanece válido e o broker
recusará todas as autenticações.

## Quando as mudanças entram em vigor

O broker carrega usuários e ACL somente ao iniciar:

- Criar usuário exige reiniciar para ele conseguir conectar.
- Atualizar senha exige reiniciar; conexões já abertas continuam válidas até
  serem encerradas. Depois do reinício, somente a senha nova funciona.
- Excluir usuário exige reiniciar; as conexões caem no reinício e as sessões
  persistentes do usuário excluído são removidas durante a recuperação.
- Alterar ACL exige reiniciar. Assinaturas e filas que deixaram de ser
  permitidas são removidas na recuperação.

As operações administrativas usam um lock lateral, validam o arquivo inteiro e
publicam a mudança por arquivo temporário privado, `sync_all`, rename atômico e
sincronização do diretório. Uma falha antes do rename mantém a versão anterior.

