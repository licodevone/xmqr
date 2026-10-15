# P97 rev1 — B10: TLS com senha e ACL, sem certificado de cliente

2026-10-15. Entrada `beabcbb2ff3aa4e0cf471400e708280c0621722c`,
`v0.12.0`, árvore limpa e prerelease publicada. Pedido do mantenedor: concluir
a fase 4, com prompt antes da funcionalidade e GitHub atualizado.

Objetivo: modo explícito `tls-password` que valida certificado do servidor no
client, transporta CONNECT com usuário/senha por TLS e aplica ACL deny-by-default,
sem solicitar nem aceitar certificado de cliente. `secure-mtls` continua padrão.

Escopo: configuração, inicialização, transporte e política de autenticação do
broker; client C48 em repositório próprio; testes de configuração, autenticação e
integração TLS; documentação, plano e registro. Sem alterar codec, formatos de
estado, quotas, QoS, retenção ou configuração de endpoints adicionais B09.

Contrato: `MQTT_SERVER_CERT`/`MQTT_SERVER_KEY` obrigatórios;
`MQTT_CLIENT_CA`/`MQTT_CLIENT_CRL` recusados neste modo; usuários e ACL
obrigatórios por arquivos ou bundle dinâmico, com separação de perfil de estado.
Não reutilizar `password-lab` na rede; suas credenciais ficam em TLS. Nunca
enviar senha em argumentos, logs ou arquivos versionados. O client exige CA e
SAN/validade e rejeita cert/key neste modo. Falha de configuração impede bind.

Validação: gates Rust fmt/test/Clippy/build em Ubuntu 26, negativos de modo e
variáveis, senha/ACL/CA/SAN e client com certificado; integração MQTT QoS 0/1/2
usando estado/credenciais temporários. Registrar limites reais antes de tag.
Migração: opt-in; `secure-mtls` e clientes existentes não mudam. Rollback requer
restaurar configuração e diretório de estado compatíveis, sem conversão de WAL.
