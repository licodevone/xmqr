# P252 — Manager X legível e console Windows

Versão1.0, 22/10/2026. Base0fbe2dec, locaisP240–P251 preservados.
Entrada: usuário solicita trocar Manager por símboloX das imagens051332/051441,
maior na bandeja, verde online/apagado offline, e iniciar console web. P251
aceito pelo operador120s, Broker/AdminHTTP200 e1conexão; consoleAdmin desativado.

Objetivos: X sem palavras nem bolinha de status, desenho ocupando área útil do
ícone (Windows determina tamanho físico da bandeja); verde apenas todos os
serviços instalados Running, demais estados desaturados/apagados. Preservar
menus, avisos, UAC e esconder completamente sem softwares instalados. Manter
texto distinguindo estadoSCM de saúdeMQTT; não prometer conexão pela cor.

ConsoleA28: prover configuração explícita durável por TOML de serviçoAdmin,
executávelClient e perfis PUB/SUB privados mTLS para Brokerlocal8883; clientIDs
próprios, sem alterar Clientserviço, contasweb, token, certificados, senha ou ACL
existentes. Novos perfis só referências a caminhos privados, não segredosinline.
Nada de variáveis globais permanentes ou enfraquecimento de validações.

Escopo principal: tools/windows-manager fontes/assets/build.rs; iconeManager
packaging/windows; script/artefatos de atualização in-place com backup/hashes;
documentos/registrosP252 e chat. Admin separadoA28 sob promptpróprio. Visual
seguirá imagem anexada; usar ferramenta de imagem para edição pedida. ICO e
RGBA gerados como empacotamento de imagem aprovada, sem redesenhar viaPython.

Validação: Managerfmt/test/clippy/buildWindows; imagemXpresente em verde/apagado,
sem texto/badge e com pouca margem; icone incorporado durante link nativo,
somente auditoriaread-only depois. Atualizadores parseados/guardas testadas em
fixtures, guardas de conta/caminhos/reparse e backupCreateNew; somente execução
administrativa pelo operador se token das ferramentas continuar nãoelevado.
Console: testesA28 + ensaioisolado quando possível, comprovação instalada via
operador e navegador sem exibirtoken/senha/payloadprivado.

Sem desinstalar/MSI/commit/push/tag/versão/release ou ACLreset. Parar/reabrir
somenteManager na atualização; reiniciar somenteAdmin para console quando
aplicado pelo operador. Broker e Clientserviço devem permanecer funcionando.
Agentes emparalelo conforme pedido vigente, arquivos com responsáveis distintos.

### P252 - revisao de validacao dos helpers (agente packaging)

Em 22/10/2026, antes da correcao: parser dos dois scripts PASS. Prova .NET
em memoria mostrou que FileSystemAccessRule Allow(ReadAndExecute) normaliza
Synchronize: mascara1179817, enquanto enum ReadAndExecute isolado131241.
O validador privado deve comparar mascara normalizada1179817, mantendo
LS somente leitura/execucao. Revisao sem alteracao de ACL instalada.
A comparacao semantica de ACE deve usar GenericAce.GetBinaryForm(buffer,0),
API real, preservando owner/protection/flags/tipo/mask/SID e ignorando so
metadados AI/group. Provar negativos e politica gerada em memoria antes
entregar. Escopo dos scripts e author/header do prompt preservados.

### P252 - configuracao Admin herdada confirmada no P250

Revisao antes do ajuste: evidencia P250 confirma admin/root ownerSYSTEM,
DACLprotegida apenasSY/BA FullControl e LS ReadAndExecute; admin.toml tem
ownerSYSTEM e os mesmos tres grants herdados, DACLnaoprotegida. O script
inicial recusaria esse arquivo legitimo. Autorizar somente para admin.toml
esse caso exato herdado com ownerSY/BA, tresACECommonAllow herdadas sem
flagsadicionais, mascaras exatas, apos verificar o parentrootprivado.
Nunca aplicarACL ao root nem normalizar/proteger arquivoexistente. Guardar
ACLoriginal e exigir igualdade semantica apos File.Replace/rollback.
Stagingconfig tem ACLprivadaprotegidaBA/SY; ReplaceFile deve preservarDACL
do destino, incluindo heranca. Provar replace real em fixtureWindows com
Get-Acl antes/depois, e negativos do caso herdado em memoria, semhostupdate.

### P252 - leitura LocalService obrigatoria nos caminhos consumidos

Antes do ajuste, revisao independente apontou que politicaBA/SY somente,
valida para backup privado, nao basta para root/config/perfis/credenciais
consumidos por LocalService. Assert dos caminhos existentes deve exigir
ACE LS ReadAndExecute exata alem de SY/BA FullControl; sem modificarACL.
O construtor generico BA/SY semLS permanece somente no staging/backupnovo.

### P252 - preservacao owner/grupo SYSTEM via escopo de privilegio

Aprovado pelo coordenador antes de implementar: ReplaceFile documentaDACL,
mas nao garante owner/grupo. Habilitar SeRestorePrivilege temporariamente
somente no processo PowerShell elevado do operador, guardando estadoanterior
e restaurando-o em finally. Falha na aquisicao ocorre antes de pararAdmin
ou criararquivos. Criar stagingconfig com owner/grupo originais eDACLprivada
protegida BA/SY; File.Replace preservaDACLoriginal do destino e a verificacao
exige owner/grupo/DACL/protecao originais, inclusive herancaexataP250.
Nenhum setter emACLinstalada/root/state. Semhabilitarprivilegios no agente;
testes semadmin cobrem parser/interopcompile/politicas/hash/replacegenerico,
limiteownerSYSTEM comprivilegio fica explicitamente NOT_RUN aqui.

### P252 - ACL padrao de binarios Program Files

Antes da correcao, leitura somente metadados em ProgramFiles/XMQR confirmou
Manager/Admin ownerSYSTEM e grantsWindows padrao para TrustedInstaller
(SID S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464).
Guarda SY/BA exclusiva recusaria esses diretorios legitimos. Somente guarda
de binarios/diretorios ProgramFiles admite esse SID exato, alemSY/BA;
politicas privadas Admin/console/credenciais continuam somenteSY/BA/LSRX.
Reconhecer tambem GenericWrite/GenericAll e admitir CREATOROWNER apenas
ACEInheritOnly com OI+CI em diretorio, nunca grant efetivo ao arquivo.
Nenhuma ACL instalada e alterada; manter negativos de escritores amplos.
