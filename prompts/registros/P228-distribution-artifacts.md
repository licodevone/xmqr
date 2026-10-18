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

Ainda pendentes: builds e QA de ambas imagens,
export/proveniência final. Publicação Hub/tag/prerelease só após aceite
global6/CI/comboadmin pelo coordenador, sem modificar latest/tags antigas.
Wire deste harness é MQTT3.1.1 loopback; não prova TLS, perda de energia ou
certificação integral MQTT5. MIT e textos originais de terceiros preservados.
