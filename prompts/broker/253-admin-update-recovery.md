# P253 — Recuperação da atualização Admin P252

Versão 1.0, 2026-10-22. Base Broker 0fbe2dec, alterações P240-P252 preservadas.
Entrada: screenshot image(20261022-055409).png: Manager atualizado, Admin P252
falha após File.Replace em verificação de identidade da ACL; rollback exige
a mesma igualdade e é bloqueado. Backups e console/ foram preservados. Token
das ferramentas sem elevação, sem acesso à ACL ProgramData; SCM consultado
pela ferramenta não comprova estado real. Não declarar causa exata sem SDDL.

Objetivo: coletar metadados atuais/backup e, mediante guardas completas,
concluir atualização já aplicada iniciando somente Admin. Sem repetir P252,
reinstalar, trocar binários/config, alterar ACL existente, conta, certificado,
token, senha, usuário ou estado privado. Broker/Client/Manager intocados.

Arquivos: novo scripts/recover_windows_admin_p253.ps1; helpers/testes isolados
em target/p253-*; registro P253, chat e guia. Não modificar P252 existente nem
ZIP anterior nesta etapa; P252 fica marcado como não reaplicável após falha.

CLI: padrão diagnóstico somente leitura, opção -Resume validada para operador
PowerShell7.5+64bit elevado. Guardas de caminhos absolutos sem reparse, registro
64bit e conta/ImagePath Admin, manifesto/hashes A28 conhecidos e identidade
dos backups. Varredura limitada a pastas p252-backup-GUID, exatamente um par
reconhecido; não escolher por data. Não executar candidato desconhecido.

Evidência sem abrir segredos: SDDL/owner/group/protection/ACE de admin/root,
config, console/perfis, pastas de backup e config anterior; hash binários
públicos, estado SCM e indicadores. Conteúdo da configuração não secreta pode
ser lido localmente para comparar exatamente AddConsole(backup)=atual e perfis
exatos esperados; não persistir/printar TOML ou sua cópia no relatório público.
Não abrir/hash/logar token, chaves, senha, users, certificados nem payload.

Aceitar para continuar somente mudança de metadados de proteção/herança na
configuração com owner/grupo originais e exatos grants CommonAllow SY/BA FA,
LS ReadAndExecute normalizado, sem ACE extra/negação/callback/flags perigosas.
Comparar grants com backup original seguro e root protegido verificado.
Se leitura LS faltar, owner/grupo divergir ou grants/bytes/perfis não forem
reconhecidos, recusar sem SCM/ACL writes e deixar relatório para diagnóstico.
Sem relaxar guardas de segredos ou modificar qualquer ACL. Root/state não
sofrem setters. ACL metadados não são prova de bytes/configuração corretos.

Antes de SCM exigir todos preflights. -Resume: Admin apenas Stopped/Running,
sem dependentes ativos; Start apenas se Stopped, observar Running20s e HTTP
loopback status seguro sem tokens. Não autenticar usuário nem PUB automático.
Relatório em target/p253-diagnostic, arquivo novo único/CreateNew, sem conteúdo
privado. Registrar também recusas/falhas e caminho de relatório para operador.

Validação: parser, fixtures de políticas privado/herdado/transição com
negativos owner/grupo/ACE/LS/flags e pares ambíguos, conteúdo/config/perfis,
hash guard e prova de recusas antes de SCM por doubles. Prova Windows real
Replace isolada quando possível sem exigir SYSTEM; reconhecer limite do token.
Execução instalada só operador; não alegar elevação/recuperação já executada.
Agentes paralelos por solicitação vigente, ownership separado de arquivos.

## Revisao 1.1 - representacao redundante e backup privado

Antes da implementacao, admitir no admin.toml atual ate8ACECommonAllow,
flags apenas0/Inherited16, somenteSY/BA FullControl2032127 e LS
ReadAndExecute1179817. Duplicatas desses grants exatos sao redundantes e
podem resultar do merge; nenhumaSID/tipo/mask adicional e aceita. Exigir
presencaSY/BA/LS e owner/grupo exatamenteiguais ao backuporiginalseguro;
ignorar apenasProtected/Inherited como representacao nessa configuracao.
Backupconfig nao e consumido pelo servico: permitir ausenciaLS, mantendo
SY/BAFA e owner/grupo originais reconhecidos e zeroextragrants. Root/console
continuam protegidos com politicas privadasexatas. Perfis exigemLSRX.
Escopo permanece diagnostico/resume semsetterACL/config/binario. Relatorio
snapshotCreateNew antecedepreflight quando possivel, e resultadoCreateNew
separado registra recusas. Varredura max16pastas porroot e parunico, semdatas.