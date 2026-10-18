# P228B — artefatos e QA isolados broker0.43.0

Execução em2026-10-18 sob P228v1.1 e
[P228B](../broker/228b-distribuicao-isolada-estado16.md). Este registro é separado
do aceite global P228 do coordenador. Não declara encerramento da fase6.

## Fonte e ambiente

Clone isolado `.artifacts/p228-broker-release043/xmqr`, HEAD de build
`ba6ef50204dec2c6385b272e595260b9def1e794`, versão broker/legacyadmin0.43.0.
Inputs rastreados de runtime, Cargo e Docker permanecem sem alteração.
Harness/prompts/registro próprios não são inputs do Dockerfile allowlist.
Host Windows, Docker Desktop29.8.2; instalações somente em container próprio
Ubuntu26.04amd64. Não há instalação no host, mudança de serviço/firewall ou
leitura de credenciais do operador.

## Gates leves já executados

- `python scripts/test_distribution.py`: PASS6/6.
- `python scripts/test_phase3_notices.py`: PASS14/14.
- `python scripts/verify_p228_package_state16.py --self-test`: PASS3/3,
  leitor binário limitado, CRC/truncamento e entrada excessiva fail-closed.

## FAIL de infraestrutura e cancelamento coordenado

Coletor fonte locked independente falhou `OSError12: Cannot allocate memory`
em `hashlib.file_digest/readinto`; destino parcial `dist/notices-source`
preservado, não é inventário aceito nem licença rejeitada. Retry deve usar
destino novo. O build Docker runtime serialj1 deste clone teve coleta interna
166pacotes/323textos PASS e chegou à compilação final, mas NÃO produziu imagem.

Após falha ENOMEM simultânea da release nativa do coordenador, foram
encerrados apenas os processos próprios validados docker.exe6944 e filho
docker-buildx.exe52364, cuja linha continha o build/tag exclusivo P228.
Buildx `k24z5q5xqcu0vleps4400xuty` confirmou canceled/context canceled,
220,796661s,20/24etapas completas. Export preservado:
`dist/p228-build-cancelled.dockerbuild`, SHA256
`e81aae0f2050bb535f1ffe5d968ba5067be00beb0122ef3cd83f9951e90f83d0`.
Consulta inicial por ref com prefixos falhou `no record found`; ref curto
correto permitiu inspeção/export. Não houve prune, alteração de daemon/WSL,
perfil Cargo, recursos do host ou stacks alheias. Novos builds pesados
permanecem pausados por coordenação; nenhum PASS de imagem é inferido.

## Pacotes pinados para o lifecycle real

Baseline público broker0.42.0, fonte/tag
`24d219816fdac3e47115bcb2e59edd55b0c11407`, pacote
`xmqr-broker_0.42.0-1_amd64.deb`, SHA256 verificado:
`914d38e4fcd16b2d52a6a3e3e56710cc1371248976b9436c8b7570c04dc0e354`.

Novo pacote OFICIAL CI39140250983 da fonte ba6, fornecido pelo coordenador e
copiado para `dist/xmqr-broker_0.43.0-1_amd64.deb`:2.953.322bytes, SHA256
recomputado neste clone e igual ao sidecar verificado pelo coordenador:
`33b96f64f2e26f388f7878f2dd65e27271ab7113de65327dbdffdaffdfc268a5`.
ELFs esperados do mesmo pacote, conferidos durante a instalação isolada:

- broker:`1ee611b082b5e8cb14bf881996ce314c391573353cf8971232728cb54a243207`;
- legacyadmin:`3081297fb37431ef7f0c1f3110b753b54f1cd9c476b7386bfa9a63586cdf1ebf`.

CI integral Rust/package PASS é resultado coordenado da execução oficial,
não execução de Cargo deste clone. Artifactid12141242904; digest do ZIP não
foi recomputado aqui e não é apresentado como validado independentemente.

## Lifecycle e pendências

Execuções leves em containers exclusivos
`xmqr-p228-lifecycle-20261018-1`, Ubuntu26.04 local
`sha256:f144425ff09be612d6d9ad965196e9cdc23dae1f42110a8a11a3e9a8198759f7`,
limite768MiB/1CPU, sem portas publicadas. Source/artefatos read-only,
somente report próprio gravável. Guarda exige container/root/Ubuntu26/
amd64/opt-in e pacotes/fontes pinados.

`dist/qa-reports/p228-lifecycle-1.json`: FAIL preservado,6,9859s,
`old_reader_refuses_v16`; instalação042/backup15 e upgrade043/replay passaram.
Harness exigia texto UnsupportedVersion, mas leitor042 desserializa esquema
deny_unknown_fields antes de verificar versão. RevisãoP228B1.2 preservou
oráculo fail-closed e acrescentou classificação estática/hashes de saídas,
zero mutação independente e prova direta de retained/offline em documento15.

`dist/qa-reports/p228-lifecycle-2.json`: FAIL preservado,9,6001s,
`broker_startup_exit` no destino rollback. Negativo042 anterior PASS com
exit1/schema; snapshot/WAL da cópia16 e live16 idênticos. SHAstderr
`c6adccb87cab726bf8007dd72cb47f3ded0688e1ed08f8df6ea2e1ec4b3e296b`;
stdout vazio. Backup/restore legado não inclui `.mqtt-broker-profile`, e a
proteção de startup open-lab recusa estado restaurado sem marcador. Revisão
P228B1.3 prepara negativo específico dessa proteção e restauração separada
dos bytes EXATOS do marcador15 original antes do replay042 em destino novo.
Não modifica binário ou snapshot nem afirma que `state restore` inclui perfil.

`dist/qa-reports/p228-lifecycle-3.json`: PASS10,3021s,5etapas completas:
instalação042/retained/offline/backup15 privado, upgrade043/ELFs CI/unit sem
autoenable/replay/migração16, recusa042 em CÓPIA16 sem alterar snapshot/WAL,
downgrade preservando16/restore15 em destino NOVO/replay042 e remove/purge
preservando estado/segredo/marcador/conta. Antes de restaurar marcador original,
o negativo de perfil não marcado recusou startup sem alterar snapshot/WAL.
SHA do marcador original restaurado separadamente:
`4ec6e6c0788676506f691b29da8bfb54e50beba6dec44dc40844e7dd0950e249`.
Backup15 snapshotSHA
`dd09c03730306cf5dfd3b5d590b9acaf5454d4efdd9b3a6feb1c5184ea43c2be`;
snapshot16 migradoSHA
`8cc95198544190fb68a7a162a0dfc0146a273f750c55b8d4e0672653d4a20728`.
WAL após shutdown em ambos:
`eb77c1a9d4deabfbb19fefc88a43d1843d11228a5f414c66fbfd4aa14b2a38eb`.
Container próprio terminou exit0 e foi removido por --rm. Recursos do operador
não foram alterados; não houve execução042 em live16.

Retry da coleta locked, sem compilação, em destino novo
`dist/notices-source-retry-1`: PASS166pacotes/323textos. Fonte/lock ba6, PATH
Rust explícito, Cargooffline, TMPDIR=/var/tmp, targetprivado; parcialENOMEM
anterior preservado. QA do pacote OFICIAL CI por funções originais
`expected_collection/deb_payload/verify_payload`: PASS166pacotes/323textos,
1.728.802bytes originais. Manifesto canônico SHA256
`2bd772c7e525cd56f966e9ef806b3cba87d819aa524d640097bc0c38f69b86b3`.
MIT própria fonte CRLF SHAacfd4bb82..., pacote LICENSE/copyright LF SHA
`84381e555814f7125a9db5bce4f79b786cfb795b05eaddc2ef31a3a414842fc9`:
comparação permite somente CRLF→LF própria. Terceiros estritamente byte a
byte, sem normalização, arquivos ausentes/extras rejeitados. Sem relicenciamento.

Ainda pendentes: vínculo das imagens à fonte final aprovada,
export/proveniência final. Publicação Hub/tag/prerelease só após aceite
global6/CI/comboadmin pelo coordenador, sem modificar latest/tags antigas.
Wire deste harness é MQTT3.1.1 loopback; não prova TLS, perda de energia ou
certificação integral MQTT5. MIT e textos originais de terceiros preservados.

## Adaptação de proveniência P228B1.4

Preparada antes do patch e aprovada pelo coordenador: `--source` é agora
SHA40 minúsculo explícito, validado sintaticamente; `runtime_checkpoint`
registra ba6 separadamente. O argumento NÃO prova origem. Para o pacote final,
o registro deve vincular head_sha do run GitHub PASS ao SHA256 do .deb e aos
ELFs esperados do comando. Baseline042, versões/arquiteturas e hashesELF não
mudam. Self-tests do harness agora5/5 (três leitores + dois grupos de sintaxe
SHA). Nenhum novo ciclo de pacote é alegado por esta alteração documental de
proveniência. Build Docker exclusivo autorizado está em execução com rótulo
do checkpoint d6f1062; fonte final e publicação seguem com o coordenador.

## Docker candidato validado, não publicado

Slot exclusivo liberado pelo coordenador após a release nativa terminar.
Build runtime `cargo build --locked --release --bins -j1`: PASS284s, perfil
release4m42; imagem legacyadmin reutilizou o build Cargo aceito (cache),
PASS3,8s. Sem compilação concorrente deste agente. Inputs de build rastreados
iguais a ba6; revisão de rótulo
`d6f10623e2ff4f0afc525c71f1e4ff31167665ca`, cujo diff era só QA/prompts.

- Candidato local `xmqr-p228-broker:0.43.0-d6f1062`, IID
  `sha256:48b7855e62910419f9c6f9335ec4a4468f4b37227704c4c0cdc8068883290f4e`.
- Candidato local `xmqr-p228-admin:0.43.0-d6f1062`, IID
  `sha256:f2b6037fc2328a57cfc701029d707b07c66aa072f03cf467a485583982de83ec`.

Não são digests remotos publicados. User10001:10001, platformlinux/amd64,
SIGTERM, entrypoints, versões0.43.0 e revisão conferidos por `validate_image`
original. Broker default secure-mtls sem credenciais recusa startup exit1
exigindo MQTT_SERVER_CERT; não há fallback aberto. ELFs Bookworm:
brokerSHA`a122cc2788993170eaf8ca65a11f142d08937fb8e2e821e7d2e9502cfd4375e3`,
legacyadminSHA`36068a35bcfb9b79fd820391f06e2633eae62ecc7cc90d221c1cb1021a3df98f`
igual nas duas imagens. Esses ELFs não são usados para fabricar pacoteUbuntu.

`verify_docker.py --remote-wss`: PASS TCPmTLS QoS1/pubsub, SIGTERM durável/
restart/retained, CA/senha inválidas; WSSmTLS MQTT3.1.1/5 pubsub/perfil e
negativos opt-in/CA/SAN/senha/ACL. Read-only/caps-none/no-new-privileges,
fixtures de certificados/credenciais públicas isoladas; nenhuma porta host
publicada. Peer imutável client0.38.0,
`lepinheiro100/xmqr-client@sha256:b025a82ab4172f82223e8b01b125570996f374a27ee524a04cc62eac81a148f9`,
clone da tag com HEAD`fca6fc82117b7ee2b770dc2e4ce673b53764b211`.
Report `dist/qa-reports/p228-docker-mtls-wss-candidate-1.json`, SHA256
`e080e42dee560a39dacc869cb283b8fdc7e74edea05c1b7bb4b86a95cf1fc5b3`.

`verify_admin_image.py`: PASS imagem dedicada non-root sem binário broker,
backup recusa trava ativa, backup/verify/restore offline e destino existente
recusado. Volumes/processos próprios removidos pelo harness. Report
`dist/qa-reports/p228-admin-image-candidate-1.json`, SHA256
`44b98ba92271cbdaab33316a6dc8652c526a5dd54e79bc1ea34ee4e18ec72890`.

Notices das duas imagens por funções originais `image_payload/verify_payload`:
PASS166pacotes/323textos/1.728.802bytes estrangeiros estritamente originais,
manifesto igual à coleta locked independente. MIT própria preservada CRLF,
SHArawacfd4bb82...; comparação canônica LF84381e55..., sem mudar termos.
Nenhum Hub/tag/prerelease/export final produzido. Rerótulo final por build
cacheado e pacoteCI da fonte final ainda dependem da coordenação e dos gates
globais; estes resultados não são aceite irrestrito da fase6.

## Repetição da fonte final db472bc — gates locais PASS

PreparaçãoP228B1.5 commitada antes da integração. Branch própria integrou
main`db472bc64558bf0e376a902b7780a259247c5149` em merge1cd7f208, preservando
623aeca/23c216; nenhuma alteração no original/main. Diff do merge contra db
contém somente os três arquivos P228B/harness/este registro. Inputs de build
src/Cargo/Docker/collector/notices/LICENSE iguais ao db e ba6, comprovados por
Git, não por número de versão ou argumento. AGENTS/skills não diferiram.

[CI39164202189](https://github.com/licodevone/xmqr/actions/runs/39164202189)
consultada pela API: completed/success, head_sha exatamente db472bc.
Artefato12150137120, `xmqr-broker-ubuntu26-amd64`, não expirado, baixado para
`dist/ci-db472bc-39164202189`. Pacote OFICIAL2.953.782bytes, SHA256 recalculado
e igual ao sidecar:
`c2341ab3a341b1854e85ebb2f0bec9535968374b226a12a60cee58aa7cef3d4e`.
DigestZIPb5c2ba3f... foi informado pela API, não recalculado aqui; não confundir
com SHA do .deb. Uma consulta inicial `gh run view --json artifacts` recusou
campo não suportado; consultas separadas de run/artifacts retornaram os dados.
Isso foi falha de consulta, não de pacote/CI. ELFs extraídos sem instalação,
versões0.43.0 PASS: broker1ee611b0.../admin3081297f... iguais aos hashes completos
já registrados; bytes Ubuntu nativos conferidos novamente.

Lifecycle REAL repetido desde instalação042 em novo container próprio com
o pacote CI db, não apenas mudança de flag: PASS27,3274s/5etapas completas.
Report `dist/qa-reports/p228-lifecycle-final-db472bc-1.json`, SHA256
`f77015aadf65e3ec4388786b3d37cfd6a698e8546de2bb6dc2904ce2276485ad`.
Retained/offline/documento15 e backup real privados, upgrade/replay16,
negativo042/CÓPIA16 exit1/schema sem mutação, downgrade sem converter16,
restore15 em destino NOVO com marcador original separado e negativo de perfil,
replay042 e remove/purge preservando dados/secret/conta PASS. Snapshot16 desta
execuçãoSHA`45aa71a1eb80161b7bee8efc092bba685d69df3d2ac4a03c2109b5744f09291c`;
snapshot15/WAL iguais ao ciclo anterior. FAIL1/2 anteriores preservados.

Imagens finais LOCAIS, VCS_REF db472bc, rebuild com etapa Cargo CACHED:

- `xmqr-p228-broker:0.43.0-db472bc`, IID
  `sha256:475b31c8258d853ae011cd46431b180556d19ce319db45b73923252c1f9c061b`;
- `xmqr-p228-admin:0.43.0-db472bc`, IID
  `sha256:673a062c7fd6ccaeedc34afb9ad1748f90fc7fba9367458ca49a642da649fafc`.

`validate_image` original confirmou revisão/user/sinal/entrypoint/arquitetura.
Hashes Bookworm medidos novamente: brokera122cc27.../admin36068a35..., idênticos
aos candidatos, sem usar esses ELFs no .debUbuntu. QA final mTLS TCP/WSS,
MQTT3.1.1/5, perfil, retained/restart e CA/SAN/password/ACL/opt-in negativos
PASS com client038 por digest imutável. Report
`dist/qa-reports/p228-docker-mtls-wss-final-db472bc-1.json`, SHA256
`d152acf9ee6b5b9741ba99a0a725379283cf7c762cb81a805c2dfadb1f1d0f0c`.
Imagem legacyadmin dedicada/UID10001/sem broker, lock ativo recusado,
backup/verify/restore e destino existente recusado PASS. Report
`dist/qa-reports/p228-admin-image-final-db472bc-1.json`, SHA256
`7c0679a98886857ff31f345d165f1c8c0e2ed0b703577ab4ef903f53a86d3c0c`.

Notices repetidos nos TRÊS artefatos finais (.deb oficial e ambas imagens):
PASS166pacotes/323textos/1.728.802bytes originais; manifesto igual à coleta
locked independente (inputs do coletor/Cargo/suplementos sem diferenças).
MIT própria preservada, terceiros estritamente byte a byte. Testes leves
repetidos: harness5/5, distribuição6/6, noticesnegativos14/14 PASS.

Export final pendente nesta atualização: aliases DockerLOCAIS numerados043
existentes apontam candidatos fonte1574ab9, não foram sobrescritos. Coordenador
foi informado para confirmar ownership e preservação antes da troca local;
alternativa seria exportar pelos refs próprios. Nenhum Hubpush/tagGit/release.
CI integrada39164217059 ainda aguarda confirmação do coordenador. O preparo
local não é aprovação da fase6 nem autorização para publicar.

## Preservação dos aliases LOCAIS autorizada

Coordenador conferiu ownership dos candidatos1574ab9 e autorizou a troca
somente local após preservação. Antes de qualquer tag, launcher inlinePython
falhou SyntaxError de quoting; nenhuma operação Docker foi executada por ele.
P228B1.6 revisado antes do retry; driver PowerShell próprio em dist validou
todos os IIDs, recusaria colisão em alias preservado e confirmou revisão db.

- `xmqr-p228-preserved-broker:1574ab9` preserva
  `sha256:6c4a865d03cbb603d8c1e5159d7f346c281ce144667352060bca31746e3f5bcc`;
- `xmqr-p228-preserved-admin:1574ab9` preserva
  `sha256:9c077343b37c929d8a40baec4fb2d2261532b0b11a361955e5ac02e9834514f1`.

Aliases LOCAIS lepinheiro100/xmqr-broker:0.43.0 e xmqr-admin:0.43.0 agora
apontam respectivamente os IIDs finais475b31c8.../673a062c... db472bc.
Imagens antigas não foram apagadas e são recuperáveis pelos aliases acima.
Sem push/retag remoto, latest ou tags antigas alteradas. Export a seguir será
executado no checkout limpo EXATO db, não no merge da branch de evidências.
