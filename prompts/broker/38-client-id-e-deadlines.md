# P38 — Fechar lacunas de Client ID, keep-alive e deadlines

Tipo: correção/validação proposta. Leia codec.rs, mqtt/mod.rs, store.rs,
router.rs, cli.rs e docs/conformance/mqtt311-status.md. O codec atual lê ID vazio
sem recusa própria; a matriz registra recusa de Client ID vazio como pendência.
CLI exige 1–23 caracteres restritos; estado possui limite de 256 bytes.

## Prompt de trabalho

Inspecione todo o caminho CONNECT antes de concluir seu comportamento. Prepare
política explícita conforme MQTT 3.1.1: CleanSession=0 e ID vazio, possibilidade
de ID atribuído em sessão limpa ou recusa protocolar. Confirme cláusula e CONNACK
exatos na fonte, não invente número. Diferencie restrição da CLI, capacidade do
servidor e semântica MQTT. Preserve identidade e gerações no takeover.
Audite deadlines já presentes: CONNECT/escrita 3 s, frame parcial 30 s,
keep-alive 1,5x e cap de inatividade 300 s quando keep-alive=0. Esses limites
devem ser lidos no snapshot futuro; não são novos recursos prometidos.
Não introduza timer wheel, novo TTL de sessão ou Last Will implicitamente.

## Aceite futuro

Fixtures wire independentes para IDs vazio/longos, CleanSession 0/1, resposta
e fechamento, CONNECT duplicado e antes do CONNECT, fragmentação lenta,
PINGREQ/PINGRESP, timeout e tomada do ID. Use relógio controlado quando possível;
documente cap operacional separado da regra MQTT. Não declarar gate aprovado sem execução.
