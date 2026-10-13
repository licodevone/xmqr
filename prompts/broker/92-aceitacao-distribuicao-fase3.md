# P92 v1.8 — gates finais e distribuição fase3

Preparado 2026-10-13 antes de versões/embalagem. P89 exige B06+B07+B08+C07
com evidência real. Broker patch0.11.6: recusas CONNECT corrigidas por P93,
sem formato/quota/dependência runtime nova. Client minor0.9.0: prazo total
opcional, jitter/cancelamento/prazos C45. Admin independente0.1.0 permanece
com pin e release anteriores se compatibilidade do formato for comprovada.
Não iniciar fase4. Alterações concorrentes pertencem aos agentes informados.

Gates nativos locked: fmt, teste completo, clippy-Dwarnings, release bins,
inventário MIT e avisos; falha requer revisão do prompt antes de correção.
P90 mutações reais com orçamento/seeds/watchdog; P91 3x600s reais de campanha
final TCP+mTLS, invariantes/recuperação/memória, Mosquitto2.0.22 independente
com matriz normativa e C45 ambos sentidos. Reexecutar B06 no código final.
Admin0.1.0 só compatibilidade, sem alterar pin/versão automaticamente.

Embalagem deve preservar os textos originais LICENSE/NOTICE, não apenas
inventário SPDX. Reutilizar coletor e suplemento valuable revisados A03 do
admin, verificar byte/SHA e metadados locked; superset inclui dependências
dev/Windows e AWS-LC vendorizado, não alegar composição ELF completa.
Docker allowlist ampliada só para coletor/suplemento; coleta no build e COPY
para runtime sem tokens/chaves. .deb instala copyright MIT e textos de
terceiros; testar hashes no payload e ciclo Ubuntu26 privado, sem serviços
do operador. Testes contratos devem cobrir essas novas entradas.

Somente fonte aceita commitada e clean: clone exato próprio, gate relevante
nesse commit e artefatos identificados por SHA/revisão. Docker Linuxamd64
Bookworm não root, sem latest, novas tags0.11.6 broker/legadoadmin e0.9.0
client. .debUbuntu26amd64, exporttar e manifest/checksums. GitHub prereleases
v0.11.6/v0.9.0 após push/tags; conferir assets reais e digests remotos Hub
lepinheiro100. Não sobrescrever tags/releases/arquivos já publicados.

Registros finais/matriz/checklist somente após PASS, limites claros: sem
MQTT5, produção/SLA/conformidade integral/ASAN/LibFuzzer/MSRV1.88 exato/arm64
ou novo teste Windows. Prompts e registros públicos nunca incluem secrets.
Falha de publicação não desfaz aprovação técnica mas deve ser informada,
sem dizer distribuído antes de verificação remota.

## Revisão1.1 — bytes de avisos antes de política Git

Inspeção confirmou core.autocrlf=true; suplemento valuable tem SHA pinado.
Adicionar packaging/notices/** -text a .gitattributes em ambos repos para
checkout não converter LICENSE original. Sem mudar bytes, licença ou fonte
de terceiro; hashes devem permanecer idênticos em clone/imagem/pacote.

## Revisão1.2 antes de corrigir coleta client

Dockerclient FAIL fechado: rumqttc0.25.1 não inclui LICENSE no crate. Metadata
Apache-2.0/repositorybytebeamio/rumqtt e .cargo_vcs_info.json confirmam revisão
f1e9e8d558783f942993046679cdf3c8c3a3d36b. API GitHub árvore completa dessa
revisão confirmou LICENSE raiz (11358bytes, blobd645695...), semNOTICE extra;
texto original recuperado por connector, não licença reescrita. Versionar
suplemento e SHA pinado, validar revisão/metadados antes de cópia, ampliar
allowlist somente pasta/LICENSE revisados e testes. Coreclient/MIT próprio
não são relicenciados; rumqttc conserva Apache2.0. Novo commit distribuição,
mesmo runtime0.9.0 ainda sem tag/release, clone exato atualizado e gate rerun.
OwnMIT EOL CRLF/LF é Gitcheckout: QA compara termos/copyright canônicos e
registra hashesraw; terceiros permanecem byte estrito, valuable -text preservado.

## Revisão1.3 — ambiente ENOSPC antes de remediação própria

Diagnóstico P91/C46 confirmou /tmp tmpfs3.9GiB100%/0livre; cacheCargo privado
copiado em/tmp encheu memória/filesystem, jobsRPCintermitentes e build falhou
ENOSPC. P91 teve2campanhasFAIL(795s/136s), não30minPASS; /var/tmp ext4/dev/sdf
tem946GiBlivres. Nenhuma modificação runtime por esse diagnóstico. Validar
PIDs/args e paths absolutos APENAS jobs/cacheC46 próprios antes de encerrar/
mover cache para destino próprio/var/tmp (recuperável, Linuxshell único).
Não apagar/tmp ou dados/serviços alheios nem reiniciar WSL/Docker. Todo novo
cache/estado durável/teste deve usar /var/tmp nativo, TMPDIR=/var/tmp e budgets;
gate sourceexato com -j1 evita competição desnecessária. ReexecutarP91>=3x600s
inteiros; repetirP80/B06/P90 no filesystemfinal e preservarfalhas anteriores.

## Revisão 1.4 — antes de corrigir fixture de compatibilidade

O wrapper verify_admin_compatibility.py ainda força dir=/tmp apesar do TMPDIR
do processo. Retirar apenas esse override; o wrapper e o fixture independente
passam a respeitar TMPDIR=/var/tmp. Sem mudar admin, pin ou seus 18 cenários.
P94 full P80 final-v3 passou 60/60, mas P95 provou ragged EOF no SIGTERM mTLS:
6/6 sinais falharam com TLS1.2/1.3, 2/2 DISCONNECTs foram controles positivos.
Repetir os gates pertinentes no ELF corrigido, não anunciar fase 3 encerrada.

## Revisão 1.5 — checkpoint documental antes do congelamento P95

Criar docs/phase3-acceptance.md inicialmente EM VALIDAÇÃO, distinguindo os
gates já observados de B08/artefatos ainda pendentes. Atualizar notas de
CHANGELOG/README/VERSIONING com a correção P95 e as referências aos três
sistemas, sem declarar aceite ou MQTT5. O relatório só passa a ACCEPTED após
os resultados reais requeridos. Registrar fonte exata dos artefatos separada
de commits documentais posteriores; não atribuir artefatos a outro commit
sem gate de identidade/build. Imagens anteriores permanecem sem alteração.

## Revisão 1.6 — executar os ELFs instalados no ciclo Ubuntu26

Clone broker abbe38ca passou oito gates (135 Rust) e os ELFs coincidiram com
e57b1e2d/f40ecbb5; .deb a2ce949b e client04eb2830. QA dos cinco payloads PASS
com licenças originais; ciclo install/upgrade/rollback/remove/purge Ubuntu26
passou. Inspeção do fixture mostra que check_versions consulta dpkg, mas não
executa os ELFs instalados. Os avisos usr-merge de dpkg-shlibdeps não devem
ser tratados como prova da execução. Antes de reforçar packaging/test_package.sh,
acrescentar --version real de broker/legadoadmin/client em cada etapa instalada
e comparar à versão Debian sem revisão. Repetir ciclo privado completo com
os MESMOS artefatos. Não mudar builder, Cargo, binários, serviços do host ou
tags. Não anunciar P91 concluído enquanto soak/matriz completa estiverem ativos.

## Revisão 1.7 — aceite real antes do fechamento documental e publicação

P91 agora terminou: soak6/6, 1808.946s, todos>=600s; matriz87/87, TLS12,
wire19 e contratos21 PASS. P95/B06/P90/P80/C45/C46, clones exatos, QA5,
licenças e ciclo Ubuntu26 com ELFs instalados PASS. Gitleaks do código novo
broker/client PASS redacted, sem inferir auditoria integral. Concluir agora
docs/phase3-acceptance, evolution-plan, matriz, README/CHANGELOG/VERSIONING,
COBERTURA e registros. Em client, concluir README/CHANGELOG/C46; em admin,
atualizar somente o estado factual do planejamento A04, não versão/pin.

Preservar JSONs históricos: soak capturou HEAD3a5e29d dirty=true antes do
checkpoint abbe, mas o ELF executado e57b1e2d e hashes src/Cargo são estáveis
e coincidem com rebuild limpo abbe. Não relabelar o report como clean.
Interop usa imagens576de5dd/e1c56183 com revisionsabbe/e688; nenhum MQTT5.
Erros intermediários sem causa exata permanecem explícitos, reforçados por
diagnóstico Will6PASS/oráculo SUBACK/contratos21 e matriz completa final,
não mera promoção de um retry. Aceite é finito/experimental, não estabilidade
ilimitada, SLA ou conformidade integral.

Artefatos exportados de abbe/e688 clean, tags nesses checkpoints imutáveis,
prereleases, Hub numerado sem latest, verificação real dos digests/assets.
Commits documentais posteriores não alteram a fonte atribuída aos artefatos.
Só marcar distribuição publicada depois das verificações remotas; falha de
publicação deve permanecer informada sem desfazer/mascarar os gates técnicos.

## Revisão 1.8 — checksum documental antes da publicação

Get-FileHash calculou SHA real da matriz87 final:
809719cd60c24e8a97c53506b813719125470c3b1494275e164c06e3aaabddaf.
O registro coordenado recém-criado contém um 'd' extra (65 caracteres), erro
de transcrição do resumo, não alteração do JSON. Corrigir somente esse texto;
copiar evidências originais sem editar e gerar sidecars a partir dos bytes reais.
Validar cada asset e manifest, sem anexar logs, credenciais ou estado bruto.
