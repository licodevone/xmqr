# P94 v1 — orçamento de envio não é deadline de encerramento

2026-10-13, antes do ajuste P80/P92. Reexecução fullP80 no candidato0.11.6
falhou em não leitorQoS0 (teto5000 OU60s). Reexecução focadaTCP/mTLS1rep
passou com4672/4864envios,3.506/6.551s; isso não apaga a falha anterior.
Inspeção demonstra problema determinístico do harness: quando5000envios são
alcançados antes do prazo de escrita/fechamento, ele falha imediatamente sem
esperar o deadline60s anunciado. Batches32 também excedem teto5000 (5024).
Não atribuir falha ao runtime nem ampliar budget para esconder comportamento.

Primeiro adicionar helper/testes independentes de ação no teto, demonstrando
que5000antesdeadline não é tempo esgotado; deadline atingido continuaFAIL.
Depois usar batchmin(32,5000-sent), suspender envioQoS0 ao esgotarbudget e
aguardar/poll20ms dentroMESMO prazo60s, semPUB extra/sem permitir cliente
fixarvaga indefinidamente. IndependentePUBACK/probe, métricas e reusovaga
continuamexigidos. Registrar se esperou no teto. Falsehealthy/probefail,
cliente nãoencerrado aos60s e orçamento excedido continuam negativos.

Somente scripts/benchmark_pressure.py, test_benchmark_pressure.py e docs/
registroP94; runtime/Cargo/MIT/quotas/timeout3s/estado/TLS intocados. Reexecutar
5contratoslegados+novos efull60P80 no candidatohashd371d... em labs próprios.
Rerun30minP91 separada apósFAILdiagnóstico, sem inferiraceite por slicePASS.
Falha requer promptrev antes de novo fix; não publicarphase3antesgates.
