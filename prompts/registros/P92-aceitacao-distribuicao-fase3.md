# P92 — fechamento coordenado e distribuição da fase 3

13 de outubro de 2026. Prompt P92 v1.6 preparado antes das mudanças e
revisado antes de cada correção. Estado deste registro: **EM VALIDAÇÃO**;
não anuncia fase concluída, tags ou publicação antes dos gates pendentes.

## Checkpoints de código e versões

- Broker e mqtt-admin legado 0.11.6: fonte de distribuição
  abbe38ca6c041f7328e85054506a4eed22c74c41, clonada limpa e detached pelo Git
  Linux. CONNECT é corrigido por P93 e TLS/drain por P95, sem novo formato,
  dependência ou quota.
- Client 0.9.0: fonte e688c75a3779803e8f1868792dcc5e7a36f2dd6e, clone
  limpo com oito gates PASS e pacote candidato gerado. C45/C46 são próprios.
- Admin independente 0.1.0: versão, pin 3606ede844210997fa733408855099535145ac48
  e distribuição anterior preservados. A04 entregou somente planejamento.

Commits posteriores de documentação não são apresentados como fontes de
artefatos construídos antes deles. As tags finais devem identificar esses
checkpoints depois do aceite, sem mover versões já publicadas.

## Resultados reais deste checkpoint

Broker nativo final e57b1e2d26de50d09bb6bdadb74e4c0531dcac15399ece4369f4e0a0824e2987;
admin legado f40ecbb5e1641565bbf6ec2cb0e14a7d58973709270bc89c64070ae32b6f9083.
P95: 135 Rust PASS, seis campanhas explicitamente opt-in repetidas por P90,
fmt/clippy/build/inventário PASS. P90 final 18/18, fontes estáveis; nenhum
claim de ASAN/LibFuzzer. TLS estrito 12/12 e wire 19/19 no mesmo ELF.

P80 repetido integralmente no ELF final: 60/60 PASS, arquivo ignorado
dist/p92-pressure-p95-final.json, em /var/tmp disk-backed; B06 e quotas
preservados. Verificação adicional de shutdown: três testes independentes
PASS, incluindo falha real de snapshot que não termina como sucesso.

Admin independente 0.1.0 contra o broker final: 18/18 cenários PASS no
wrapper verify_admin_compatibility.py, em laboratório privado. ELF do admin
b6edea14c7214ce4574f08d954a8a2e4833995f0f5b6bd054d133f412d0f473e.
Campo histórico de versão do fixture não foi usado como prova; o wrapper
consultou versões/hashes reais. Não houve repin ou implementação de canal.

Docker final do checkpoint abbe38ca: broker e admin legado construídos e
versões reais conferidas. verify_docker PASS: mTLS pub/sub, bytes/retained,
SIGTERM/restart e negativos de CA/senha. verify_admin_image PASS: imagem
dedicada, não-root, ausência do broker, recusa de lock ativo, backup/verify/
restore offline e recusa de destino existente. Recursos de teste removidos;
nenhuma configuração, porta, serviço ou dado do operador foi alterado.

O clone broker concluiu oito gates PASS em 786,159s: 135 testes, Clippy,
fmt, release, inventário, seis contratos de distribuição, coleta 113/218 e
.deb Ubuntu26. ELFs reconstruídos iguais aos hashes e57b1e2d/f40ecbb5,
clean antes/depois. Pacote 2.400.116 bytes, SHA
a2ce949b1d20c685835ae4eeac697d59c41306dc1deea8bd7375d8293eba4cb3.
Esses resultados estão nos JSONs privados do clone (p92-native-final e
p92-native-identity); igualdade neste build não promete reproducibilidade geral.

QA completo dos cinco payloads PASS, 14 negativos PASS; report
dist/p92-notices-final.json SHA
60b392dec0593f8e8994573a5d25b9f8dfc64ff624e10ff8860efa4c1d32d0ae.
113/218 no broker/legadoadmin e 81/158 no client, comparados a fontes externas
aos próprios payloads. Primeiro localizador do manifest usou pasta errada;
foi corrigido antes de executar QA, não foi falha de conteúdo do pacote.

Ciclo Ubuntu26 completo PASS com os mesmos .deb: instalação 0.11.5/0.8.1,
upgrade 0.11.6/0.9.0, rollback, remove/purge, conffile editado/dado/senha de
fixture preservados conforme contrato, unidades válidas e sem autoenable.
P92 v1.6 reforçou check_versions para executar os três ELFs instalados;
sintaxe shell PASS e ciclo inteiro repetido PASS. Sem corrigir/ignorar ABI
por inferência do aviso usr-merge. Containers efêmeros ausentes após cleanup.

P91 campanha 3x600s e matriz 87 permanecem em andamento; duas repetições
longas passaram, mas ainda não são o aceite integral. Falhas externas e
seus diagnósticos estão preservados em P91, sem promovê-las por mero retry.
Tags, exportação aceita e publicação ainda são gates pendentes.

## Licenças e falhas operacionais preservadas

Código próprio MIT e copyright preservados. Coleta de originais é superset
do Cargo.lock (inclui dev/Windows/AWS-LC), não SBOM completo do ELF nem parecer
jurídico. Suplementos valuable/rumqttc são originais, com revisão/hash
verificados; a falta inicial de LICENSE no crate rumqttc falhou fechada antes
do ajuste. Não relicenciar terceiros. MIT própria só admite normalização
CRLF para LF na comparação; textos estrangeiros exigem bytes estritos.

Client candidato .deb e imagem passaram comparação dos 81 pacotes/158 textos;
a primeira chamada de QA .deb usou caminho de manifest errado e falhou,
a chamada corrigida passou sem alterar o artefato. O QA conjunto final acima
passou após o .deb do broker estar pronto, com os mesmos bytes.

O primeiro checkout do clone broker foi tentado enquanto a clonagem ainda
copiava os packs; falhou por arquivo em crescimento e o Docker não iniciou
por ausência de Dockerfile. A clonagem terminou com exit0; checkout exato
depois disso funcionou. Não mascarar a primeira falha como build PASS.
fsck padrão também apontou três entradas históricas ausentes no cache
commit-graph copiado; conectividade dos objetos reais no clone e origem
passou com core.commitGraph=false. Nenhum cache Git/histórico original foi
reescrito ou apagado. O clone permaneceu clean e recebeu o checkpoint final.

Falhas de /tmp/ENOSPC e tentativas WSL que não iniciaram estão em C46/P91.
Não afirmar que limpamos/movemos aquele cache: o helper recusou qualquer
mutação quando a origem já estava ausente. Novos builds usam cache privado
ext4 /var/tmp, -j1, sem cópia ampla ou restart de WSL/Docker.

## Fechamento técnico coordenado — 2026-10-13

P91 terminou integralmente: soak6/6 em1808,946s, três repetições TCP/mTLS,
todas>=600s, 40512publicações/162048entregas,90SIGKILL/30SIGTERM. Os1698probes
incluem quatro ready0 transitórios e recuperação máxima1,659s dentro do budget
quiescente15s. Report p91-soak-candidate-6.json SHA
6bdc2c71c276723a0c4ad782643752aad243816e5d8283a386d63678951826c1.

Matriz final p91-interop-candidate-4.json passou87/87 (59C43+28extensões),
346,063s, cleanup202containers/2volumes PASS. SHA
809719cd60c24e8a97c53506b813719125470c3b1494275e164c06e3aaabdddaf.
Will isolado6/6 e contratos do harness21/21 reforçam o diagnóstico sem ampliar
W8. As causas exatas dos dois FAIL anteriores de readiness não foram recuperadas
e seguem explícitas em P91. Não trocar falhas antigas por PASS ou culpar ambiente
sem prova. Wire19 e TLS12 no ELF final, todos os demais gates acima, passaram.

O report do soak conserva HEAD3a5e29d dirty=true do início. As26entradas src/Cargo
ficaram estáveis, e o ELF e57b1e2d coincidiu com o rebuild clean abbe38ca. Interop
usou IDs Docker576de5dd/e1c56183 e revisionsabbe/e688. Não relabelar essa evidência
como checkout clean; a identidade foi estabelecida separadamente.

docs/phase3-acceptance.md passou a ACCEPTED no escopo experimental validado,
com checklist/matriz/documentação alinhados. Exportação a partir dos clones
exatos passou; .deb e exports Docker tar.gz têm checksums/manifests. Ainda não
é publicação remota. Os tar.gz são imagens para docker load, não arquivos de
ELFs nativos para instalação direta. MQTT3.1.1 permanece o protocolo entregue.

## Pendências de publicação e limites

Somente após P91 e os demais gates: concluir o registro de aceite, tags
imutáveis v0.11.6/v0.9.0, prereleases com .deb/tars/checksums/provenance,
push de imagens numeradas para lepinheiro100 e verificação remota dos digests.
O admin independente não recebe uma versão documental artificial.

Sem MQTT5, fases 4/5 implementadas, Windows broker nativo, arm64, MSRV1.88
exato, novo teste físico ESP32, SLA, throughput máximo, dias de estabilidade
ou prova de perda de energia. Fonte e limites em docs/phase3-acceptance.md,
P90/P91/P93/P94/P95 e C45/C46. O plano administrativo está no repositório admin.
