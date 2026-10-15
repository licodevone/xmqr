# P106 — decisão $SYS

- Prompt: [P106](../broker/106-decisao-sys.md).
- [ADR 0002](../../docs/adr/0002-sys-topics.md): não gerar `$SYS` na fase 5;
  monitor HTTP loopback existente permanece o canal de agregados.
- Nenhum código MQTT mudou; B14 é decisão, não implementação nem aceite B13.
