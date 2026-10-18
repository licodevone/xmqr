# P228B v1.6 — QA isolado dos artefatos broker0.43.0

Preparado em2026-10-18 antes da autoria do harness. Complementa P228v1.1;
owner não altera runtime/manifests/CI nem o registro global P228 do coordenador.
Fonte de build: ba6ef50204dec2c6385b272e595260b9def1e794, clone isolado em
.artifacts/p228-broker-release043/xmqr. HEAD/inputs rastreados ficam exatos;
somente harness/documentação próprios serão commitados em branch separada.

## Evidência e falha de infraestrutura já observadas

Contratos de distribuição6/6 e QA negativo de notices14/14 PASS nativos Windows.
Docker build runtime local, serialj1, coletou166pacotes/323textos originais,
mas foi cancelado antes de gerar imagem final por coordenação após pressão de
memória simultânea à release nativa. Fonte não mudou. Coletor independente
no WSL falhou OSError12 Cannot allocate memory em readinto de um texto no
destino parcial dist/notices-source. Não é licença rejeitada ou PASS parcial.

Só os PIDs validados docker-buildx52364/parentdocker6944, com linha exata
do build deste clone/tag, foram encerrados. Buildx k24z5q5xqcu0vleps4400xuty
confirma canceled/context canceled; export preservado em dist, SHA256
e81aae0f2050bb535f1ffe5d968ba5067be00beb0122ef3cd83f9951e90f83d0.
Uma consulta inicial usou ref com prefixos e não encontrou registro; ref curto
correto confirmou e exportou. Nenhum daemon/serviço/stack alheio, memória do
host, WSL ou cache compartilhado foi alterado. Não retomar builds pesados
até coordenador liberar; retry de coleta usará destino novo, nunca sobrescrever
o parcial. Não reduzir perfis Cargo ou suprimir erro para produzir artefato.

## Harness e aceite mínimo

Criar scripts/verify_p228_package_state16.py com stdlib, guardas root,
/.dockerenv, Ubuntu26amd64, flag explícita de ambiente e pacotes exatos.
Nunca executar instalação/remoção no host. Estado/configuração/segredo são
fixtures próprias dentro do container; nenhum dado de operador é lido.

1. Instalar .deb042 real (SHA publicado914d38e4...), verificar versões,
   unidade com systemd-analyze e ausência de autoenable. Criar retained e
   fila offline persistente por MQTT3.1.1 real com o binário instalado.
2. Parar broker e fazer backup15 com mqtt-admin042 real ANTES do upgrade.
   Validar snapshotCRC/envelope15, manifesto/hashes/modos privados do backup.
   Leitor da fixture segue formato binário existente, com limites explícitos;
   não fabricar estado nem alterar versões de documentos à mão.
3. Instalar .deb043 novo, verificar versões/unidade/config/secret/estado
   preservados. Abrir estado15 pelo broker043, consumir offline/retained,
   parar e comprovar documento16/watermark. Isso não é prova TLS ou energia.
4. Em CÓPIA privada do estado16, executar binário042 extraído e já conferido
   contra o pacote original: exigir recusa de formato16 e hashes snapshot/WAL
   inalterados. Jamais executar042 no diretório live migrado para16.
5. Downgrade de pacote042 preserva16/config/secret, não converte dados.
   Restaurar backup15 para destino NOVO e só então abrir por042, comprovando
   replay offline/retained real. Rejeitar restore para destino já existente.
6. Remove/purge preservam estado/segredo/conta; purge remove só conffile do
   pacote. Reportar versões/SHA/artifactsource e etapas sanitizadas; cleanup
   só processos e diretórios próprios, nenhum restart/serviço do host.

Preparar self-tests leves do leitor/guardas sem apt/Cargo/Dockerbuild e sem
anunciar ciclo executado antes de haver .deb043. Falhas reais exigem revisão
deste prompt antes do fix; preservar relatórios e não ajustar oráculo para verde.

## Imagens/pacote/publicação

Reusar Dockerfile fonte exata, j1, UID10001/caps-none/read-only/mTLS defaults,
MIT e textos originais sem normalização de terceiros. Coletor independente
de fonte locked, noticesQA, .debUbuntu26 e lifecycle precisam PASS. Binários
nativos serão fornecidos pelo coordenador com SHA para --skip-build; não
usar ELFBookworm no pacote Ubuntu. Não iniciar Cargo no target do original.

Nenhuma imagem Hub/tag/release/latest é publicada aqui sem aceite global6,
CI da fonte exata e A21/admin16. Registro próprio P228-distribution-artifacts.md,
separado do registro global. Não declarar fase6 encerrada por estes artefatos.

## Revisão1.1 — pacote oficial CI e barreira DISCONNECT

Self-tests leves do leitor3/3 PASS. Coordenador forneceu pacote OFICIAL da
fonte ba6/CI39140250983 PASS, SHA33b96f64f2e26f388f7878f2dd65e27271ab7113de65327dbdffdaffdfc268a5.
Copiado e hash conferido, sem instalar host. ELFs do pacote: broker
1ee611b082b5e8cb14bf881996ce314c391573353cf8971232728cb54a243207 e admin
3081297fb37431ef7f0c1f3110b753b54f1cd9c476b7386bfa9a63586cdf1ebf.
Podemos usar este pacote no lifecycle leve enquanto build nativo permanece
serializado; não recompilar nem reconstruir imagem antes da coordenação.

Antes da primeira campanha, reforçar fixture DISCONNECT: enviar pacote,
shutdown da escrita e aguardar EOF/reset do servidor antes de publicar para
a sessão offline. Isso dá barreira de término do handler, não sleep/race.
Negative042 usa porta válida livre numa CÓPIA16. Checar unit também após
downgrade. Esses ajustes não alteram broker nem bytes esperados MQTT.

## Revisão1.2 — FAIL da classificação de recusa do leitor042

Lifecycle1 preservado FAIL em `old_reader_refuses_v16`, após instalação042,
backup15 e upgrade043/replay passarem. O harness exigia texto de versão.
Fonte042 real desserializa Envelope/State `deny_unknown_fields` ANTES de
comparar a versão: watermark16 pode produzir `Malformed`, não o erro de
versão. Não modificar binário legado nem aceitar qualquer exit não-zero.

Antes de repetir, registrar código, classificação estática schema/versão e
SHAstdout/stderr (não conteúdo/payload/segredo); conferir hashes snapshot/WAL
independentemente da classificação. Aceitar exclusivamente recusa não-zero
com erro conhecido de schema/versão e zero mutação da cópia e live16. O
binário042 já é provado saudável pelo seed real15 no início do mesmo ciclo.
Adicionar também prova direta no documento15/backup: retained e sessão
persistente com fila offline exata, sem outbound, além do replay no wire.
Isso reforça a fixture sem fabricar estado ou mudar dados/código do broker.
Relatório novo separado; manter o primeiro FAIL e sua causa de harness.

## Revisão1.3 — FAIL de restauração open-lab sem marcador de perfil

Lifecycle2 preservado: negativo042 confirmou exit1/schema e hashes intactos;
rollback falhou no startup do destino restaurado. Backup/restore legado copia
somente snapshot/WAL, não `.mqtt-broker-profile`. `ensure_state_profile` recusa
open-lab em estado não marcado, tratando-o conservadoramente como secure-mtls.
Não alterar essa proteção nem substituir o perfil por valor inventado.

Antes do backup/upgrade, preservar bytes do marcador do diretório15 original
em metadado privado separado. No destino NOVO restaurado, provar primeiro
recusa específica de perfil sem marcador e snapshot/WAL intactos. Só então
restaurar bytes EXATOS do marcador original, modo0600/ownerxmqr, antes de
abrir com042 e verificar replay. Manifesto do backup continua estritamente
com seus três arquivos; não incluir metadado extra silenciosamente. Registrar
esta etapa de responsabilidade do operador, distinta do `state restore`;
o harness não afirma que o comando legado restaura marcador/credenciais.
Manter FAIL2 separado, report novo e zero alteração de runtime/pacote.

## Revisão1.4 — proveniência explícita sem constante autorreferente

Coordenador aprovou adaptação leve antes do patch: a fonte final da release
também conterá testes/prompts/CI, sem diferença nos inputs runtime ba6. Para
testar seu pacote CI exato, `--source` passa a ser SHA40 minúsculo EXPLÍCITO,
validado sintaticamente; relatório separa `runtime_checkpoint=ba6`. A flag
não é prova de proveniência: registro do coordenador deve vincular head_sha
do run GitHub PASS ao SHA do .deb e aos ELFs esperados fornecidos no comando.
Não resolver proveniência por igualdade de versão ou pelo texto do argumento.

Preservar pin do .deb042, nomes/versões/arquitetura dos pacotes e hashesELF
explícitos do043. Acrescentar self-tests leves de sintaxe SHA, sem build ou
instalação adicional. Commit separado desta mudança para cherry-pick antes
do congelamento final; build Docker atual d6 pode continuar e não é publicado.

## Revisão1.5 — integrar fonte final e repetir artefatos exatos

Nova autorização do coordenador: integrar main
`db472bc64558bf0e376a902b7780a259247c5149` somente nesta branch/clone.
Preservar commits623aeca/23c216 (proveniência explícita e evidências Docker),
que não estão na árvore db472bc. Comparação lida antes do merge confirma que
as três diferenças P228B são essas adições próprias; entradas runtime/Cargo/
Docker/notices/LICENCE equivalem a ba6. Preferir conteúdo próprio SOMENTE
nas colisões dessas três adições, não descartar trabalho geral do main.

CI padrão39164202189 consultada por API: completed/success/head_sha db472bc;
artefato12150137120 não expirado. Baixar pacote oficial em destino NOVO,
conferir sidecar, conteúdo, ELFsha/versões e vincular o run ao hash observado.
Rerodar lifecycle real completo com fonte db472bc, não meramente mudar flag.
Preservar os reports antigos e classificar qualquer novo FAIL antes de fix.

Rebuild Docker serialj1 com VCS_REF db472bc e inputs runtime comprovadamente
iguais, reaproveitando cache Cargo; referências locais novas sem substituir
candidatos anteriores. Repetir QA mTLS/WSS/admin/notices contra imagens finais.
Preparar exports e manifesto com revisão real db472bc apenas após os gates
locais: se `release_assets.py` exigir HEAD exato, alternar este clone LIMPO
temporariamente para db472bc, mantendo branch própria/commits preservados,
e retornar à branch depois. Conferir selected-inputs diff vazio antes disso.
Nenhuma alteração do original/main ou de serviços/estado do operador.

CI integrada39164217059 ainda em andamento nesta preparação. Publicação de
tags/Hub/release continua PROIBIDA até confirmação global do coordenador;
preparar/exportar localmente não equivale a publicar nem a fechar a fase6.

## Revisão1.6 — preservar aliases locais antes do export

Coordenador confirmou ownership dos aliases locais043 antigos fonte1574ab9.
Autorizou preservar seus IIDs exatos em aliases exclusivos
`xmqr-p228-preserved-broker:1574ab9` e `xmqr-p228-preserved-admin:1574ab9`
(se já existirem, exigir IID igual sem sobrescrever) e então atualizar SOMENTE
aliases DockerLOCAIS `lepinheiro100/xmqr-{broker,admin}:0.43.0` para db472bc.
Não fazer push ou alterar qualquer tag remota existente.

Primeiro launcher inlinePython falhou SyntaxError de quoting antes de
executar qualquer operação Docker. Preservar classificação como falha do
launcher, não de artefato; retry por driver PowerShell próprio no dist,
com strings literais, validação dos IIDs/revisão e checagem de cada exitcode.
O driver pode reconhecer alias já final com backup esperado para retry
idempotente, mas qualquer IID diferente causa recusa. Sem apagar imagens.
Depois, checkout LIMPO exato db para executar release_assets original;
branch própria mantém todos os prompts/evidências e será retomada após export.
