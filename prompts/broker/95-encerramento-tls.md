# P95 v1 — encerramento TLS e espera das conexões no SIGTERM

13 de outubro de 2026, antes de reprodução/correção. P91 matriz candidata:
59 casos C43 PASS, extensão FAIL no SIGTERM do XMQR com mosquitto_sub,
exit 7 CONNECTION_LOST, sem timeout/erro de protocolo. Falha preservada em
p91-interop-candidate-1.json; não convertê-la em PASS ou culpar o peer.

Hipótese verificável: serve_connection retorna cedo se unregister falha por
actor já encerrado, antes de connection.shutdown; transport::serve solta
JoinHandles, e main aguarda apenas actor/writer. Pode sair sem close_notify
TLS. Reproduzir mTLS privado com Python SSL suppress_ragged_eofs=False e
Mosquitto 2.0.22; registrar bytes/EOF/sinal/versão/hash, sem segredos. Antes de
mudar runtime obter prova direta ou revisão v2 com causa diferente.

Se confirmada: menor correção em src/mqtt/mod.rs, src/transport/mod.rs e
src/main.rs, tests relacionados. Sempre tentar shutdown limitado do transporte
antes de propagar erro de cleanup; não esconder erro de persistência. Conter
panics como antes. Parar listener antes do barrier do actor, depois esperar
conexões/tarefas admitidas com budget TOTAL de shutdown limitado (15s), não
sleep arbitrário. Tracker existente de admission pode fornecer drain por
permits se contar inclusive handshakes e não deixar novo accept ocorrer.
Preferir essa fronteira a nova dependência ou alteração do writer/quotas.

Gates: reprodução antes/depois; teste que drain bloqueia enquanto há tarefa
admitida, libera ao fechar/drop/panic, timeout continua erro; TLS shutdown
peer não leitor permanece limitado; signal em mTLS com conexão ativa e
handshake parcial; erro do actor continua exit não-zero. fmt/test locked/
clippy -D warnings/release/license inventory, B06/P90/P80, integração admin,
P91 wire e matriz completa ambos sentidos, soak inteiro 3x600s após congelar
fonte. Sem alterar ACL/TLSCA/SAN/QoS/WAL/payload ou ampliar quotas.

Candidato broker permanece 0.11.6, ainda não tagueado/publicado. Client0.9.0
e admin0.1.0 não recebem bump por fix de broker. Novos SHAs devem substituir
artefatos candidatos antigos nos gates, sem apagar registros das falhas.
Rastrear fontes/hashes/imagens por commit exato; novas tags só após aceites.
Código próprio MIT e notices originais mantidos. Registro P95 após execução.
