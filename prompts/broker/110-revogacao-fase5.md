# P110 rev1 — aceite cruzado A02/A03 da política dinâmica

2026-10-15. Entrada broker `9b4b9fe` mais P109 local, admin `3253c72`
mais A08 rev5 local. Editor de papéis/grupos/ACL offline e reload online
existem, mas A02/A03 globais ainda não receberam prova cruzada suficiente.

Em recursos temporários, iniciar broker acl-lab com bundle privado e socket
admin. Criar cliente MQTT conectado com QoS2 inbound aceito e manter PUBREL
pendente. Editar/desabilitar usuário via CLI do admin ou alterar bundle
privado validado, aplicar `channel reload` com hash/CAS, comprovar que conexão
é encerrada e nova autenticação falha. Reabrir broker, confirmar inbound QoS2
durável e recibo de reload. Para A02, criar/alterar role/group/ACL via editor,
aplicar e provar concessão/negação de publicação ou assinatura no wire.

Não usar serviço/estado real. Não imprimir senha/hash em logs; fixtures têm
credenciais públicas de teste. Negativos: referência inválida preserva bundle,
viewer não aplica, geração obsoleta/arquivo alterado não revogam. Gates Rust,
integração Linux/WSL e matriz atualizada conforme evidência. Não extrapolar
acl-lab para mTLS físico ou produção.
