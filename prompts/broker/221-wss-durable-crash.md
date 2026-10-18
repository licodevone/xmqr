# P221 — sessão WSS após queda abrupta do broker

Entrada: P218 validou parada limpa e reinício com sessão e mensagem offline WSS. Este prompt precede a campanha de crash.

Objetivo: confirmar que assinatura MQTT 5 persistente e publicação QoS 1 offline já confirmada sobrevivem a `SIGKILL` do broker e retomam por WSS mTLS com Session Present=1, sem novo SUBSCRIBE nem perda silenciosa.

Escopo: fixture efêmera de CA, mTLS, ACL e estado privado em loopback; primeiro estabelecer sessão, receber SUBACK, desconectar assinante, publicar QoS 1 e aguardar PUBACK; matar o processo do broker, reiniciar com o mesmo estado, reconectar a mesma identidade e conferir entrega/PUBACK. Executar com estado distinto do caso de parada limpa. Não modificar o broker ou serviço instalado; se houver falha, registrar antes de corrigir.

Aceite: local e CI da fonte exata PASS, regressões WSS/TCP proporcionais e registro honesto. O teste cobre um assinante e uma publicação offline; múltiplos inflight, power loss/ENOSPC e carga longa continuam fora deste recorte.
