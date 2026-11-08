# P277 v1.1 — limitar publicações por identidade autenticada

Base `fbea7e0` (candidato 0.45.0). Acrescentar `[[publish_limits]]` com
usuário, mensagens por segundo e rajada, opt-in e limitado a 256 regras.
Validar antes de iniciar em `configuration.rs` e `main.rs`. O ator mantém
baldes voláteis independentes por nome de usuário, compartilhados entre
conexões e listeners. Sem estado novo em disco e sem ampliar permissões.

Cobrar depois de ACL, geração e duplicatas QoS 2 pendentes, antes da
mutação de estado. Para MQTT 5 enviar PUBACK/PUBREC 0x97 em QoS 1/2 e
DISCONNECT 0x96 em QoS 0; MQTT 3.1.1 fecha a conexão sem ACK de sucesso.
Preservar PUBREL, obrigações aceitas, Wills e encaminhamento interno.
[OASIS MQTT 5](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html)
§2.4 e §§3.4.2.1, 3.5.2.1, 3.14.2.1.

Testar configuração, ACL, rajada, recarga, partilha entre conexões,
isolamento e recuperação. Métrica fixa `publish_rate`, sem labels de
identidade. Documentar operação e registrar PASS/FAIL/BLOCKED.

Revisão 1.1. O primeiro Clippy ultrapassou o tamanho de `run`.
Validar a incompatibilidade com `open-lab` dentro do validador de perfil
existente e repetir os gates.
