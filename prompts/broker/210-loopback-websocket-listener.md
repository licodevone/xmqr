# P210 — listener WebSocket MQTT de laboratório no broker

Entrada: broker 0.38.0 publicado; client C112 em validação de CI. Fase 7 aberta. Este prompt precede qualquer mudança funcional no broker.

Objetivo: permitir um listener WebSocket MQTT opt-in, somente no perfil `open-lab`, com bind numérico loopback e caminho `/mqtt`. Aceitar upgrade HTTP com `Sec-WebSocket-Protocol: mqtt`, transportar pacotes MQTT 3.1.1/5 binários para o mesmo router do listener TCP e preservar isolamento dos modos TLS/mTLS e senha. Recusar subprotocolo ausente/errado, URL/caminho inesperado, texto e frames acima do limite; handshake e primeiro CONNECT sujeitos a deadline.

Contrato de configuração: `MQTT_WS_BIND` não tem default, exige endereço loopback com porta não zero e distinto do `MQTT_BIND`. Não habilitar em outros perfis. Reusar o limite de admissões entre TCP e WS; evitar que duas portas dobrem o teto de conexões. Não gravar segredo ou URL em logs. O shutdown deve drenar os dois listeners antes do encerramento do router.

Aceite: fixture real de publicação/assinatura MQTT 3.1.1/5 por WS com o client C112, negativos de handshake/protocolo/caminho, frame texto, fragmentação binária, tamanho e timeout; regressão TCP e políticas de startup, shutdown e capacidade. Fmt, suíte, Clippy, build, inventário de licenças/distribuição e CI da fonte exata. Registrar evidência e limitação no checklist, sem marcar fase 7 completa. WSS com certificados, CA/SAN/mTLS e rotação fica para prompt próprio. Sem tag/release isolada.

Revisão 2 após o primeiro teste de fio: o handshake e o CONNECT MQTT 5 fragmentado chegaram ao broker, mas a fixture presumiu incorretamente que o CONNACK MQTT 5 tivesse exatamente três bytes de corpo. O broker inclui propriedades negociadas, de modo que a asserção falhou diante de um CONNACK válido. Corrigir a fixture para verificar tipo, Session Present=0 e reason code=0 independentemente do comprimento das propriedades; repetir sem contar o primeiro resultado como PASS. Fortalecer também a asserção de rejeição de frame texto para não capturar sua própria falha.

Revisão 3: os cenários de fio fragmentado e negativos passaram até o cruzamento com o client real, mas a fixture gerou um `--client-id` maior que os 23 caracteres permitidos pela CLI. Corrigir somente o ID da fixture, repetir a integração completa e manter este resultado como falha de teste, não falha do protocolo.
