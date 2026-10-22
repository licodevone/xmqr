# P251 — Reparo restrito da pasta client-default

## Revisão1.1 — preservar owner/grupo e conter propagação

Revisão antes de aplicar: clone SetSecurityDescriptorBinaryForm serve somente
para comparação, pois persistência pode marcar owner/grupo modificados. Aplicar
remoção em Get-Acl fresco, alterando só DACL. ACL raw também deve conter somente
CommonAceAllow sem callback/opaque e igual quantidade de regras enumeradas.
Mudanças OI/CI podem propagar pelo Windows: exigir DACL protegida de TODOS os
filhos diretos, sem reparse, antes de escrever; guardar metadados e conferir
iguais depois. Não seguir ou reconfigurar filhos. Guardar grupo da pasta também.
Primeiro fixture de negativos PowerShell foi agrupado incorretamente e produziu
somente3checks; corrigir criação dos casos, repetir e registrar contagem real.

Versão1.0, 22/10/2026. Prompt apresentado antes da implementação.
Entrada: relatório04:27:53UTC P250: ClientStoppedExit1, últimas tentativas
accessdenied; pasta client-default ownerSYSTEM/DACLprotegida e quatro ACEs:
SYSTEMFA,LocalServiceRX,AdministratorsFA,operadorSID1001FA. Client.toml e sink
têm ACLs privadas; sink vazio. Broker/AdminStoppedExit0, sem listeners.

Causa suficiente confirmada por revisão independente: service_config::load
valida parent imediato; LocalService rejeita ACE ao usuário1001. Não atribuir
origem da permissão ao operador, Explorer, antivírus ou roteiro sem evidência.

Objetivo: script administrativo de operador que remove somente ACE explícita
FullControl OI/CI do usuário atual na pasta padrão, sob guardas exatas. Preservar
ownerSYSTEM, grupo, DACLprotegida e três regras existentes de sistema/serviço.
Guardar SDDL anterior em relatório workspace; sem recursão e sem tocar arquivos
filhos, configs, tokens, senha, certificados, sink ou validadoresRust.

Escopo: scripts/repair_windows_client_directory_acl.ps1, registroP251, docs de
teste e chat. Sem alteração ao executável instalado. Guardar caminhos locais
sem reparse, conta/imagem SCM padrão, Client parado, estrutura ACL exata.
Recusar regra diferente/inherited/deny/outroSID/owner. Estado já corrigido é
idempotente. -StartServices opt-in inicia Broker, espera readinessHTTP200,
inicia Client/Admin existentes e observa120s. Não parar ou reiniciar serviços.
Falha posterior mantém ACL privada corrigida, sem restaurar regra inadequada.

Aceite: parserPASS, helperACL com positivos/negativos em memória sem host;
revisão independente; nenhum segredo no backup/log; aplicação real depende
do operador elevado porque ferramentas são nãoadmin. Não instalar nem alterar
ACL automaticamente; apresentar comando exato após validar script. Estado
instalado120s e ausência de erros posteriores permanecem pendentes.
Sem commit/push/tag/release.
