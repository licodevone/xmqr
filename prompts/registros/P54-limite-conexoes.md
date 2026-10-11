# P54 — admissão TCP configurável

Base d95fcb7. Alteração local AGENTS.md preservada e excluída do commit.
Prompt rev1 criado/apresentado antes do código. Skill xmqr-rust-mqtt aplicada.
Primeira fatia da fase1: [limits].max_connections e MQTT_MAX_CONNECTIONS,
precedência explícita, default64, faixa1..64. Quotas duráveis e formato intactos.

Validação Ubuntu26/WSL: 92 testes finais; fmt, clippy -D warnings e build dos
binários aprovados. Teste TCP/MQTT real com limite1: segunda conexão fechada e
vaga reutilizada após DISCONNECT. C27:4 integrações aprovadas, incluindo TLS,
QoS, retomada e cancelamento. Testes adicionais cobrem não Unicode, override
inválido e ausência de criação de estado. Sem alteração funcional no client.
Primeiro conjunto passou com90 testes; novos casos negativos foram adicionados
e a suíte final repetida. Nenhuma falha de gate nesta etapa.

Documentação, exemplo e changelog atualizados. Versão mantida, sem release/tag:
pacote publicado0.10.0 ainda não contém P52/P54. Sem serviços reais modificados.
Não há medição de capacidade nesta etapa; conexão TCP não equivale a sessão ou
mensagens/s. Próxima fatia exige prompt específico para limites do estado,
filas e inflight, com rejeição de reduções incompatíveis sem truncar dados.
