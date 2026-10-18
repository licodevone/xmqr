# P219 — fragmentação e limites de quadros WSS

Entrada: broker 0.42.0; WS local já tem vetores de fragmentação, texto e tamanho. P218 cobre reinício de sessão WSS. Este prompt precede os novos vetores WSS.

Objetivo: transportar MQTT 3.1.1/5 em quadros binários WSS fragmentados sem alterar roteamento ou ACL e recusar quadros de texto e payload acima do limite, mantendo o listener disponível para novas conexões.

Escopo: ampliar a fixture mTLS descartável existente, com certificados efêmeros e TCP de controle. Testar CONNECT fragmentado com continuação, pub/sub após fragmentação, frame de texto inválido, frame binário maior que 64 KiB, fechamento e nova conexão saudável. Respeitar os limites já documentados; não mudar configuração de produção sem necessidade.

Aceite: fixture local e CI da fonte exata PASS; regressões WS aberto, WSS MQTT/ACL, TCP e pacote Ubuntu sem alterações. Registrar apenas o recorte validado no plano. Navegador real e matriz global continuam abertos.
