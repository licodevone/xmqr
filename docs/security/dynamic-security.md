# Segurança dinâmica do broker (P44, 0.8.0 local)

Recurso opcional para Linux/WSL, ativado por `MQTT_SECURITY_BUNDLE` com o caminho
absoluto de um bundle TOML privado. Aceita `secure-mtls` e `acl-lab`; este último
continua restrito a loopback. Sem a variável, os perfis e arquivos legados mantêm
o comportamento anterior. O bundle rejeita `MQTT_USERS_FILE` e `MQTT_ACL_FILE`.
Windows compila os perfis legados, mas rejeita o bundle dinâmico. Outros sistemas
Unix também não têm a validação de arquivo Linux implementada nesta fatia.

## Bundle e permissões

O arquivo deve ser regular, sem symlink, de propriedade do UID efetivo do broker,
com modo exatamente 0600 e até 1 MiB. Use filesystem Linux privado no WSL.
Campos desconhecidos, versões distintas de 1, referências inexistentes e nomes
ou memberships duplicados são recusados. Não há normalização implícita de nomes.

```toml
version = 1

[[roles]]
name = 'sensor'
publish = ['sensor/value', 'status/device']
subscribe = ['sensor/#']

[[groups]]
name = 'devices'
roles = ['sensor']

[[users]]
username = 'device'
password_hash = 'REPLACE_WITH_ARGON2ID_PHC_HASH'
# Obrigatório em secure-mtls; fingerprint do certificado DER apresentado.
cert_sha256 = 'sha256:REPLACE_WITH_64_HEX_DIGITS'
disabled = false
roles = []
groups = ['devices']
publish = []
subscribe = []
```

O exemplo é um esquema, não uma configuração executável. Obtenha o hash pela
entrada interativa de `mqtt-admin hash-password` e o fingerprint por
`mqtt-admin fingerprint`, conforme [autenticação](auth-acl.md). Nunca coloque
senha como argumento nem use a credencial pública das fixtures em uma instalação.
Em acl-lab, `cert_sha256` pode ser omitido. Em secure-mtls, certificado, senha e
vínculo de fingerprint continuam obrigatórios; o reload não troca CA/CRL/TLS.

Concessões diretas, papéis e grupos formam uma união. `publish` exige tópicos
concretos; `subscribe` exige o filtro literal concedido. A entrega verifica o
tópico concreto, preservando a regra `$`. Usuário ausente ou desabilitado não
autentica; nenhuma concessão é implícita. Limites: 1024 usuários, 128 papéis,
128 grupos, 64 papéis/grupos por usuário, 64 papéis por grupo e 256 concessões
publish/subscribe por papel e por usuário efetivo. Quatro slots Argon2 são
compartilhados entre todas as gerações. Limites MQTT e formato durável não mudam.
Para um bundle vazio, declare `version = 1` e `users = []` no nível raiz.

## Interface administrativa real

A interface desta versão é o sinal local SIGHUP do processo Linux. Não existe
endpoint HTTP/MQTT de administração nem CRUD de bundle no mqtt-admin. Um operador
com acesso ao arquivo privado e permissão do sistema operacional para sinalizar
o processo prepara uma cópia privada completa, valida seu TOML, faz rename
atômico e sincroniza arquivo/diretório. Não sobrescreva parcialmente o bundle.
Depois sinalize somente o PID conhecido dessa instância:

```sh
kill -HUP <PID_DO_BROKER>
```

O watcher processa uma atualização por vez; sinais pendentes podem se agrupar.
O candidato é lido e validado fora dos workers Tokio. O ator reconcilia e faz
commit durável antes de publicar a política e incrementar a geração. A fila
administrativa é limitada; uma recusa de admissão não altera a política.
Bundle inválido mantém geração, política e conexões anteriores. Falha de
persistência não publica a candidata e usa o encerramento seguro existente;
não promete disponibilidade após commit incerto.

Após um reload válido, TODAS as conexões do perfil dinâmico são encerradas para
exigir nova autenticação, mesmo usuários sem mudanças. O processo e listener
continuam ativos. CONNECT autenticado numa geração antiga é recusado no registro.
Novas decisões usam a política atual. Bytes de uma escrita iniciada antes da
barreira podem chegar depois; não há promessa de recolher dados já enviados.
A geração inicia em 1 após cada startup e aumenta em memória a cada sucesso;
não é um identificador persistente de versão do bundle.

## Sessões, retained e Will

A reconciliação remove sessões clean e assinaturas/fila offline/inflight outbound
sem permissão. Retained já aceito permanece armazenado, mas sua entrega exige ACL
atual do destinatário. Wills aceitos são consumidos uma vez no commit: um Will
permitido pela candidata é publicado para retained e filas persistentes; um Will
revogado é descartado. Conexões clean encerradas não recebem essas entregas.
Um Will QoS 0 não é enfileirado offline. Um limite de armazenamento excedido por
essa reconciliação recusa o reload sem publicar parcialmente a candidata.

Mensagens inbound QoS 2 aceitas antes de PUBREC mantêm a responsabilidade durável
mesmo se o usuário for removido. O usuário não pode reconectar até reativação;
após reativação, PUBREL pode concluir o fluxo sem perder ou duplicar a mensagem.
Essas sessões ficam dentro das quotas existentes e podem ocupar capacidade
indefinidamente enquanto o usuário permanecer removido. Não existe expiração ou
limpeza administrativa dessa responsabilidade nesta versão.
A referência de ownership é [OASIS MQTT 3.1.1, seção 4.3.3](https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html).

## Auditoria, rollback e evidência

Eventos de reload contêm resultado fixo e, em sucesso, geração. Não incluem
usuário, hash, caminho privado, tópico, payload ou senha. Os testes verificam
logs de processos isolados. Nenhuma credencial ou configuração real foi alterada.

Para rollback de política, restaure um bundle privado anterior e sinalize a
instância; isso também encerra conexões. Voltar ao binário 0.7 exige remover
`MQTT_SECURITY_BUNDLE`, restaurar configuração legada e usar backup verificado
para estado/configuração. Não há conversão automática de credenciais. Documento
MQTT v2 (leitura v1), WAL/snapshot v1 e quotas continuam iguais.

As fixtures em `scripts/verify_dynamic_security.py` verificam autenticação/ACL,
reload inválido, revogação, retained/offline, Will, startup, recuperação QoS 2 e
logs. O exemplo `p44_security_fixture` gera somente um hash de senha pública para
esses testes; não é um utilitário de produção. Ver
[registro P44](../../prompts/registros/P44-0.8.0.md) para comandos e resultados.
TLS/mTLS externo, Mosquitto, falhas de energia e segurança de produção não são
declarados validados por essas fixtures.
