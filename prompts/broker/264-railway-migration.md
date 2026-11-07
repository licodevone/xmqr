# P264 v1 — Migrar Broker XMQR e subscriber para Railway

## Estado de entrada

Oracle Ubuntu 26.04, instância Always Free `xmqr`, permanece RUNNING. Inventário SSH somente leitura confirmou `xmqr-broker` 0.43.0 (systemd, TCP TLS/mTLS público 8883, monitor loopback 9090, estado em WAL/snapshot), `xmqr-admin` 0.11.0 independente como observer local e `mqtt-client` 0.43.0 como subscriber systemd para `xmqr/health`. Client credentials/certificados e ACL existem no host. Manager não está instalado como serviço Linux nesta VM; o Manager Windows é ferramenta local. Railway atual contém apenas XMQR Platform API + Postgres.

## Objetivo

Implantar broker e subscriber como serviços Railway distintos, transferir o estado persistente e configuração/certificados necessários sem expor segredos, validar TCP/TLS/mTLS e clientes antes de qualquer corte. Manter Admin/Manager como ferramentas operacionais locais e configurá-las para o novo endpoint depois de emitido.

## Escopo

- Railway: serviço Docker para broker XMQR, volume persistente para estado, proxy TCP público na porta MQTT; serviço separado para subscriber XMQR existente se tecnicamente necessário.
- Preservar imagem/versão, ACL, CA, identidade e estado MQTT. TLS/SAN deve validar o endpoint Railway; mTLS e ACL deny-by-default permanecem ativos.
- Planejar transferência de estado com processo de backup consistente e rollback. Oracle fica ligada até o usuário aprovar corte e aceite ponta a ponta.
- Não alterar/excluir instância Oracle, dados ou certificados; não publicar credenciais, chaves, senha, conteúdo de env ou payload em logs/repositório.
- Client desktop/CLI, Admin observer e Manager permanecem em seus repositórios separados; não transformar interfaces locais em daemons Railway sem arquitetura aprovada.

## Aceite

- Railway broker deployment SUCCESS/RUNNING, TCP proxy acessível, validação TLS/SAN e mTLS passando.
- Estado, usuários e ACL verificados; pub/sub com cliente e Admin compatíveis; subscriber inicia e consome após cutover coordenado.
- Backups privados preservados e rollback operacional documentado.
- Nenhuma indisponibilidade permanente na plataforma ou Oracle antes da aceitação.

## Validação

Gates Rust/documentação conforme `AGENTS.md`, interoperabilidade MQTT com TLS/mTLS, health/monitor, persistência após restart Railway e teste dos executáveis Client/Admin/Manager. Registrar PASS/FAIL/BLOCKED por evidência observada; não declarar migração concluída antes dos testes.
