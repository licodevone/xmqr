# Prompt — Last Will MQTT 3.1.1

Implemente Last Will como próxima fatia vertical depois de validar a versão 0.2.0. Use OASIS MQTT 3.1.1 §§ 3.1.2, 3.1.3, 3.14 e 3.14.4 como fonte normativa e confirme os identificadores exatos antes de registrá-los nos testes.

## Trabalho pedido

1. Amplie CONNECT para validar Will Flag, Will QoS, Will Retain, tópico e payload, rejeitando combinações reservadas/inválidas.
2. Armazene o Will como parte da conexão/sessão apropriada sem persistir credenciais.
3. Publique o Will quando a rede fecha anormalmente, Keep Alive expira, ocorre erro de protocolo ou o servidor encerra a conexão nas condições previstas.
4. Cancele o Will em DISCONNECT normal antes do fechamento.
5. Defina comportamento em takeover do mesmo `client_id`, shutdown gracioso e falha antes/depois do commit.
6. Aplique ACL, limites, QoS, retained e durabilidade existentes à publicação do Will.
7. Não introduza Will Delay de MQTT 5 no núcleo 3.1.1.

## Testes obrigatórios

DISCONNECT normal, queda de socket, timeout, processo abortado, takeover, ACL negada, Will QoS 0/1/2, Will Retain, payload vazio, flags inválidas, restart e cliente externo independente.

## Gate

Cada caminho deve provar se o Will foi cancelado, publicado uma vez ou rejeitado. Atualize `CHANGELOG`, matriz de conformidade, documentação e versão somente depois das evidências.
