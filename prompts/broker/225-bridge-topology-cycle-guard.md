# P225 — topologia declarada e recusa de ciclos na bridge T02

Entrada: P223/P224 e C125/C126 aceitos, bridge experimental MQTT 3.1.1 unidirecional. Este prompt precede qualquer código da proteção de topologia.

Objetivo: adicionar um arquivo de topologia privado, opt-in e obrigatório quando `route.qos=1`, descrevendo as instâncias gerenciadas no mesmo domínio operacional por identidade de broker e prefixo. O sidecar deve conferir se sua própria rota está no manifesto e recusar ciclos no grafo de encaminhamento antes de abrir conexão. Rejeitar links duplicados, brokers/prefixos inválidos, ambiguidades e arquivo inseguro. Uma topologia sem ciclo deve permitir duas bridges simultâneas que encaminham em cadeia, com ACL/TLS existentes.

Limite honesto: isso evita ciclos apenas entre links declarados e controlados pelo mesmo manifesto. MQTT 3.1.1 não fornece marcador de percurso por mensagem; uma bridge externa não declarada, configuração divergente ou alteração de rota em execução não é detectável. Não declarar proteção universal nem encerrar T02. A entrega não altera payload, tópico publicado ou o broker. QoS 0 legado segue compatível sem manifesto; configuração QoS 1 existente precisa migrar para o manifesto antes de um novo release.

Aceite: ensaio de configuração com ciclo direto e longo, acíclico, manifesto adulterado/sem a própria rota, caminhos/permissões e aliases; integração com duas instâncias reais em cadeia sem retorno, negativos ACL/TLS, regressões C125/C126, fmt/test/Clippy/CI. Sem tag antes do pacote e aceite da fase 8.
