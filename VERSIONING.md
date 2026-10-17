# Versionamento

## P145 — marco de negociação de recepção MQTT 5

Broker e `mqtt-admin` legado 0.23.0 incluem P144; client independente 0.21.0
inclui C80/C81. Documento durável v10 permanece compatível com broker 0.22.0;
o ciclo de pacote ainda deve validar o rollback. O admin independente fica em
0.4.0. Fases 6A–6D e 7–9 seguem abertas. [Nota de release](docs/releases/0.23.0.md).

## P143 — marco de metadados de PUBLISH MQTT 5

Broker e `mqtt-admin` legado 0.22.0 incluem P141/P142; client independente
0.20.0 inclui C77/C78. O documento durável passa a v10; rollback ao broker
0.21.0 exige backup privado v8 anterior à primeira gravação nova. O admin
independente permanece 0.4.0. Fases 6A–6D e 7–9 continuam abertas.
[Nota de release](docs/releases/0.22.0.md).

## P141 — aceito em main após 0.21.0

Payload Format Indicator e Content Type MQTT 5 são preservados na mensagem
durável. O broker lê documentos v1–v8 e grava v9 na próxima transição.
Rollback para 0.21.0 exige backup privado v8 anterior à migração; não abra
estado v9 com 0.21.0. O client C77 publica essas propriedades. Sem tag/release
para esta fatia isolada; testes, integração e CIs da fonte passaram.

## P140 — marco de Topic Alias MQTT 5

Broker e `mqtt-admin` legado 0.21.0 incluem P138/P139: Topic Alias de entrada
e saída por conexão. Client independente 0.19.0 acompanha. Não há nova
migração do documento v8. O Mosquitto 2.0.22 rejeita a forma abreviada válida
em fixture isolada; essa direção não está homologada. Fases 6A–6D permanecem
abertas. [Nota de release](docs/releases/0.21.0.md).

## P137 — marco de limites MQTT 5

Broker e `mqtt-admin` legado 0.20.0 incluem P134/P136: Receive Maximum e
Maximum Packet Size MQTT 5. Client independente 0.18.0 acompanha. Não há nova
migração do documento v8. [Nota de release](docs/releases/0.20.0.md).

## P133 — marco de expiração e Will MQTT 5

Broker e `mqtt-admin` legado 0.19.0 incluem P130–P132: Message Expiry,
DISCONNECT Session Expiry e Will Delay. Client independente 0.17.0 acompanha.
O documento durável migra de v6 para v7/v8; rollback para 0.18.0 exige backup
privado v6 anterior. Fases 6A–6D continuam abertas. Veja a
[nota](docs/releases/0.19.0.md).

## P129 — marco de sessões MQTT 5

Broker e `mqtt-admin` legado 0.18.0 incluem P126–P128: ACKs de sucesso em formas
normativas, Clean Start e Session Expiry zero/finita/infinita. Client independente
0.16.0 acompanha. O documento durável migra de v5 para v6 na próxima gravação;
rollback para 0.17.0 exige restaurar backup privado v5 anterior à migração.
Fases 6A–6D continuam abertas. Veja [nota](docs/releases/0.18.0.md).

## P124 — marco MQTT 5 ampliado

Broker e `mqtt-admin` legado 0.17.0 incluem P119–P123: QoS2 MQTT 5,
UNSUBSCRIBE, motivos ACL e propriedades informativas de CONNECT. P125 libera
explicitamente o lock do armazenamento no encerramento. Client independente
0.15.0 C60–C64 acompanha o subconjunto. Fases 6A–6D e conformidade MQTT 5
integral continuam abertas. Documento durável v5 inalterado. Distribuição
experimental e rollback em [nota](docs/releases/0.17.0.md).

## P117 — marco MQTT 5 inicial

Broker e `mqtt-admin` legado 0.16.0 acrescentam o subconjunto MQTT 5 P115/P116:
sessão limpa, publicação e assinatura QoS0/1 sem propriedades avançadas,
com entrega viva/retained e interop Mosquitto. Client independente 0.14.0
C57/C58 acompanha o contrato. Fase6A, QoS2 e propriedades continuam abertos.
Documento durável v5 e formato 3.1.1 não mudam; rollback para broker 0.15.0
exige encerrar o serviço e preservar backup offline do diretório de estado.
Distribuição experimental conforme [nota](docs/releases/0.16.0.md).

## P113 — fechamento experimental da fase 5

Broker e `mqtt-admin` legado 0.15.0 acrescentam canal local autenticado,
recibos duráveis, auditoria com rotação/épocas no documento MQTT v5, inventários,
ações de sessão/retained e versão em status. Admin independente 0.4.0 fornece
CLI e diagnóstico; client 0.13.0 já foi publicado. O broker lê v1–v4, mas
0.14.0 não lê v5: rollback requer backup offline anterior e diretório novo.
As tags são imutáveis e as releases permanecem experimentais. Consulte
[aceite da fase 5](docs/phase5-acceptance.md) para gates e limites.
As tags `v0.15.0`/`v0.4.0` e prereleases correspondentes foram publicadas;
veja [P113](prompts/registros/P113-release-fase5.md).

## P103 — fechamento experimental da fase 4

Broker/legado admin0.14.0 inclui rotação TLS P100/B11 e política estática por
endpoint P101/B09. P102 passou na COM4 com seis rotações físicas; fase4 foi
aceita no escopo finito. Taguear/publicar 0.14.0 só após gates do commit exato,
pacotes, hashes e imagens numeradas; client0.12.0 segue versão própria e admin
independente0.2.0 continua inalterado.

## Fase 4 — P97/P98

Broker/legadoadmin 0.13.1 acrescenta `tls-password` opt-in no listener único;
client C48 0.11.1 mantém CA/SAN/validade sem certificado de cliente. As tags
0.13.0/0.11.0 ficaram sem release por default Docker divergente; P99/C49
corrigiram isso sem reescrever tags. B12 tem
decisão em ADR-0006, sem reload geral do TOML. Políticas por listener B09,
rotação B11 e campanha física E02 continuam abertas. Tags/release são criadas
somente após gates e artefatos do commit exato; versões anteriores imutáveis.

## P89–P95 / C45–C46 — fechamento técnico da fase3

Broker/legadoadmin patch0.11.6 corrige recusas CONNECT e encerramento TLS;
client minor0.9.0
adiciona prazo total opcional e robustez de reconexão. Novo admin0.1.0 mantém
pin/release e é exercitado contra o broker, sem bump documental artificial.
P92/C46 regem aceites e distribuição nova, sem mover tags/latest antigos.
Checklist B06/B07/B08/C07 encerrado com resultados efetivamentePASS.
Gates/PROMPTS e limites em phase3-acceptance; versões candidatas não anunciam
por si só publicação ou homologação. Artefatos dos checkpoints abbe38ca/e688c75,
mesmo com registros posteriores; MQTT3.1.1/MIT/formatos/quotas preservados.

Publicação P92 concluída: tagsv0.11.6/v0.9.0 nesses checkpoints, prereleases
com42/18assets e checksums remotos conferidos. .deb/manifests baixados iguais;
Hub numerado e execução por digest aprovados. Docs posteriores não exigem bump
ou retag, nem alteram os manifests de fonte dos artefatos.

## P88 — terceiro projeto, sem bump do broker

xmqr-admin independente0.1.0 tem tag/release e pacote próprios. mqtt-admin
legado permanece0.11.5 no broker/deb/imagem existentes. A publicação do novo
admin não move tag0.11.5 nem muda client0.8.1. P88 apenas atualiza referências
e checklist; commits documentais não exigem versão/tag artificial.

## P86/P87 — patch0.11.5, início da fase3

P86 corrige a distinção entre erro de leitura e cauda WAL incompleta. Somente
UnexpectedEof autoriza truncamento; EIO preserva o arquivo e falha a abertura.
Injetores são exclusivos de testes, sem configuração pública. Client0.8.1
mantido; formatos e dependências preservados. P87 governa commit exato,
tag/prerelease/.deb e Hubbroker/admin0.11.5 após gates, sem latest/overwrite.
Esse marco B06 não encerra a fase3 nem equivale a homologação de produção.

PublicaçãoP87 concluída: tagv0.11.5 no commit3606ede844210997fa733408855099535145ac48,
prerelease, .debUbuntu26amd64 e duas imagensHub numéricas com digests remotos
conferidos. Client0.8.1/tags antigas/latest não alterados. Ver registroP87.

## P80/C43 — correção0.11.4 e evidência fase2

Broker/admin0.11.4 limita shutdownTLS demonstrado por não leitor.
Clientruntime0.8.1 mantido; C43 só acrescenta testes/documentação.
Tagv0.11.4/prerelease/.deb/Hub após gates do commit exato.
Release da correção não encerra fase2: E01 físico permanece pendente.

## Marco P78/C42 — 2026-10-13

Broker/admin 0.11.3 e client 0.8.1 são patches de distribuição, com consulta
de versão do admin. O admin permanece no crate do broker; não tem ciclo
independente. Publicar v0.11.3/v0.8.1 somente depois dos gates e artefatos
desse commit. Docker Hub autorizado: lepinheiro100/xmqr-broker,
lepinheiro100/xmqr-admin e lepinheiro100/xmqr-client, tags numéricas novas.
Não alterar tags existentes nem latest. Prereleases preservam limitações
experimentais. Planejamento completo não significa fases implementadas.

Broker e client têm versões independentes. Tags publicadas não são alteradas.
A base do broker é v0.9.0 (688fa4f); P47 cria o marco0.10.0 para systemd/deb.
A base do client é v0.4.0 (3e7c16a); C31 cria o marco0.5.0.

Minor0.x.0 adiciona uma fatia; patch0.x.1 corrige defeitos. Pacotes Debian usam
revisão separada (ex.:0.10.0-1). Tag identifica código; GitHub Release inclui
notas e anexos e não equivale a pacote num repositório APT.

Releases permanecem experimentais/pre-release até conformidade, interop,
recuperação e operação comprovadas. Commit/push/tag/publicação só com autorização.
Esta etapa tem autorização explícita; confirmar gates e registrar limitações
antes de tag/publicação. Não reescrever tags0.9/0.4 para incluir novos binários.

MIT, MQTT3.1.1, quotas e formato de estado preservados. MQTT5 não implementado.
1.0 depende dos gates de produção; sem promessa de API estável em0.x.

## Fase1 — P61

Broker0.11.0 e client0.7.0 têm tags independentes e releases experimentais.
Gates Ubuntu26/WSL, interop e ciclo de pacote em container foram aprovados.
Não há homologação nova de Ubuntu24, arm64, Windowsbroker ou MSRV1.88 exato.
Não há conformidade MQTT5 nem prontidão de produção. Tags antigas imutáveis.
