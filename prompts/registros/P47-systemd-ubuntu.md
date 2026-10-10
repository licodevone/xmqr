# P47 — systemd e Ubuntu26

Data:2026-10-10. Prompt:../broker/47-systemd-ubuntu.md rev1.
Base:688fa4f/tagv0.9.0, árvore limpa. Implementação/commit/push/prereleases
autorizados explicitamente. Ubuntu26.04/WSL amd64, Rust1.99.0, systemd259.
Novo marco0.10.0, sem reescrever tags ou histórico.

## Implementação

SIGTERM/SIGINT fecham listener e enviam barreira ao ator. Comandos anteriores
são processados; estado candidato preserva sessões persistentes/inboundQoS2,
remove clean sessions e publica Wills com vista offline, commit antes de
snapshot/shutdown do writer. ACK/quotas/ACL/formatos/MIT preservados.
Timeout15s interno20s unit. Type=simple, conta dedicada, StateDirectory privado,
hardening, restart limitado; SIGHUP limitado ao bundle dinâmico.

Pacote deb gerado em Ubuntu26 com dependências ABI calculadas, ownershiproot
do payload, conffile env, usuário xmqr, estado0700. Não habilita/inicia
automaticamente. Upgrade/remove param serviço; upgrade exige start explícito.
Remove preserva config/dados; purge remove conffile do pacote, preserva dados,
credenciais externas e conta. CI adiciona teste de sinais e build/deb Ubuntu26.
README/VERSIONING alinhados; registros históricos preservados.

## PASS executado

- WSL:fmt --check,test --locked --offline (83 testes),Clippy all-targets
  -Dwarnings, build debug/release bins. Inventário license_inventory --check.
- scripts/verify_shutdown.py:3 cenários PASS (SIGTERM Will/retained/offline sem
  duplicata; SIGINT inboundQoS2 após restart; falha snapshot não anuncia sucesso).
- scripts/verify_last_will.py:9 regressões PASS com client independente.
- client validation/C29-integration.py:1 cenário múltiplos filtros PASS.
- scripts/verify_systemd.py como root, --test-user licod26: PASS com units
  temporárias /run, estado próprio /var/lib/xmqr-test-UUID, certificados/credenciais
  públicas de teste. Serviços executaram como usuário não root, com hardening:
  mTLS pub/sub, reload, restart, stop, exit0 e snapshot. Cleanup removeu somente
  recursos de teste. Units usam paths e usuário de teste, não os de produção.
- Docker Ubuntu26 limpo:apt install deb, systemd-analyze verify units, usuário
  criado e serviço não habilitado. Upgrade revisão1→2 preserva edit em conffile.
  Remove/purge preservam dados e credenciais externas. packaging/test_package.sh
  reproduz o ciclo; revisões2 são só artefatos de teste, não releases.
- Docker Ubuntu26 + Mosquitto clients:scripts/verify_interop.py:4 testes PASS,
  QoS0/1/2, wildcards/overlap, retained/restart/$, sessão/UNSUBSCRIBE e negativos.
- Windows:cargo check --locked --offline --all-targets PASS nos dois projetos.
  Não equivale a runtime durável Windows.

## Falhas durante desenvolvimento, corrigidas

Clippy detectou serve com105 linhas: limite local explicado para dispatch de
perfis. FixtureQoS2 omitia retain no frame, corrigida para0x35. Teste systemd
usava ClientID longo e marcador JSON incorreto; corrigidos. Smoke inicial
invocava mqtt-admin --help como sucesso, mas CLI retorna1; gate corrigido.
systemd-analyze da árvore WSL antes da instalação recusava bins ausentes;
verificação válida passou no payload instalado e units temporárias.

## Limitações / NOT_RUN

Não há repositório APT próprio assinado/destino configurado. Deb local via apt
e anexos GitHub são a distribuição inicial. Ubuntu24/arm64/MSRV1.88 exato não
validados. Não há sd_notify/Watchdog nem promessa de readiness via active.
Mosquitto externo validado em open-lab; não alegar Mosquitto mTLS completo.
Testes de parada não comprovam perda de energia ou produção. Docker atual pode
ser reconstruído com nova versão; imagem nova não publicada em registry.
Não houve instalação/ativação permanente no WSL ou alteração de estado real.

Commit/push/tag/releases executados após gates; hashes/URLs registrados no Git
e na resposta final, não presumidos neste documento antes da criação.
