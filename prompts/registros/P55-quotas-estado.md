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
