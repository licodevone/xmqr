# P78 — Planejamento de paridade e distribuição Docker Hub

Versão: 1.6. Data: 2026-10-13. Estado: execução autorizada.

Revisão 1.1: a primeira aplicação de patch não encontrou a linha compacta da
ajuda do admin. Reaplicar como edição independente; preservar saída de ajuda
e código 2 para argumentos inválidos. Não ocorreu execução de software.

Revisão 1.2: a ferramenta recusou delete/add no mesmo path de .dockerignore.
Usar somente Update File e validar o patch inteiro antes da aplicação.

Revisão 1.3: o leitor independente encontrou três ambiguidades no plano:
ESP32/rotação tinha dependência circular entre fases; offline/online do admin
estavam misturados; aprovação de ADR não distinguia implementação do canal.
Separar E01 base/E02 rotação, administração offline/online e A04 contrato/A09
implementação. Nenhuma fase futura será executada para resolver esses pontos.

Revisão 1.4: os 107 testes Rust passaram, mas Clippy recusou duas asserções
is_empty do novo teste de admin. Comparar com vetor vazio explicitamente,
sem desabilitar lint; repetir fmt/test/Clippy/build/inventário/contratos.

Revisão 1.5: teste do admin esperava log de readiness sem habilitar RUST_LOG;
EnvFilter padrão filtra o aviso open-lab. Definir RUST_LOG=info somente no
broker temporário da fixture e repetir; não alterar logs/perfis do aplicativo.

Revisão 1.6: backup passou mas verify precisa da cópia temporária em /tmp;
rootfs read-only sem tmpfs impediu esse teste. Adicionar tmpfs limitado, privado
ao container, documentar a necessidade para o admin e repetir backup/verify/
restore. Não tornar o rootfs gravável nem alterar o contrato offline existente.

## Entrada e autorização

Broker/admin: HEAD e8bd06b, versão 0.11.2, árvore limpa. Client independente:
HEAD 6c54281, versão 0.8.0, dois arquivos tar.gz/checksum locais preexistentes
que não serão alterados nem adicionados ao commit. Docker Desktop Linux/amd64
e Ubuntu-26.04/WSL com Rust 1.99 estão disponíveis. Docker Hub autenticado
como lepinheiro100, conferido sem ler ou exibir tokens.

O mantenedor autorizou commits, pushes, tags e releases de entregas aceitas,
.deb e Docker Hub. Esclarecimento posterior: concluir o plano detalhado e
a distribuição solicitada; não implementar todas as fases de paridade agora.

## Objetivo e escopo

1. Concluir um plano rastreável de broker/admin/client frente ao Mosquitto,
   com estado, dependências, critérios de saída e limites de cada fatia.
2. Broker/admin 0.11.3: adicionar consulta --version/-V ao admin, coberta por
   teste de processo, sem abrir configuração, rede ou estado.
3. Docker: alvo admin explícito e broker como último alvo/padrão, usuário
   10001, SIGTERM, mTLS padrão no broker, contexto com allowlist e labels
   coerentes com a versão real do binário. Sem credenciais/estado na imagem.
4. Gerar .deb Ubuntu26 amd64 (broker inclui admin), imagens DockerBookworm
   amd64, hashes e manifesto de proveniência do commit aceito. O .deb nativo
   Ubuntu NÃO será instalado na imagem Bookworm.
5. Publicar imagens versionadas lepinheiro100/xmqr-broker:0.11.3 e
   lepinheiro100/xmqr-admin:0.11.3, tag Git v0.11.3 e prerelease com .deb,
   checksums e evidência. Client segue prompt C42 e ciclo próprio.

Arquivos: Cargo.toml/lock, Dockerfile/.dockerignore, main.rs do admin,
tests/admin_cli.rs, scripts/test_distribution.py, scripts/verify_admin_image.py
e scripts/release_assets.py,
docs/plano-paridade-mosquitto.md, docs/evolution-plan.md, docs/docker.md,
README/CHANGELOG/VERSIONING, prompt e registro P78.

## Invariantes e migração

Não alterar MQTT, QoS, WAL/snapshot, quotas, autenticação, ACL, dependências,
serviços instalados, imagens antigas, tags publicadas ou material didático.
Novos testes usam somente recursos temporários e containers de nome exclusivo.
Certificados de teste nunca serão anexados ou enviados ao registry.
O admin permanece no mesmo crate, sem versão/repositório independente.
Nenhum pacote inicia serviço automaticamente. Patch de operação/distribuição;
backup e rollback offline preservados. MIT própria e direitos de dependências.

## Aceitação e validação

- Plano com todas as áreas do backlog, fontes oficiais datadas, ordem e gates;
  plano concluído não equivale a implementação, conformidade ou produção.
- Fmt, testes, Clippy, builds release e inventário de licenças em Linux.
- Testes de contrato dos Dockerfiles/contexto e consulta de versão do admin.
- Imagens: UID/entrypoint/labels corretos, binários/versões coerentes e sem
  material privado; teste mTLS pub/sub/restart/negativos em containers isolados.
- Admin: consulta de versão e operações offline em volume de teste, sem broker.
- Pacotes: conteúdo/ABI/checksum e instalação/upgrade/rollback/remove/purge
  em Ubuntu26 descartável; não operar instalação real do mantenedor.
- Commit exato aceito; tag imutável; artefatos gerados desse commit, hashes,
  digest remoto conferido após push; prerelease só após gates e anexos completos.
- Publicar apenas tags numéricas novas; não mover latest nem tags antigas.
- Registrar PASS/FAIL/BLOCKED/NOT_RUN, revisar este prompt antes de corrigir
  falhas de aceite e preservar evidência de tentativas.
