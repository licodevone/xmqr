# P247 - Configuracao inicial local segura dos servicos instalados

Versao 1.6 - 21/10/2026, America/Sao_Paulo.

Revisao independente identificou intervalo entre preflight e copia do backup:
derivar hash esperado desse backup tardio poderia aceitar customizacao feita
durante geracao criptografica. Fixar hash aprovado no preflight, conferir
novamente antes e apos copiar backup e usar somente esse hash na troca.
Preservar configuracao alterada nesse intervalo; testar tambem cenario de
backup tardio contendo alteracao enquanto hash aprovado permanece fixado.

Nova captura elevada image(20261022-014834).png comprova avanco ate linha217:
File.Replace recebeu $null no parametro string backup e PowerShell converteu
para caminho vazio, rejeitado pelo .NET. Corrigir usando caminho explicito
novo de backup atomico no staging privado, recusando backup existente e
revalidando hash do modelo imediatamente antes. Preservar backup anterior,
rollback e dados do operador. Testar a funcao real extraida da AST em arquivos
temporarios nao secretos: reproduzir falha anterior, substituicao/backup,
recuperacao, recusa de backup existente e de configuracao alterada. Sem SCM,
sem ACL/credenciais reais. Nao afirmar que elevacao/SCM ainda nao vistos passaram.

Teste inicial da regressao: dez casos passaram; caso de ACEidentica duplicada
falhou na expectativa de rejeicao porque FileSystemSecurity consolida regras
identicas ao importar SDDL (saida real ja tem somente duas regras). Ajustar
o teste para aceitar essa mesma politica normalizada e adicionar duplicata
com privilegio extra como negativo. Comparador continua exigindo igualdade
exata das regras efetivamente retornadas; nenhuma permissao e relaxada.

Falha real do operador: PowerShell7.6.7 elevado parou na linha71, verificacao
de permissoes privadas. Metadados enviados comprovam ownerBA, DACLprotegida,
duas regrasfull SY/BA e flagAI no descriptor. Comparacao textual de SDDL
recusou representacao valida. Corrigir por comparacao de owner/protecao e
multiconjunto exato de ACEs permitidas (SID/mask/flags), rejeitando DACLnula,
vazia, regrasextras, deny, callbacks e regras divergentes. Nao ignorar flags
nas ACEs nem ampliar permissoes. AI do descriptor e grupo primario nao
alteram as regras de acesso esperadas neste caso.

Adicionar modulo/testes isolados em memoria (reproducao literal da captura e
negativos de seguranca) e integrar verificacao ao inicializador. Reusar
bootstrap existente somente apos validacao rigorosa de permissoes privadas.
Nenhum arquivo de credencial, estado ou servico instalado sera alterado nos
testes. Desktop reaberto restabeleceu leitura/escrita no projeto; token das
ferramentas permanece restrito, leitura de ACL ProgramData ainda negada.
Nao anunciar elevacao das ferramentas nem funcionamento SCM sem evidencias.

Revisao apos primeiro PrepareOnly: Set-Acl sobre descriptor novo solicitou
SeSecurityPrivilege indisponivel no token nao elevado. Corrigir aplicacao
Owner/DACL por API .NET com secoes explicitas, sem SACL e sem reduzir acesso
privado; repetir somente em diretorio de teste novo. Nenhuma instalacao alterada.

Segundo PrepareOnly: API .NET tambem recusou WriteDac. Token sandbox tem somente
Modify via SIDs restritos e nao pode aplicar DACL privada; isso bloqueia prova
nativa deste inicializador nesta sessao, antes de gerar segredos. Nao enfraquecer
DACL, nao contornar sandbox e nao alegar prova operacional. Validar parser,
helper e revisao independente; entrega exige primeira execucao administrativa
do operador e diagnostico posterior. Usuario perguntou sobre desinstalar:
manter instalacao atual para aplicar configuracao, sem nova reinstalacao.

## Entrada e objetivo

Usuario instalou os candidatos, tentou iniciar os tres servicos (Erro1) e
executou coletor administrativo. Relatorio real target/p244-diagnostic/
installed-diagnostics.json, CreatedUtc2026-10-22T00:08:13Z, comprova modelos
inalterados: Broker sem CA/servercert/key/users/ACL; Client arguments=[];
Admin sem token. Servicos instalados como LocalService. P246 resolveu icons/
1077, nao fez provisionamento. HEAD0fbe2dec e P244-P246 locais preservados.

Objetivo: preparar uma correcao executavel pelo operador administrador para
instalacao LOCAL atual, mantendo secure-mtls, senhas fortes, ACL deny-by-default,
loopback127.0.0.1 e arquivos privados. Nenhuma credencial de teste/fixa.

## Escopo

- Helper Rust independente tools/windows-password-hash: stdin privado limitado,
  Argon2id perfil do broker, sal CSPRNG exclusivo. Nunca aceitar/exibir senha
  em argumentos/logs. Nao usar fixture P242 de sal fixo para usuarios reais.
- Modulo PowerShell para gerar CA local e identidades TLS unicas, fingerprint
  DER, usuario MQTT local com senha aleatoria, ACL de topico local restrito.
  CA/key privados apenas em staging protegido; sem certificate store global.
- Script inicializador PowerShell7/64-bit/admin, opcao PrepareOnly em diretorio
  privado novo para validacao nativa isolada; modo instalado aceita somente
  registros/caminhos dedicados padrao e servicos parados/modelos inalterados.
  Recusar configuracoes personalizadas e arquivos de credenciais existentes;
  nunca sobrescrever chave, usuarios, token, estado ou payloads do operador.
- Preflight completo antes de aplicar. Staging privado, configs de destino
  preparadas com caminhos corretos, copias de seguranca das configs-modelo;
  arquivos novos create-new, sem remocao recursiva/alteracao de ACL compartilhada.
  Owner/DACL SYSTEM/Administrators/LocalService conforme arquivo e diretorio;
  CA signing key excluida do acesso do servico.
- Client persistente sub mTLS do topico local, senha em arquivo, saida JSONL
  privada preexistente e limitada8MiB. Sem stdin/payload secreto em argumentos.
- Admin token nativo token-init; normalizar ACL para LocalService; users.json
  ausente e permitido, nao fabricar JSON vazio. Conta web criada depois por
  bootstrap autenticado local, sem senha padrao embutida.
- Inicio de servicos somente por opcao explicita StartServices apos arquivos
  validados, Broker antes do Client/Admin, aguardar/reportar status. Agente
  nao altera/inicia servicos reais do host por conta propria: entrega concreta
  para operador pois token desta sessao nao e elevado.

Arquivos: novos scripts/modulo/helper/docs/registro P247, chat. Sem alteracao
de protocolo, MSI/versoes, commit/push/tag/release. Nao adicionar nova rodada de
reinstalacao como tratamento para estes arquivos ausentes.

## Validacao e aceite

Hash helper: verificacao de senha, sais diferentes, entrada fora de limites;
fmt/tests/clippy/release locked. Scripts parseados. Preparacao isolada privada
com certificados/fingerprint/formatos corretos e provas de processo nativo
TLS MQTT mais Admin usando os executaveis P246 quando possivel, sem SCM/store.
Resultados de ACL/aplicacao SCM elevados somente apos execucao do operador;
marcar esses gates pendentes, nao anunciar servicos reais funcionando.
Entregar comando unico e instrucoes do painel sem expor segredo no chat/artefato.
