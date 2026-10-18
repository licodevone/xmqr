# P220 — navegador real no WSS mTLS

Entrada: broker 0.42.0, client 0.36.0 e P216/P218/P219 validados por clientes de fio. Este prompt precede a campanha com navegador real.

Objetivo: executar WebSocket MQTT em Chromium real com certificado cliente, página HTTPS de origem permitida, subprotocolo `mqtt`, usuário/senha e ACL. Demonstrar publicação e assinatura MQTT 3.1.1/5, recusa de origem não listada, ausência de certificado, senha inválida e tópico proibido.

Escopo: servidor HTTPS e broker temporários em loopback, CA e certificados efêmeros, contexto de navegador descartável. Não instalar certificados na conta do usuário nem alterar o broker do WSL. O script deve se encerrar com diagnóstico claro se o navegador de teste não estiver disponível, preservando a campanha como pendente em vez de declarar aceite. `Origin` não substitui mTLS nem autenticação MQTT.

Aceite: navegação e WebSocket feitos pelo navegador, não apenas handshake HTTP manual; resultados reproduzíveis e negativos explícitos; regressões TCP/WSS proporcionais; evidência no checklist. A validação local isolada não encerra a fase 7 sem gate automatizado e matriz de regressões.
