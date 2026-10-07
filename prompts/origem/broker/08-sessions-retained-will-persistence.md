# Prompt — sessões, retained, Will e persistência

Defina agregado de sessão, ownership por client ID, epoch da conexão e conteúdo persistido. Modele clean session/start, expiry, assinaturas, fila offline, inflight nos dois sentidos e takeover.

Defina retained separadamente de mensagens normais: substituir, remover com payload vazio, expirar e entregar durante SUBSCRIBE. Modele Will, cancelamento em desconexão normal e atraso MQTT 5 quando aplicável.

Para persistência, declare atomicidade, fsync/durabilidade, recuperação, corrupção, compactação, migração e quotas. Construa testes de crash em pontos de commit e prove que a recuperação não confirma dados inexistentes nem perde estado já confirmado segundo a configuração.

