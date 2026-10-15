# P96 rev1 — primeira fatia B09: endpoints mTLS compartilhados

2026-10-15. Entrada cce3549, broker0.11.6, client0.9.0, admin0.1.0; árvores limpas.
Fases1/2/3 aceitas; conferir registros P92/P95. Pedido autoriza evolução dos
três projetos, commits/push/tags aceitas; releases conforme artefatos disponíveis.

Objetivo: até3 binds mTLS adicionais via broker.additional_binds no TOML v1,
com um roteador/estado/política, teto global de conexões e IDs únicos globais.
Scope: configuration.rs, main.rs, transport/mod.rs, testes, harness externo,
docs configuração/paridade/checklist, CHANGELOG/manifests0.12.0 e registroP96.

Contrato: opt-in/restart-only, somente secure-mtls; lista vazia preserva defaults.
Recusar duplicação, porta0 e bind inválido, wildcard/sobreposição e mais de3
adicionais antes do listener. Não anunciar políticas distintas por listener:
B09 continua parcial. B10 TLS sem certificado e B11 rotação não entram aqui.
Falha em qualquer bind impede operação; shutdown cancela todos os accepts e
drena os mesmos permits. Preservar fingerprint/senha/ACL, QoS e estado existentes.

Aceite: configuração negativos e default; integração2endpoints mTLS, pub/sub
cruzado nos3QoS, teto agregado N/N+1/liberação/restart/retained e bind ocupado;
regressõesTLS/shutdown. Recursos temporários e credenciais de teste, sem tocar
serviços reais. Gates fmt/test/clippy/build/inventário Ubuntu26; revisão segurança.
Migração: TOMLv1 opt-in, estado inalterado; rollback exige remover campo novo.
Prompt revisado antes de corrigir falhas; somente PASS real autoriza tag0.12.0.

## rev2 — fixtures de configuração

Primeiro cargo test recusou uma construção literal de Configuration sem o
novo campo. Atualizar fixtures com Default, preservando semântica anterior;
repetir testes e gates. Não alterar limites para contornar falhas.

## rev3 — compilação do servidor

O gate `cargo test --locked --no-run` no Ubuntu 26 encontrou E0425 em
`main.rs`: `run` calcula `additional_binds`, mas não o entrega a `serve`.
Passar a lista validada explicitamente à função e repetir compilação. Se
aparecerem problemas de concorrência nos accepts, preservar a mesma política,
limite e barreira de desligamento para todos os listeners.

## rev4 — lint do teste de configuração

Os testes Rust passaram, mas Clippy com `-D warnings` recusou `assert!` sobre
`is_empty` no teste novo. Ajustar a asserção para a forma recomendada, sem
alterar o comportamento, e repetir o gate completo.

## rev5 — assinatura de serve

O lint seguinte encontrou 8 argumentos em `serve` após acrescentar a lista.
Agrupar endereço primário e adicionais no mesmo parâmetro, mantendo a
validação anterior e a partilha de recursos, e repetir Clippy/build.

## rev6 — teste externo após reinício

O harness comprovou os dois endpoints, QoS0/1/2 cruzados, teto N/N+1 e
retained após reinício. A última asserção de bind ocupado falhou com EADDRINUSE
por TIME_WAIT do socket de prova, não por processo ativo. Reutilizar endereço
no socket de verificação e repetir a campanha, mantendo o teste de recusa do
segundo bind e a saída do processo.

## rev7 — ambiente do inventário

O inventário foi chamado sem o PATH do Rust no Ubuntu26; falhou antes de ler
dependências porque `cargo` não foi encontrado. Reexecutar com o PATH usado
nos gates Rust. Nenhum código ou inventário foi alterado por essa falha.

## rev8 — corrida no teste de persistência durante o gate final

Depois da atualização de versão, o gate paralelo encontrou `AlreadyOpen` em
`persistence::tests::actor_acks_after_commit`, teste não modificado que passou
antes. Investigar se o shutdown confirma o fechamento do lock antes do retorno;
repetir isolado e depois a suíte sem concorrência externa. Não declarar PASS
por mero retry se a corrida for reproduzível.

## rev9 — credencial do harness

A revisão de segurança observou uma senha de fixture literal no novo harness.
Gerar a senha apenas no diretório temporário durante o teste, transmiti-la ao
utilitário de hash pelo PTY (não por argv) e não imprimi-la na saída. Repetir a
campanha release após essa alteração. O código de produção não muda.
