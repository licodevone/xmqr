# Prompt — máquina de estados da conexão

Modele a conexão desde o accept até o encerramento. Antes de CONNECT, apenas CONNECT é permitido; imponha timeout, versão negociada, autenticação, keep alive e uma única identidade de cliente.

Defina tabela de transições para handshake, conectado, draining e fechado. Inclua takeover de client ID, clean session/start, keep-alive 1,5×, DISCONNECT normal, EOF, erro de protocolo, falha de escrita e shutdown do servidor.

Implemente cancelamento estruturado, filas limitadas e um único owner do socket. Teste pacotes fora de ordem, CONNECT duplicado, clientes lentos, half-close, timeout e corrida entre takeover e reconnect.

