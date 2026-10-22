# P247 - Configuracao inicial local Windows

Prompt: broker/247-windows-local-initial-setup.md v1.2. Data local21/10/2026.
Windows x64, PowerShell7.6.7/.NET10.0.13. Base0fbe2dec preservada, sem
commit/push/tag/versao/novo MSI. Alteracoes P244-P246 locais preservadas.

## Causa comprovada

Coletor administrativo do operador: target/p244-diagnostic/installed-diagnostics.json,
CreatedUtc2026-10-22T00:08:13.7062897Z. Tres componentes instalados com
executaveis presentes e modelos TOML inalterados. Broker sem ca/servercert/key,
users.toml e acl.toml; Client arguments=[]; Admin sem state/token. Log do
Broker registra required file or directory missing. Client/Admin1077 atuais
indicam nenhum inicio desdeboot, nao um diagnostico causal adicional.
O Erro1 mostrado nas tentativas e generico; este relatorio comprovou a
configuracao inicial ausente. Reinstalar os mesmos MSIs nao a cria.

## Implementacao

- tools/windows-password-hash: crate/lock independentes, stdin32..1024bytes,
  semargumentos, Argon2id v19 m19456/t2/p1/output32 salt16CSPRNG, zeroization.
- scripts/windows_bootstrap_crypto.psm1: CA3072/2anos, folhas2048/1ano,
  SANlocalhost/127.0.0.1, EKUs separados, chaves/seriais/senha exclusivas,
  stdinprivado UTF8semBOM, arquivoscreate-new com DACLprivada na criacao.
- scripts/initialize_windows_local.ps1: PS7.5+, Windows64/admin instalado,
  registros/defaultImagePath exatos, nao-reparse, modelosinalterados, destinos
  novos/dirs certificados/clientstate/adminstate vazios; recusa customizacao.
  Stagingprivado semLS, dados do servico com ownerBA e SY/BA/LS restritos;
  Client persistentesub topico local, saida8MiB; token-init nativoAdmin.
  Backup/reversao de arquivos proprios e ACLs, sem apagar arquivos alterados
  externamente. StartServices opcional e ordenado. Resultado parcial sem
  segredos mesmo quando inicio falhar; nao anuncia runtimeaceito pelo preparo.
- docs/windows-local-initial-setup.md: comando concreto para operador;
  painel/conta inicial, limites de validade/saida e diagnostico posterior.

Agentes paralelos: helper, criptografia e revisao independente. Revisao
conferiu registro/ImagePath reais somente leitura, corrigidos Contains frouxo,
checagem de configreparse, rollback e relatorio parcial. Nenhuma mutacao SCM,
MSI, certificado global ou arquivos instalados pela sessao de desenvolvimento.

## Verificacoes reais

- Helper: cargo fmt PASS; cargo test --locked --offline 5/5 PASS;
  cargo clippy --locked --offline --all-targets -- -Dwarnings PASS;
  cargo build --locked --offline --release PASS.
  EXE208896bytes, SHA256bd1953e3822a6fabd4d6b7f25bd146263ce16bc9abd6c4e592a2c70b3d053e25.
- PowerShell parser dos dois scripts PASS; importmodulo PASS.
- Teste criptografico em memoria17/17 PASS: SAN/EKU, RSA/SHA256, chaves
  distintas/compativeis, seriais, validade, WindowsX509Chain CustomRootTrust
  com unicaCAefemera e ApplicationPolicy correta; helperstdin duas vezes
  mesma senha CSPRNG, perfilcorreto/saisdistintos. Nenhum segredo gravado.
- Negativo modo instalado semadmin: guardrecusou antes de importar modulo,
  alterar arquivos ou chamar SCM (exit1 esperado).
- PrepareOnly01: SetAcl pediu SeSecurityPrivilege; revisado prompt1.1,
  trocado por FileSystemAclExtensions.SetAccessControl (Owner/DACL, semSACL).
  PrepareOnly02 tambem recusou WriteDac (Unauthorized). Token restrito de
  sandbox tem Modify, nao consegue aplicar DACLprivada. Prompt1.2 documenta
  BLOCKED; nao adicionar SIDs amplos ou relaxar DACL para contornar.
  Restaram somente dois diretorios de teste vazios sob target; sem segredos.
- git -c core.safecrlf=false diff --check PASS antes da entrega final.

## Gates pendentes

Criacao/aplicacao completa de arquivos/ACL e prova nativa integrada do novo
inicializador: BLOCKED pelo token. Inicio/parada/reinicio/reboot dos tres
servicos sob LocalService: PENDING operadoradministrador. Parser/revisao e
testes em memoria nao provam esses gates. Nenhum servico real declarado
funcionando. Entrega por comando usando fonte/helper no projeto ja existente;
nao ha pacote novo para instalar nem necessidade de desinstalar as versoes atuais.

## Correcao apos tentativa administrativa - prompt v1.4

Operador executou inicializador elevado: falha linha71 na checagem privada.
Captura posterior de bootstrap mostra ownerBA, protectedTrue, D:PAI com
somente SY/BA FullControl OICI. Falha reproduzida na comparacao textual:
descriptor persistido incluiAI, embora regras e owner estejam corretos.

Durante duas interacoes exec-server/apply_patch estavam bloqueados por
file:///workspace invalido no Windows; nao houve alteracoes nesse periodo.
Reabertura do desktop restabeleceu leitura/escrita do projeto. whoami /priv
continua token restrito sem elevacao; GetAcl ProgramData/bootstrap negado.
Nao alegar que abrir aplicativo como admin elevou ferramentas automaticamente.

Adicionado scripts/windows_private_acl.psm1: compara owner e DACL protegida,
exige mesma lista normalizada de regras allow SID/mask/flags em descriptors
raw; rejeita callback/object/opaque/deny, regras extras e DACL nula/vazia.
Ignora somente metadados de descriptor AI/grupo, nao flags de heranca em ACEs.
Inicializador usa modulo na verificacao apos aplicar e na validacao somente
leitura de bootstrap existente; nao remove/reset bootstrap para contornar erro.

Novo scripts/verify_windows_private_acl.ps1: 19/19 PASS em memoria no Windows.
Reproducao literal do SDDL enviado, ordem equivalente, owner errado,
protecao ausente, Everyone/AU/LocalService extras, direitos reduzidos/extra
escritaLS, deny, heranca/propagacao divergente, nula/vazia. Primeiro teste
de duplicata identica tinha expectativa incorreta: .NET consolida ao importar
SDDL. Prompt1.4 revisado antes do ajuste; politica consolidada equivalente
aceita, privilegio extra continua rejeitado. Nenhuma DACL real alterada.
Agente independente revisou integracao/modulo e repetiu19/19 PASS.

Parser de inicializador/modulos/teste PASS. Nenhuma alteracao Rust/versao/MSI.
Gates nativo completo/SCM permanecem pendentes do operador. Proxima acao:
repetir comando inicializador -StartServices na janela PowerShell elevada,
sem reinstalar, sem apagar bootstrap nem dados existentes. Historico das
interacoes nao gravadas durante bloqueio foi recuperado nesta retomada.

## Correcao de File.Replace apos avanco administrativo - prompt v1.5

Captura image(10).png mostra primeiro guard26 por ausencia de elevacao.
Nova captura image(20261022-014834).png, arquivo exato referenciado pelo
operador, mostra Administrador:PowerShell e falha na linha217 File.Replace:
The path is empty (Parameter path). Leitura dessas imagens autorizadas
comprovou avanco alem da geracao/aplicacao inicial de credenciais/ACLs.
Nao houve tentativa de StartServices antes desse ponto. A captura nao
substitui verificacao independente de rollback/estado final do host.

Funcao Replace-XmqrClientConfig agora recebe backup explicito e novo no
staging privado client.toml.replaced; valida backup ausente e hash atual do
destino. Backup client.toml.before e rollback anteriores preservados. Sem
parametro string $null, que o binderPowerShell converte em string vazia.

Novo verify_windows_config_replacement.ps1 carrega SOMENTE funcao real da
AST do inicializador, sem executar corpo de provisionamento/SCM, e cria
arquivos nao secretos sob target/p247-replace-GUID. 17/17 PASS: erro antigo
reproduzido, destino/fonte preservados na rejeicao, substituicao e backup
corretos, fonte consumida, recuperacao apos falha posterior, backup existente
recusado/preservado, config personalizada recusada/preservada, parametro
backup vazio recusado. Sem ACL/credenciais/estado/servicos instalados alterados.
Necessario repetir comando inicializador na janela administrativa do
operador; nao repetir instalacao nem apagar arquivos existentes. Inicio SCM
dos tres ainda nao comprovado.

Revisao independente identificou hash derivado de backup tardio no fluxo
principal. Prompt1.6 preparado antes do ajuste: hash aprovado agora fixado
no preflight dos modelos, cliente revalidado antes de copiar backup, backup
comparado ao valor aprovado e troca recebe somente esse valor fixado.
Mais tres asserts de regressao para mudanca durante preparacao/backup tardio:
total20/20 PASS. Suite de permissoes19/19 repetida PASS. Revisao independente
confirmou a integracao. Parser/diffcheck PASS. Sem mutacoes do host.

Limitacao de concorrencia ja existente: se outro administrador alterar a
configuracao aplicada durante uma falha posterior, rollback preserva esse
arquivo pelo hash, mas ainda pode remover credenciais novas do inicializador.
Nao exercitado no host; esta entrega nao anuncia rollback concorrente integral.

## Operador concluiu preparo e inicio - 21/10/2026

target/p247-setup-result.json CreatedUtc2026-10-22T02:04:52.9208814Z:
FilesPrepared/StartRequested/StartupSucceeded true, Broker/Client/Admin
Running. Captura image(20261022-020528).png confirma mesma saida. Assim,
preparo administrativo e inicio inicial dos tres foram comprovados.
Leituras HTTP reais pelo agente: Broker /health200ok, /ready200ready;
Admin /api/auth/config200 modeusers/setup_requiredtrue. /healthz foi uma
sondagem de rota inexistente404, corrigida para rotas reais verificadas no
codigo, sem mudar o host. SCM/CIM/processos do host nao consultaveis pelo
token restrito; nao interpretar resultados filtrados como desinstalacao.

Verificacao posterior: connections_total1/sessions1/connections_active0,
sem rejeicoes de autenticacao/ACL. Source Client aplica90s idle de aplicacao
tambem no servico, mesmo com PINGRESP; C152/P248 corrigem essa politica para
runtime persistente. Portanto snapshot inicial Running nao prova sustentacao
do Client. Nao rerodar P247 nem regenerar credenciais; dados ja preparados.
