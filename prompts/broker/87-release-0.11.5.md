# P87 v1 — distribuição do patch P86/B06

Preparado em2026-10-13 sob autorização contínua do mantenedor. Entrada:
P86 reproduziu erroEIO após leitura curta convertido emUnexpectedEof; o código
agora propaga o erro e só permite truncar EOF verdadeiro. Broker/admin0.11.4
e client0.8.1 publicados e imutáveis. Esta release depende dos gates finais
deP86, não declara fase3 concluída.

Objetivo: patch broker/admin0.11.5; clientruntime0.8.1 mantido. Antes de editar
versões: atualizar Cargo.toml/lock raiz, ARG VERSION Dockerfile, CHANGELOG,
VERSIONING, README/documentação, registro P87. Não mudar dependências, MSRV,
MIT, WAL/snapshot/documento MQTT, quotas ou configurações. Nenhum arquivo
privado do ESP32 ou estado real entra no contexto Docker/artefatos.

Sequência autorizada:

1. AceitarP86 com fmt/test/clippy/build/inventário, negativos e wire loopback;
   executar regressão client e integração mTLS pertinente em recursos novos.
2. Commit revisado, merge fast-forward e pushmain; não usar force nem tocar
   alterações não relacionadas. Gate adicional no commit exato, árvore limpa.
3. `.deb` Ubuntu26.04 amd64 a partir de clone limpo desse commit. Ciclo
   instalação/upgrade/rollback/remove/purge somente em container descartável;
   versões anteriores e client0.8.1 são pacotes já publicados, não novos builds
   do client. Preservar configuração/dados/credenciais simulados no teste.
4. DockerBookworm linux/amd64, targetsbroker/admin com versão real e labelsOCI
   do commit; usuário10001, mTLS padrão. Testes próprios pub/sub, retenção,
   reinício, negativos e admin com dados efêmeros. Confirmarcleanup.
5. Gerar arquivos exportados, SHA256 e manifesto de provenance. Nova tag
   anotadav0.11.5 somente no commit aceito; GitHubprerelease com limites e
   anexos.deb/checksums/imagens/manifesto/evidência. Publicar Hub
   lepinheiro100/xmqr-broker:0.11.5 e xmqr-admin:0.11.5, conferir digests remotos.
   Sem latest, overwrite, tag/clientnova ou reupload de binário antigo alterado.
6. Registro público de commits, hashes/digests e gates reais após resultados;
   commit/push documental. Só então anunciar a release completa.

Ferramenta ausente/falha externa => BLOCKED/FAIL concreto, nunca PASS presumido.
Sem instalar/alterar serviços reais, firewall, router, Wi-Fi/firmwareCOM4;
sem promessa de energia real, todas as plataformas ou prontidão para produção.
