# P55 — preparação e revisão P54

## Estado

PREPARED: prompt rev1 criado antes das atualizações documentais. Implementação
P55 e testes funcionais P55 NOT_RUN. Base local broker 7d5f371, 2026-10-11.
Alteração preexistente em xmqr/AGENTS.md preservada sem modificação nesta tarefa.

## Revisão P54

Inspecionados prompt/registro P54, commit e diff, configuration.rs, main.rs,
transporte, testes de configuração e scripts/verify_connection_limit.py.
Contrato consistente: default64, faixa1..64, override explícito, validação antes
de serve/estado e uso dos permits existentes. Novos negativos cobrem overrides
inválidos e não Unicode. Não identificado defeito impeditivo nesse recorte.

O registro P54 relata 92 testes, fmt, Clippy e build aprovados em Ubuntu26/WSL,
recusa da segunda conexão/liberação da vaga e 4 integrações C27. Resultados
históricos conferidos documentalmente, sem logs brutos anexos neste registro;
não equivalem a novos PASS executados aqui. Publicação remota não verificada.

## Próximo passo e contexto

Criado prompts/broker/55-quotas-estado.md: sessões, retained, assinaturas,
offline e inflight; limites positivos até tetos atuais; recuperação e commits
com quotas coerentes; redução incompatível sem descarte. Sem código funcional,
versão/release, commit/push ou mudança no client. Atualizados contexto broker,
evolution-plan e AGENTS.md da pasta agregadora. Fase1 permanece incompleta.

## Validação desta preparação

Verificar leitura dos arquivos gravados, links locais e git diff --check.
Gates funcionais não repetidos por se tratar de prompt/contexto documental.

Resultado documental: git diff --check PASS; leitura dos arquivos PASS; links
Markdown locais dos arquivos verificados sem destinos ausentes. Nenhum teste
funcional foi executado nesta preparação.


## Execução P55 rev2 — 2026-10-11

IMPLEMENTED_LOCAL / ACCEPTANCE_BLOCKED. Base broker 4fe905ab78382678a90cc59832808939e04ef6ad; client 98b72f0fd4e63aa0bb55b39a7ad3d9784b7c78c3, sem alteração funcional no client. Ambiente Windows, rustc 1.98.1 (48a229cea 2026-09-01). wsl.exe --list --quiet retornou vazio (exit0): nenhuma distribuição disponível nesta sessão.

Implementado StateLimits tipado; parser TOML/overrides para cinco quotas; validação anterior à criação de estado; propagação ao ator/store; validação antes das transições de recuperação e de cada commit; inflight outbound/drain coerentes; encerramento do writer em recusa de documento/quota. Documento v2/leitura v1 e WAL/snapshot preservados. Atualizados README/changelog, exemplo, cobertura, contexto, plano e política de release.

### Resultados reais

| Comando/cenário | Resultado | Evidência |
| --- | --- | --- |
| cargo fmt --all -- --check | PASS / exit0 | target/p55-fmt.log |
| cargo clippy --locked --all-targets -- -D warnings | PASS / exit0 | target/p55-clippy.log |
| cargo build --locked --bins | PASS / exit0 | target/p55-build.log; linker Windows emite mensagens de criação de biblioteca |
| cargo test --locked | FAIL / exit101: 37 PASS, 25 FAIL | target/p55-tests.log; falhas de fsync de diretório Unix |
| cargo test --locked configuration::tests | PASS / exit0: 5 testes | target/p55-configuration.log |
| cargo test --locked reduced_quotas_accept_boundary | PASS / exit0: 1 teste | target/p55-quotas.log |
| cargo test --locked configured_inflight_defers | PASS / exit0: 1 teste | target/p55-inflight.log |
| cargo test --locked --test configuration | PASS / exit0: 4 testes | target/p55-process.log |
| git diff --check | PASS / exit0 | Sem erros de whitespace |
| Recuperação reduzida v1/v2, crash/Will e integração broker/client Unix | BLOCKED | Teste específico escrito sob cfg(unix); WSL indisponível |
| Interop Mosquitto, regressão TCP P54 e pacotes instalados/upgrade | NOT_RUN | Requer ambiente Unix apropriado; não há novo PASS |

Primeiros gates detectaram erros de edição sintática/propagação e Clippy de nomes/Rustdoc. Prompt revisado antes das correções; erros corrigidos e gates de compilação/fmt/Clippy repetidos. A suíte completa foi executada antes da inclusão do teste portável de drain; este teste e os demais testes afetados foram executados depois. Não alegar aprovação da suíte completa final.

### Retomada obrigatória antes de tag/release

Executar em Linux/WSL confirmado, na mesma árvore e com client independente identificado: suíte completa, negativos Unix, recuperação/redução sem perda, regressão P54 e integração C27/QoS/retained/Will/TLS/ACL pertinente. Acrescentar integração isolada de quotas em processo e evidência de startup recusado sem listener/mutação; o teste store direto não prova sozinho todo o startup. Registrar comandos e resultados reais. Corrigir eventuais falhas revisando prompt; só então aceitar P55.

Sem mudança de versão, commit, push, tag ou release nesta execução. Pedido do usuário sobre tags foi registrado em docs/README.md da pasta agregadora; critério: marco aceito, versão correta, commit exato e release com pacotes testados/checksums. Fase1 ainda aberta.

## Autorização e publicação — retomada

Usuário autorizou commits/push de cada mudança e tags após evolução. Registrar
P55 em commit com aceite Unix pendente, sem tag/release de aceite. Ambiente
continua sem WSL/Docker. Push GitHub depende de credenciais acessíveis; Git
falhou no wincredman e conector GitHub retornou403 na tentativa C36.


## Retomada P55 rev3 — 2026-10-11

IMPLEMENTED_LOCAL / ACCEPTANCE_BLOCKED. Entrada broker HEAD
10e1b59e801b3a1e5a4d79531a801e5c0b4faeb0; client independente HEAD identificado
6ee5aa87d0e1eb16c48c625408eeaf227197da14 após trabalho paralelo do client. Nenhuma
edição no client por este agente. AGENTS.md preexistente preservado sem edição.
Prompt rev3 apresentado antes das mudanças; revisões3.1/3.2 antecederam correções
de Clippy e repetição de inventário com UTF-8. Aplicadas skills locais
xmqr-rust-mqtt e xmqr-tests; implementação/testes broker em agente paralelo.

### Alterações e política de falha

Revisão identificou uma entrada live sobrevivente quando publicação de Will
falhava por saturação. O ator agora encerra conexões e fica indisponível,
preservando a imagem comprometida e pending Will. Não confirmar publicação,
substituir Will por takeover ou continuar roteando para conexão já encerrada.
Restart com quotas suficientes completa a obrigação. Listener existente pode
permanecer ligado no processo indisponível; readiness/novas operações MQTT
falham. Erros de publicação/commit de Will durante recovery aguardam shutdown
do writer antes de retornar, sem listener de startup ou lock remanescente.

Novo negativo saturado de Will preserva fila e obrigação, verifica fechamento,
recusa de restart reduzido/reabertura imediata e replay completo com defaults.
Novo tests/state_limits.rs compila em Windows e executa em Unix:12 imagens
v1/v2 x sessões/retained/assinaturas/offline/inbound/outbound, snapshot+WAL
comprometidos, porta observada, motivo de quota obrigatório, comparação byte a
byte dos arquivos e reabertura imediata do documento. Não usa cauda WAL
incompleta, portanto a recusa deve preservar fisicamente a imagem inteira.

Novo scripts/verify_state_limits.py:7 cenários reais de fronteira N/N+1,
sessões vs admissão TCP, assinaturas, retained, offline, inbound QoS2, outbound
com defer/drain/overflow e QoS0/1/2 pelo CLI independente explícito. Reutiliza
fixtures MQTT do harness existente; estados/processos temporários loopback.
Não afirma interop Mosquitto/TLS ou falha de energia.

Requisitos de Will conferidos na fonte
[OASIS MQTT3.1.1](https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html):
MQTT-3.1.2-8/-10 mantêm obrigação até publicação ou DISCONNECT; quotas/fail-closed
são política local, não nova declaração de conformidade total.

### Ambiente e resultados reais

Windows; rustc1.98.1 (48a229cea2026-09-01), cargo1.98.1 (797e8a9bc2026-08-05).
wsl.exe --list --quiet: exit0/saída vazia. Python fora do PATH encontrado em
C:/Users/licod/AppData/Roaming/uv/python/cpython-3.12.14-windows-x86_64-none/python.exe
(Python3.12.14). Nenhuma instalação ou serviço real iniciado.

| Comando/cenário | Resultado | Log local |
| --- | --- | --- |
| cargo test --locked --no-run | PASS/exit0, todos negativos novos compilados | target/p55-rev3-compile.log |
| cargo fmt --all -- --check | PASS/exit0 | target/p55-rev3-final-static.log |
| cargo clippy --locked --all-targets -- -D warnings | PASS/exit0 após rev3.1 | target/p55-rev3-clippy-final.log |
| cargo build --locked --bins | PASS/exit0 | target/p55-rev3-build.log |
| cargo test --locked | FAIL/exit101:38 PASS/25 FAIL/1 ignorado | target/p55-rev3-tests.log;25 fsync Unix |
| cargo test --locked configuration::tests | PASS/exit0:5 | target/p55-rev3-configuration.log |
| cargo test --locked reduced_quotas_accept_boundary | PASS/exit0:1 | target/p55-rev3-quotas.log |
| cargo test --locked configured_inflight_defers | PASS/exit0:1 | target/p55-rev3-inflight.log |
| cargo test --locked --test configuration | PASS/exit0:4 | target/p55-rev3-process.log |
| cargo test --locked --test state_limits | BLOCKED:exit0,0 PASS/1 ignorado por Unix | target/p55-rev3-startup.log |
| cargo test --locked saturated_will | BLOCKED:exit0,0 PASS/1 ignorado por Unix | target/p55-rev3-will.log |
| Python ast.parse scripts/verify_state_limits.py | PASS/exit0 | target/p55-rev3-python-syntax.log |
| Python scripts/verify_state_limits.py --broker target/debug/mqtt-broker.exe --client ../xmqr-client/target/debug/mqtt-client.exe | BLOCKED/exit2:Unix necessário;7 cenários NOT_RUN | target/p55-rev3-harness.log |
| Python -X utf8 scripts/license_inventory.py --check | PASS/exit0 | target/p55-rev3-final-static.log |
| git diff --check | PASS/exit0 | target/p55-rev3-final-static.log |

Primeiro Clippy falhou em too_many_lines/format_push_string no teste novo,
corrigido após revisão3.1 e repetido. Primeiro inventário Python falhou por
locale cp1252 ao ler LICENSE; revisão3.2 adotou -X utf8 e repetição PASS, sem
alterar licença/script. Mensagens linker Windows de criação .lib/.exp são
avisos; gates acima retornaram seus códigos reais. Suíte completa rodou antes
da extração textual da fixture de teste; testes afetados/Clippy foram
repetidos depois. Não declarar suíte final completa PASS. Logs target são
artefatos locais não versionados; este registro preserva comandos e resultados.

### Aceite ainda necessário

Reexecutar suíte completa em Linux/WSL confirmado e na árvore exata; executar
novos negativos de startup/Will, scripts/verify_state_limits.py com --client
explícito e repetir regressões P54/C27/Will/ACL/TLS pertinentes. Recuperação
v1/v2/redução sem perda e integrações reais continuam BLOCKED nesta sessão,
Mosquitto e pacote/upgrade NOT_RUN. Garantias fsync não foram adaptadas para
passar Windows. Fase1 permanece aberta, sem tag/release de aceite broker.

Atualizados README/changelog/configuração e prompt; coordenador atualiza plano
após resultados. Commit/push autorizados nesta retomada ficam com coordenador;
este agente não alterou versão, não fez commit/push/tag ou release.

### Coordenação/revisão final

Revisão independente do diff/fixtures não encontrou impedimento concreto ao commit. Conferidos protocolo das fixtures, documentos v1/v2, shutdown aguardado e preservação de Will; isto é inspeção, não execução Unix. Plano docs/evolution-plan.md atualizado com critérios pendentes e marco C37 do client. Links locais dos prompts/plano/configuração/C37 conferidos sem destinos ausentes.

Usuário autorizou commit/push/tag por evolução aceita. Commit desta retomada mantém aceite P55 pendente e versão broker0.10.0, sem tag/release. AGENTS.md preexistente excluído do commit. Pré-verificação git push --dry-run origin HEAD com TLS OpenSSL retornou exit128: credencial wincredman/Username GitHub indisponível, mantendo verificação TLS. Push final será tentado pelo coordenador; criação local de commit não implica publicação.

Client paralelo: C37commit6ee5aa87d0e1eb16c48c625408eeaf227197da14/tag anotada localv0.6.0,45 testes debug e45release PASS; pacote Windows ZIP/SHA-256 local validado. Push atômico commit/tag falhou por mesmas credenciais. PacoteUbuntu/interop externa NOT_RUN; fase1 permanece aberta.
