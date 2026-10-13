# P78 — Aceite de fontes e candidatos de distribuição

Data: 2026-10-13. Prompt P78 revisão 1.6. Base e8bd06b, broker/admin0.11.2;
client6c54281/0.8.0. Versões aceitas para publicação: broker/admin0.11.3,
client0.8.1 (C42). Solicitação esclarecida: concluir plano e distribuição,
não executar todas as fases. MIT, dependências, MQTT e estado preservados.

## Alterações e planejamento

- Admin --version/-V sem I/O/configuração; argumentos combinados continuam exit2
  sem echo. Dois testes novos de processo.
- Dockerfile separa admin e mantém broker como alvo final/padrão. UID10001,
  SIGTERM, mTLS padrão e contexto allowlist. Build confere versão real.
- Exportador de artefatos verifica versão/revision/user/entrypoint/platform,
  checksum e manifest do commit limpo, sem publicar ou ler credenciais.
- Plano completo com requisitos/donos/dependências/gates, MQTT5 em quatro
  fatias, operação/admin, client, transports e distribuição. Não é conformidade
  completa ou execução das fases. Leitor independente respondeu sete perguntas.
  Corrigidas três ambiguidades: E01/E02, offline/online e A04/A09. Segunda leitura
  integral não encontrou novo bloqueio concreto.
- Alterações paralelas do curso e dois tar.gz/checksum client preexistentes
  serão preservados fora do commit. Artefatos finais sairão de clone limpo do
  commit aceito, sem incorporar trabalho paralelo não selecionado.

## Resultados observados

| Gate | Resultado / ambiente |
| --- | --- |
| cargo fmt --all -- --check | PASS Linux/WSL Ubuntu26 |
| cargo test --locked broker/admin | PASS 107 testes:88 lib+4 admin+4 main+1 backup+2 admin CLI+5 configuração+1 quotas+2 versão |
| cargo clippy --locked --all-targets -- -D warnings | PASS após revisão das duas asserções is_empty do teste novo |
| cargo build --locked --release --bins | PASS Rust1.99/Ubuntu26amd64 |
| python3 scripts/license_inventory.py --check | PASS, lock alterado somente na versão do próprio pacote |
| python3 scripts/test_distribution.py | PASS5, contrato Docker/contexto/proveniência e negativos |
| Build Docker broker/admin/client candidatos | PASS DebianBookworm linux/amd64, usuário10001 |
| verify_docker.py | PASS mTLS pub/subQoS1, bytes/retain, SIGTERMexit0, retained após restart, CA/senha inválidas recusadas, rootfsread-only/capsALL/no-new-privileges |
| verify_admin_image.py | PASS imagem sem binário broker; backup recusa lock ativo; backup/verify/restore offline e destino existente recusado |
| build_deb.py | PASS Ubuntu26amd64; broker inclui admin; aviso dpkg-shlibdeps de usr-merge, sem erro |
| test_package.sh em Ubuntu26 descartável | PACKAGE_LIFECYCLE_PASS: instalação0.11.2/0.8.0, upgrade0.11.3/0.8.1, rollback, remove/purge e preservação; units verificadas sem auto-enable |

Falhas registradas/revisadas antes de corrigir: aplicação de patch recusada
sem edição; Clippy em assert_is_empty; readiness da fixture sem RUST_LOG;
verify no rootfsread-only sem tmpfs. A última foi corrigida no harness/guia,
com /tmp limitado128MiB, noexec/nosuid; não mudou o contrato do aplicativo.
Cada fixture limpou apenas seus próprios containers/volumes/redes.

## Publicação e evidência final

O aceite acima é da árvore candidata. Antes da publicação, criar commit
selecionando somente P78; usar clone limpo desse commit para builds finais,
gerar .deb/imagens/hashes e repetir gates de artefatos. Tagv0.11.3 imutável,
prerelease experimental e Hub numérico apenas após essa verificação.
Os anexos finais release-manifest, acceptance e registry-digests conterão
commit, hashes, imageIDs e digests efetivamente publicados; não são os labels
p78-candidate dos testes de preparação. Nenhuma publicação é alegada por este
registro anterior ao commit. Resultado final deve ser conferido nos anexos.

Somente Ubuntu26 .deb e Docker linux/amd64. NOT_RUN: arm64, instalaçãoUbuntu24,
MSRV1.88 exato, Windowsbroker, ESP32 físico e conformidade integral MQTT5.
Não instalou pacotes no host/WSL, não alterou serviço real, certificados reais,
firewall, volumes do operador ou tags antigas/latest.
