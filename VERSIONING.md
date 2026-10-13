# Versionamento

## P86/P87 — patch0.11.5, início da fase3

P86 corrige a distinção entre erro de leitura e cauda WAL incompleta. Somente
UnexpectedEof autoriza truncamento; EIO preserva o arquivo e falha a abertura.
Injetores são exclusivos de testes, sem configuração pública. Client0.8.1
mantido; formatos e dependências preservados. P87 governa commit exato,
tag/prerelease/.deb e Hubbroker/admin0.11.5 após gates, sem latest/overwrite.
Esse marco B06 não encerra a fase3 nem equivale a homologação de produção.

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
