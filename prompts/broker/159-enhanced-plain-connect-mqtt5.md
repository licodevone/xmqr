# P159 rev1 — autenticação inicial MQTT 5 com SASL PLAIN sobre TLS

Entrada: P158 classifica método desconhecido com 0x8C; broker 0.27.0 já autentica usuário/senha pela política escolhida no CONNECT convencional. M10 requer um método definido antes de aceitar AUTH.

Objetivo: aceitar `Authentication Method="PLAIN"` no CONNECT MQTT 5 com `Authentication Data` no formato RFC 4616 `[authzid] NUL authcid NUL passwd`, sem desafio adicional. Exigir transporte TLS e authzid vazio (sem delegação); encaminhar authcid/senha à mesma política de identidade, certificado e ACL usada pelo CONNECT convencional. Recusar combinação com Username/Password do CONNECT, dados ausentes/malformados, identidade vazia, método diferente e qualquer tentativa em transporte aberto antes de criar sessão. Nunca registrar/copiar para diagnóstico o dado de autenticação. No sucesso, CONNACK inclui Authentication Method `PLAIN`, respeitando Maximum Packet Size antes do registro da sessão; erro de credenciais não cria estado. `AUTH` pós-CONNACK e reautenticação ficam em P160.

Aceite: testes de parser e transporte TLS real para sucesso/erro e política de cert/senha; limites de comprimento, UTF-8/NUL, duplicata, ausência de dados, limite CONNACK, nenhuma escrita em falha, regressões CONNECT 3.1.1/5 e P158. Interoperabilidade com client C91. Fmt/test/Clippy/build/licenças/CI do commit exato. Registrar como fatia inicial, sem declarar AUTH/reautenticação ou fase 6D concluídos. Sem tag/release isolada, WSL do operador ou ESP32 físico.

Fontes normativas: [OASIS MQTT 5 §4.12](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html) e [RFC 4616 SASL PLAIN](https://www.rfc-editor.org/rfc/rfc4616).
