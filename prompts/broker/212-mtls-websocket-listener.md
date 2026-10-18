# P212 — listener MQTT sobre WSS com mTLS no broker

Entrada: broker 0.39.0 publicado; P210 aceita WS de laboratório em loopback. `main` limpo em `6b432be`; estado durável v15. Este prompt precede qualquer mudança funcional.

Objetivo: oferecer um listener WSS opt-in no perfil `secure-mtls`, reaproveitando certificado/chave/CA/CRL, rotação TLS, principal autenticado e ACL do listener TCP seguro. `MQTT_WSS_BIND` (ou `broker.wss_bind`) indica um endereço numérico com porta não zero, distinto de todos os binds TCP/WS. Sem valor, comportamento anterior intacto. O listener deve compartilhar router, limite de conexões, métricas e drenagem de shutdown com o TCP.

Escopo: configuração/startup em `src/configuration.rs` e `src/main.rs`, transporte em `src/transport/mod.rs`, fixture de fio em `scripts/`, documentação e registro. Restringir a primeira fatia a IP loopback mTLS com política ACL compartilhada; remoto, TLS-senha, navegador e política de `Origin` exigem revisões próprias. Rejeitar `Origin` sempre. Caminho `/mqtt`, subprotocolo `mqtt`, frames binários limitados e deadlines de TLS, upgrade HTTP e primeiro CONNECT. Falha de configuração ou de TLS fecha sem fallback WS aberto. Não persistir segredo nem registrar payload/certificados.

Estados/segurança: admitir antes dos handshakes; carregar a configuração TLS corrente por conexão para que a rotação existente se aplique às novas conexões WSS; extrair cadeia cliente verificada e passá-la ao mesmo vínculo de principal/ACL do TCP mTLS. TLS e upgrade recusados não criam sessão MQTT/Will. Manter limite de 64 KiB para frame WS e 4 KiB no primeiro read, e o limite MQTT existente. Sem migração de estado.

Aceite: configuração ausente/positiva/negativa; cliente com CA e certificado válidos troca MQTT 3.1.1/5 com TCP, ACL autoriza/nega por tópico; CA/certificado/hostname inválidos, ausência de certificado, `Origin`, caminho/subprotocolo, frame texto e quotas são recusados; rotação e shutdown preservam limites. Executar fmt, suíte, Clippy, build, licença/distribuição e CI da fonte exata. Registrar PASS/FAIL/BLOCKED reais e manter fase 7 global aberta. Sem mudança de versão ou tag nesta fatia.

Revisão 2 após o primeiro `cargo check`: o adaptador `WsStream` exige `Send` para o stream genérico; acrescentar essa restrição em ambas as funções auxiliares de handshake/leitura, sem alterar o contrato de rede, e repetir a compilação. O primeiro resultado é FAIL, não aceite.

Revisão 3 após Clippy: a inclusão de `wss_bind` levou `Configuration::parse` a 101 linhas e o novo braço de erro WSS ficou sem ponto e vírgula. Extrair a inserção dos binds WS/WSS em helper curto e acertar a pontuação; não relaxar o lint. Repetir o gate.

Revisão 4: Clippy recusou os nomes vizinhos `ws_bind` e `wss_bind` no mesmo escopo. Renomear as variáveis locais para deixar explícitos laboratório WS e WSS seguro, mantendo as chaves públicas existentes, e repetir o gate.
