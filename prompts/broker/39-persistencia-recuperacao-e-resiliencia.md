# P39 — Auditar persistência integrada e reconciliar evidências antigas

Tipo: manutenção/validação existente, com gates operacionais pendentes.
Leia mqtt/store.rs, router.rs, persistence/{mod,actor}.rs,
docs/architecture/{persistence,adr-0001-durable-persistence,rust-tokio-resilience}.md.

## Prompt de trabalho

O agregado mqtt311.state.v1 e Router integram a persistência: não reaplicar a
suposição histórica de que o WAL ainda não tem sessões MQTT. Identifique
docs/architecture/rust-tokio-resilience.md como documento desatualizado nessa
parcela; uma correção fora de prompts/ precisa de escopo próprio.
Audite escritor exclusivo fora do hot path, mailbox limitada, commit do candidato
antes de expor estado/ACK, quotas e falha fechada. Confira WAL/snapshot v1,
checksum, cauda incompleta vs corrupção completa, lock e snapshots periódicos.
Não afirmar fsync configurável, transação multichave, backup online ou segurança
contra perda real de energia sem implementação/evidência.
Audite recuperação de filtros/ACL e gerações de sessão. Preserve rollback 0.5->0.4:
remover filtros wildcard antes da parada ou restaurar backup completo anterior;
nunca misturar partes de WAL/snapshot. Verifique isolamento de panic/unwind e
consumidor lento no transporte; não transformar documentação em benchmark.

## Aceite futuro

Testes/crash autorizados em cópias isoladas antes/depois de commit, ACK e snapshot,
quota, corrupção, falha de worker/disco, revalidação ACL e restart. Separar
evidência existente, resultado da execução e operação ainda pendente. Não executar
serviço, causar falha de disco real ou tocar estado do usuário por este prompt documental.
