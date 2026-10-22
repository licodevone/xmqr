# P244 - Diagnostico da instalacao Windows real

Versao 1.1 - 21/10/2026. Usuario seguiu P243, relata ausencia de atalhos de
desktop e software sem funcionar. Nao resolver por nova ordem ou novo ZIP sem
evidencia. Snapshot Git broker 0fbe2dec3b8c6d4bb4da7f0a7180fba2498cdeed limpo;
preservar esse checkpoint e os pacotes anteriores.

Revisao1.1: Windows recusou RunAs do coletor com acesso negado antes de iniciar
processo. Preparar launcher unico explicito para operador executar como admin:
criar atalhos publicos solicitados apenas de componentes presentes, todos para
manager registrado, e executar coletor somenteleitura. Reparador separado do
coletor, sem sobrescrever atalhos existentes, sem controlar servicos ou mudar
credenciais/ACL. Fonteconcreta revisavel e resultado claramente pendente da
execucao pelo operador; nao tentar contornar a restricao da sessao.

Evidencia de entrada: imagem image(1).png mostra Broker/Client Falha na bandeja.
MSIs reais manager/broker/client terminaram0. HKLM e executaveis presentes e
hashes coincidem P242/P243; admin sem registro/arquivo/servico (sc1060).
Atalhos de menu dos tres presentes; desktopausente, XMQR_DESKTOP=0 nos3logs.
SCM query e logs privados negam acesso5 na sessao nao elevada. Templates de
broker exigemcertificados/users/ACL; client arguments=[] exigeprovisionamento.
Nao afirmar conteudo instaladoigualtemplate nemcausadefalha sem lerdiagnostico.

Objetivo: coletar status/codigos SCM, existencia de arquivos obrigatorios,
igualdade de hash com template e owner/DACL, sem conteudo de segredo. Diagnostico
administrativo somente leitura quando autorizado e possivel; nao iniciar/parar,
registrar/desinstalar, mudar permissoes ou substituir configuracoes do usuario.
Coletor limitadoconhecidos broker/client/admin, dadosdedicadospadrao. Ler apenas
mensagens fixas permitidas de service.log; ignorar linhas fora da allowlist.
Escrever relatorio somente em target/p244-diagnostic da mesma arvore de trabalho.
Pedir UAC para esse script concreto se necessario e permitido; se bloqueado,
registrar falha e entregar procedimento unico executavel pelo operador.

Escopo: script novo de coleta, registro e evidencia sanitizada, correcoes
necessarias e verificaveis de mensagens/preflight conforme resultado. Nao
relaxar mTLS, gerar credenciais de producao ou alterar servicos automaticamente.
Atalho so de software existente e com autorizacao; ausencia de selecao desktop
nao e falha de criacao. Propor configuracao inicial concreta apos diagnostico.

Aceite: diferenciar INSTALADO/CONFIGURACAO_PENDENTE/FALHA/ACESSO_NEGADO/AUSENTE;
relatorio sem senhas/chaves/payloads, parser PowerShell validado e execucao real
somente leitura, resultado e limites registrados. Sem commit/push/tag, semnova
versao de pacote apenas para ocultar falha. Manter registro do chat P240.
