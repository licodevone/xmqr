# P227F v1.0 — controle MQTT5 com quota de envio zero

Preparado2026-10-18 antes de código. Auditoria M05 encontrou evidência de
backlog/ReceiveMaximum e publisher serial válido, mas não teste combinado
de PINGREQ/SUBSCRIBE/UNSUBSCRIBE enquanto o broker esgota a quota de envio
para o mesmo peer. OASIS MQTT5 §4.9/MQTT-4.9.0-3 e §3.3.4 não permitem
atrasar outros pacotes em razão desse limite de PUBLISH.

Criar scripts/verify_phase6_control_progress.py, CLI --broker/--report
obrigatórios, estado privado/portas efêmeras e hashes antes/depois. Testar
ReceiveMaximum1 em QoS1 antesPUBACK e QoS2 depoisPUBREC/antesPUBCOMP:
segunda mensagem fica no backlog; mesmo peer obtém PINGRESP, SUBACK e
UNSUBACK antes de liberar a primeira obrigação. QoS0 também progride.
Após ACK terminal, segunda mensagem chega na ordem e conclui sem perda.

Reusar apenas helpers wire/lifecycle privados, sem executar defaults
implícitos. Relatório exclusivo sanitizado e markerP227_CONTROL_PROGRESS_PASS
somente após todos os cenários e cleanup. Não instalar/tocar serviço, placa,
relógio, firewall ou dados do operador. Nunca copiar payload/logs ao registro.
FAIL exige revisão antes de fix; este prompt não autoriza correção especulativa
de runtime sem reprodução. Coordenador integra o gate6C e registra fonte/hash.
