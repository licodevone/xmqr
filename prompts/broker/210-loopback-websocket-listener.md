# P210 — listener WebSocket MQTT de laboratório no broker

Entrada: broker 0.38.0 publicado; client C112 em validação de CI. Fase 7 aberta. Este prompt precede qualquer mudança funcional no broker.

Objetivo: permitir um listener WebSocket MQTT opt-in, somente no perfil `open-lab`, com bind numérico loopback e caminho `/mqtt`. Aceitar upgrade HTTP com `Sec-WebSocket-Protocol: mqtt`, transportar pacotes MQTT 3.1.1/5 binários para o mesmo router do listener TCP e preservar isolamento dos modos TLS/mTLS e senha. Recusar subprotocolo ausente/errado, URL/caminho inesperado, texto e frames acima do limite; handshake e primeiro CONNECT sujeitos a deadline.

Contrato de configuração: `MQTT_WS_BIND` não tem default, exige endereço loopback com porta não zero e distinto do `MQTT_BIND`. Não habilitar em outros perfis. Reusar o limite de admissões entre TCP e WS; evitar que duas portas dobrem o teto de conexões. Não gravar segredo ou URL em logs. O shutdown deve drenar os dois listeners antes do encerramento do router.

Aceite: fixture real de publicação/assinatura MQTT 3.1.1/5 por WS com o client C112, negativos de handshake/protocolo/caminho, frame texto, fragmentação binária, tamanho e timeout; regressão TCP e políticas de startup, shutdown e capacidade. Fmt, suíte, Clippy, build, inventário de licenças/distribuição e CI da fonte exata. Registrar evidência e limitação no checklist, sem marcar fase 7 completa. WSS com certificados, CA/SAN/mTLS e rotação fica para prompt próprio. Sem tag/release isolada.

Revisão 2 após o primeiro teste de fio: o handshake e o CONNECT MQTT 5 fragmentado chegaram ao broker, mas a fixture presumiu incorretamente que o CONNACK MQTT 5 tivesse exatamente três bytes de corpo. O broker inclui propriedades negociadas, de modo que a asserção falhou diante de um CONNACK válido. Corrigir a fixture para verificar tipo, Session Present=0 e reason code=0 independentemente do comprimento das propriedades; repetir sem contar o primeiro resultado como PASS. Fortalecer também a asserção de rejeição de frame texto para não capturar sua própria falha.

Revisão 3: os cenários de fio fragmentado e negativos passaram até o cruzamento com o client real, mas a fixture gerou um `--client-id` maior que os 23 caracteres permitidos pela CLI. Corrigir somente o ID da fixture, repetir a integração completa e manter este resultado como falha de teste, não falha do protocolo.

Revisão 4: a integração WS/TCP e a suíte Rust passaram, mas Clippy `-D warnings` encontrou o parser de configuração com 101 linhas após `ws_bind` (limite 100) e dois braços de logging sem ponto e vírgula. Extrair a inserção dos binds em uma função pequena ou reduzir o corpo sem relaxar o lint, corrigir a pontuação e repetir o gate.

Revisão 5: após as correções locais, Clippy avançou e identificou oito argumentos em `serve`, acima do limite sete. Incluir o bind WS na tupla existente de endereços, preservando a interface como um único argumento, e repetir Clippy; não relaxar o lint.

Revisão 6: o teste de fio e a suíte passaram, mas o coletor de avisos da distribuição recusou a dependência `pharos` por não haver arquivo LICENSE no crate. O client C112 já registrou suplemento verificável para `pharos` e `ws_stream_tungstenite`, com VCS/hash da declaração no README original. Aplicar a mesma checagem exata no broker, repetir coleta, inventário e distribuição; não aceitar o resultado anterior do coletor.

Revisão 7: ao ampliar o teste de shutdown, a fixture tentou abrir WS imediatamente após fechar um cliente TCP com quota global 1 e recebeu reset. O socket TCP ainda estava sendo drenado pelo broker; a tentativa imediata não prova vazamento de quota. Enviar DISCONNECT MQTT no TCP e aguardar em prazo limitado a liberação da vaga antes de afirmar o shutdown com WS ativo. Repetir o cenário.

Revisão 8 de segurança antes do CI: o perfil `open-lab` não autentica nem aplica ACL, e um navegador em uma página externa pode tentar WebSocket em loopback. Recusar todo handshake que contenha `Origin` neste primeiro listener local para CLI; testar o negativo. Suporte a navegador requer prompt posterior com allowlist explícita de origem e política de autenticação adequada. Documentar esta limitação sem declarar a fase 7 completa.

Revisão 9: a repetição completa após a política de `Origin` encontrou outra forma transitória da corrida de quota na fixture de shutdown: o socket WS fechou antes do cabeçalho HTTP completo, expresso por `AssertionError` da leitura exata, enquanto a espera só tratava `OSError`. Repetir apenas essa falha específica até o prazo limitado; erros de resposta HTTP continuam falhando. Reexecutar o teste de fio e o gate completo.
