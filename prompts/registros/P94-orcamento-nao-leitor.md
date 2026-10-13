# P94 — orçamento de envio e deadline do peer não leitor

13 de outubro de 2026. Prompt P94 v1 antes dos ajustes do harness. A campanha
full inicial falhou; uma repetição focada TCP/mTLS passou, sem apagar a falha.
Inspeção encontrou 5000 envios tratados como deadline temporal e batches que
podiam exceder o teto. Nenhuma alteração de runtime foi feita por P94.

Helper nonreader_batch e dois testes distinguem esgotamento de envio de prazo
expirado. Agora o lote respeita exatamente o teto; depois dele, o harness
aguarda/poll dentro do mesmo deadline de 60s, sem continuar enviando. Fechamento,
reuso da vaga, PUBACK independente, métricas e saúde continuam exigidos.
Sete contratos Python PASS, incluindo os cinco anteriores.

Campanha final-v3, arquivo ignorado dist/p92-pressure-final-v3.json:
60/60 PASS, três repetições de dez cenários em TCP e dez em mTLS. Limites de
conexões 1/8/32/64, timeout inicial, pressão/restart/drain QoS1/2 e não leitor
QoS0. Estado privado em /var/tmp no filesystem nativo do WSL. SHA do broker
d371d2834bc8f0d0f0bbd02ecd76393e4b8a88fb78465f5ed85fa7cad6b88903;
harness 581a01c8f12ded1fa8de4c64cf797c61c16aa065aed07231d6b925d36cc3035d.
A tentativa v2 não iniciou por erro do serviço WSL, não é resultado do broker.

Limites: campanha finita, não throughput máximo/SLA; CPU/RSS amostrados,
monitor habilitado, interferência do host. Crash não comprova power loss;
ESP32 físico NOT_RUN. P95 detectou outra falha de encerramento TLS após esta
campanha: o candidato corrigido precisa repetir gates. Este registro não
encerra B08 nem autoriza publicar fase 3 sem soak/interop finais.
