# P234 v1.0 — provar rejeição de texto WS/WSS no client

Data: 2026-10-19. Entrada broker `d25f9e9`, acompanhamento P233 em preparo;
client candidata 0.42.1 `db844a0`, ELF extraído do pacote de CI `39257417702`.
P232 deixou MQTT-6.0.0-1 como EVIDENCE_GAP no papel Client. A dependência
fixada ws_stream_tungstenite 0.15.0 contém fechamento em ReceivedText; ainda
falta evidência externa no executável. Sem falha de produto presumida.

Referência conferida: OASIS MQTT 5.0 OS, §6, MQTT-6.0.0-1/-2/-3/-4,
https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html . MQTT usa
quadros de dados binários; recebimento de outro tipo de dado exige fechamento.
PING/PONG/CLOSE são controles WebSocket, não dados proibidos.

Objetivo: fixture externa de servidor sintético em scripts, com MQTT 3.1.1/5,
WS loopback e WSS mTLS/CA/SAN reais temporários. Em cada combinação, controle
binário com fragmentação/concatenação, texto contendo CONNACK válido e texto
contendo PUBLISH válido após SUBACK. Texto deve causar fechamento rápido,
saída de erro e nenhuma entrega/ACK de sucesso; mesmo conteúdo binário deve
passar. Não considerar timeout do comando como rejeição válida.

Não alterar runtime nem oráculos históricos. Parser de frames independente
do produto, respeitando mask/controle e limites; binário e helpers identificados
por SHA-256; fonte declarada explícita, portas efêmeras e cleanup com prazos.
Certificados/senhas gerados e nunca registrados. Report JSON exclusivo novo.

Aceite: 12 casos PASS, binário inalterado, registro/relatório e acompanhamento
P233 com escopo exato. Se houver FAIL, preservar relatório e revisar prompt
antes de corrigir produto ou harness. Após release C146, CI Ubuntu26 extrai
pacote publicado com hash fixado e executa a fixture sem instalar o pacote.
Sem novos Rust gates só para a prova externa; sem tag/release do broker.

## v1.1 — erro do simulador antes dos pacotes MQTT

A primeira execução gerou 12 FAILs de TypeError ao construir o dicionário
de cabeçalhos HTTP com chaves bytearray não hasháveis. Nenhum caso chegou
a exercitar MQTT: não é falha do produto. Preservar o relatório original
`p234-package-ws.json`; converter o buffer HTTP completo para bytes antes de
interpretar campos e repetir os mesmos 12 casos em um relatório novo, sem
alterar os critérios. Não atribuir PASS retroativo à primeira execução.
