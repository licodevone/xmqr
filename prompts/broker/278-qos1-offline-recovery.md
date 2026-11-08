# P278 v1.0 — entrega QoS 1 offline após crash

Base `fbea7e0`. Ampliar `scripts/verify_phase6_crash_matrix.py` para
confirmar que uma mensagem QoS 1 já confirmada ao publicador enquanto o
assinante persistente estava offline sobrevive a SIGKILL e reinício.
Medir Session Present, entrega inicial sem DUP, retomada sem nova entrega
depois de PUBACK confirmado por barreira. Usar estado e tópicos sintéticos,
broker explícito e laboratório isolado. Sem mudança de wire, estado ou pacote.
Registrar resultado real e limitações do ambiente.
