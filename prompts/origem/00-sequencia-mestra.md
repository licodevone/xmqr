# Sequência mestre dos prompts

Este arquivo define a ordem executável do projeto. A numeração dentro de cada pasta identifica a evolução daquele assunto, mas **não** substitui esta sequência mestre.

## Primeira aula — antes da trilha de segurança

Comece pelo [laboratório MQTT aberto](../docs/laboratorio-mqtt-aberto.md): broker,
assinante e publicador em três terminais, QoS 0, `127.0.0.1:1883`, sem TLS,
credenciais ou ACL. Depois desse gate, o mesmo roteiro avança separadamente
para `password-lab` (usuário/senha), `acl-lab` (ACL) e somente então
`secure-mtls` (TLS/certificados). Nenhum modo sem TLS sai do loopback.

## Regra de uso em outro computador

1. Clone o repositório inteiro; não copie somente um prompt isolado.
2. Execute primeiro a trilha `setup/` e registre os valores descobertos na máquina.
3. Nunca copie IP, porta serial, nome de usuário, diretório pessoal ou caminho absoluto de outro computador.
4. Gere certificados e segredos novos em cada ambiente. Não versione chaves privadas.
5. Antes de implementar, leia `AGENTS.md`, `CHANGELOG.md`, o prompt atual e os arquivos citados por ele.
6. Um gate reprovado interrompe a sequência. Não transforme etapa não testada em sucesso presumido.

## Sequência ativa

### Fase 0 — preparar e validar o computador

Execute `setup/00` até `setup/08`, na ordem indicada em `setup/README.md`.

Resultado: repositório clonado, WSL/Rust, Python/uv e ESP-IDF identificados, certificados locais gerados e relatório de ambiente aprovado.

### Fase 1 — reproduzir o broker MQTT 0.2.0

1. Leia `broker/00-project-context.md` e `broker/01-master-orchestrator.md`.
2. Execute `broker/31-reproduzir-validar-v020.md`.
3. Use `clients/19`–`21` como histórico da primeira fatia QoS 0 e `clients/22`–`23` para validar os recursos atuais.

Resultado esperado: QoS 0/1/2, retained e sessão persistente comprovados no ambiente novo, sem declarar conformidade MQTT completa.

### Fase 2 — corrigir pendências do núcleo MQTT 3.1.1

1. `broker/32-last-will.md`.
2. `broker/33-wildcard-subscriptions.md`.
3. Reexecute segurança, conformidade, fuzzing, interoperabilidade e desempenho pelos prompts `10`, `12`, `13`, `14` e `15`.
4. Use `broker/16-production-readiness.md` somente como gate, não como promessa de produção.

MQTT 5.0 (`broker/09`) permanece fora da sequência ativa até o núcleo 3.1.1 passar pelo gate definido para a versão correspondente.

### Fase 3 — Projeto 1: câmara fria

Execute a trilha `firmware/camara-fria/`. O ESP32 com DHT22 publica telemetria no broker; o primeiro comando físico continua sendo somente o LED de laboratório.

### Fase 4 — Google Sheets

Execute a trilha `integrations/google-sheets/`. O serviço Python é um cliente MQTT auxiliar. Ele não controla hardware e não substitui a persistência operacional futura.

### Fase 5 — Projeto 2: água

Execute a trilha `firmware/agua/` somente depois do gate do Projeto 1. O controle antitransbordamento permanece local no ESP32-C3 e deve funcionar sem internet ou broker.

## Fase futura — não executar agora

As pastas abaixo estão preservadas para a futura plataforma integrada, mas não fazem parte da sequência ativa:

- `database/`
- `backend/`
- `api/`
- integração real das trilhas `web/` e `mobile/`

Enquanto essa fase não for autorizada, web e mobile podem evoluir apenas como protótipos de interface com dados simulados. Não criar gateway MQTT/API, controle remoto real ou posicionamento como solução industrial/edge.

## Construção histórica do broker

Para estudar como o broker chegou à versão 0.2.0, use esta ordem, sem reaplicá-la automaticamente sobre o código atual:

`00 → 01 → 02 → 03 → 04 → 05 → 10 → 23 → 06 → 22 → clients/19 → clients/20 → clients/21 → 24 → 25 → 26 → 27 → 28 → 29 → 30`

Os prompts `07`, `08`, `11`–`18` são referências e gates transversais. O prompt `23` aparece antes do `22` porque autenticação e ACL precisam ser definidas antes de expor pub/sub.
