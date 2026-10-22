# P251 — reparo restrito preparado

Prompt251v1.0 apresentado e revisado1.1 antes de correções da implementação.
Base/alterações locais preservadas. RelatórioP25004:27:53UTC estabelece
ClientStoppedexit1/accessdenied, parentclient-default com ACE explícitaFA ao
operadorSID1001. Revisão independente confirma rejeição no parent antes de
abrirclient.toml: LocalService só admite SYSTEM/BA/LocalService/currentSID.
Sink0bytes e ACLs próprias privadas. Broker/AdminStoppedExit0 sem listeners.
Não há evidência de autoria/origem da ACE adicional. Outros erros posteriores
não descartados até aplicar reparo.

Scriptrepair_windows_client_directory_acl.ps1 criado para operador elevado.
Guardas: conta/imagemClient padrão,Clientparado,localpathsemreparse,ownerSYSTEM,
DACLprotegida,trêsACEsmasks/flags exatos e somente possívelextraFullControlao
usuáriocorrente; rawCommonAceAllow semcallback/opaque. Negativosrecusamoutros.
BackupSDDLCreateNew no target; aplicação emGetAclfresco remove regra específica
sóaccessdirty, preserveowner/grupo. Filhosdiretos precisamprotectedsemreparse;
snapshotSDDL antes/depois. Nenhumwritefilho/chave/config/sink/dados.
StartServices optin: iniciaBrokersemparar,HTTPready200 limitado,Client/Admin,
consulta estados por120s com progresso20s. Falha mantém ACL privada corrigida.

Validações: primeiro fixturePowerShell agrupou negativos errado:3checks;
prompt1.1 antes de corrigirfixture. Rodada final8checks emmemóriaPASS (positivo,
idempotência e seisnegativos); comparaçãoexatapolíticaPASS; parserfinalPASS.
Nenhuma aplicação de ACLSYSTEM/SCMreal pelo agente. Técnicadepersistência no
host e restriçõesdeacessoelevado continuam dependentes do operador.
Revisão independente encontrou risco de owner/groupdirty no clone e propagação
OI/CI parafilhos; ambos tratados por aplicaçãoemACLfresca, guardasfilhos/group.
Guiaoriginal e cópiaraiz atualizados,14blocosparserPASS e hashesiguais.
Semcommit/push/tag/release/executávelnovo/instalação; nenhumserviçoalterado.

PENDING: aplicação pelo operador e resultado120s. Se recusarprecondições ou
falharposteriormente, coletarP250 e tratar causaconcreta, semresetreinstalação.


## Aplicação instalada confirmada pelo operador

22/10/2026: captura inline do PowerShell confirma remoção de regra pessoal,
backupSDDL target/p251-acl-before-225b6ab75c084a248ec330d9578d7d82.json,
ACLprivadaconfirmada/nenhumfilhoalterado e trêsRunning0/20/40/60/80/100/120s;
mensagem reparoconcluido/observacaoaprovada. Segunda capturaManager mostra
Admin/Broker/Client Emexecução. Aceiteaplicação120s PASS operador.
Consultasreadonlyagente subsequentes: health200/ready200/authconfig200,
connectionsactive1,total1. Não prova entregaaplicação; publicaçãoP249§8 pendente.
UI guarda resultadoúltimaação emapp.message atépróximaação/sair; refreshsnapshot
não limpa avisoanterior. Orientado sair somenteManager/reabrir, sempararserviços.
OrigemACE e cicloSCMcompleto/rebootapósreparo não provados nesta confirmação.

