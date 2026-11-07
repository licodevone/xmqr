# Registro P268 — versões MQTT por listener

- Prompt P268 v1.3. Entrada `85f2bf9`, Broker 0.43.0,
  branch `codex/p265-p266-xmqr-operacao`.
- `[[listener_protocols]]` limita MQTT 3.1.1, MQTT 5 ou ambos por bind
  efetivo. Política ausente aceita ambas. Rejeição de CONNECT elegível
  usa 0x01 ou 0x84 e respeita Maximum Packet Size. Verificação ocorre
  antes de autenticação e sessão. Sem migração de estado ou de ACL.
- Fmt e diff-check PASS. Windows/Cargo locked offline: biblioteca
  filtrada 248 PASS, 1 ignorado e 1 filtrado (monitor TCP); configuração
  e versão 10 PASS. Após o ajuste v1.3: 10 testes unitários do parser
  e 8 testes de configuração PASS.
- Clippy estrito bloqueado pelos avisos Unix preexistentes no Windows.
  Revisões 1.1 e 1.3 resolveram os avisos de tamanho introduzidos; Clippy
  sem promoção de avisos passou.
- A fixture TCP/WS compilou. Um teste isolado confirmou que o broker
  iniciou os listeners, mas o sandbox retornou WinError 10013 ao conectar.
  A fixture permanece na integração Unix; wire em Unix ainda pendente.
  WSL recusou acesso e Docker Desktop recusou seu pipe local.
- P259 v1.1 aponta para a matriz de fonte publicada. As cinco tags e
  respectivos commits de Broker, Client/Bridge, Admin e Managers
  conferiram com os repositórios locais.
- Candidato de fonte, sujeito ao aceite Linux/Ubuntu e verificação do
  pacote antes de tag de versão ou release.
- Envio pendente. Git e GitHub CLI falharam na resolução de DNS e a
  integração GitHub respondeu HTTP 403 (`Resource not accessible by
  integration`) ao primeiro objeto do candidato. A branch de validação,
  a execução da CI, a tag e a release não foram criadas.
