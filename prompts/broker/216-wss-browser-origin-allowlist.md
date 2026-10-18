# P216 — lista explícita de origens para navegador WSS mTLS

Entrada: broker/admin legado 0.41.0 e client independente 0.34.0 publicados. WSS mTLS remoto P214/C117 funciona, mas qualquer handshake com `Origin` é recusado. Este prompt precede a alteração funcional.

Objetivo: permitir navegador em WSS mTLS apenas com lista explícita de origens HTTPS exatas, mantendo recusa padrão. `Origin` controla a origem da página e não substitui certificado cliente, CONNECT com usuário/senha, ACL ou autorização de tópico. O WS aberto `open-lab` continua recusando `Origin`.

Escopo: `MQTT_WSS_ALLOWED_ORIGINS` e TOML `broker.wss_allowed_origins` (lista) somente quando há WSS `secure-mtls`. Validar origem HTTPS absoluta sem userinfo, path, query, fragmento, wildcard, `null`, duplicata, espaço ou valor vazio. Comparação exata/canônica; aceitar somente uma origem configurada, recusar origem diferente/malformada/múltipla. Não logar certificados ou credenciais. Lista vazia equivale à política padrão de recusa. Estado v15 sem migração.

Aceite: unitários de configuração e parser, handshake real com certificado cliente e `Origin` permitido/negado, MQTT 3.1.1/5 pub/sub com ACL, negativos sem certificado/senha/CA, regressões WSS sem `Origin`, WS `open-lab` e TCP/TLS, fmt/suíte/Clippy/distribuição/licenças e CI da fonte exata. Aceite parcial da fase 7; navegador completo, durabilidade por URL e regressões de produção ainda exigem campanha própria. Sem release automática antes dos gates.
