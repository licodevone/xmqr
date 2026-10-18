# P218 — retomada WSS mTLS após reinício do broker

Entrada: broker 0.42.0 e client 0.36.0 publicados; C123 demonstrou mensagem offline WSS com broker contínuo. Este prompt precede o ensaio e qualquer correção funcional.

Objetivo: verificar que uma assinatura MQTT 5 persistente por WSS mTLS sobrevive ao encerramento limpo e reinício do broker com o mesmo estado privado. O client deve receber uma publicação feita enquanto desconectado, sem novo SUBSCRIBE, apenas quando CONNACK indicar Session Present; o manifesto local precisa permanecer íntegro.

Escopo: fixture descartável Ubuntu/WSL com CA/certificados efêmeros, usuário mTLS, ACL restrita, portas locais, diretórios temporários e broker/client reais. Exercitar assinatura inicial, parada do client, publicação QoS 1, reinício limpo do broker, reconexão WSS com URL/identidade iguais, entrega offline e ACK após saída. Conferir também que URL diferente é recusada sem modificar o manifesto. Não alterar serviço instalado nem divulgar senhas. Se a retomada falhar, registrar a falha e corrigir antes de assinalar aceite.

Aceite: fixture reproduzível integrada à CI da fonte exata, regressão WSS e TCP proporcionais, verificação de CI e registro no checklist. Este aceite é parcial da fase 7; navegador real e matriz de regressões completa permanecem abertos. Release apenas quando houver marco de distribuição justificável.
