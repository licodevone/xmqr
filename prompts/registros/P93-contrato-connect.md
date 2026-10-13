# Registro P93 — recusas CONNECT

2026-10-13, P93v1 anterior aos testes/runtime; revisão1.1 anterior ao fix.
4 regressões TCP independentes com diretórios Linux privados e actor real.

Pré-fix, runtime ainda do baseline: cargo test --locked mqtt::connect_contract_tests
executado, 2PASS/2FAIL,0.23s: ClientID recusado e nível não suportado recebem
UnexpectedEof sem CONNACK. Nomes/flags/UTF8 malformados e IDs válidos PASS.
P91 externo0.11.5 também19casos,17PASS/2FAIL ClientIDvazioCS0/1. Falhas de
compilação anteriores do harness concorrente não foram tratadas como gapMQTT.

Fix mínimo: erro tipado de nível, resposta1; ID vazio/>256UTF8bytes resposta2
antes de auth/registro. SessionPresent0, pipeline ignorado e zero commits.
Sem formato/quota nova, sem relaxarTLS ou classificar rejeição como aceite.
Pós-fix targeted4PASS,1.04s, ambos gaps e negativos mantidos; revisão
independente sem achado runtime. Clippy byte_char_slices apenas no teste;
P93rev1.2 antes do ajuste sem alterar assert/limite. Gates completos e
matriz externa em andamento; este registro ainda não fecha fase3.
