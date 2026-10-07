# Contrato de trabalho por prompts — XMQR

1. Antes de qualquer alteração, prepare um ou mais prompts com ID, objetivo,
   estado de entrada, escopo, arquivos, limites, critérios de aceite, validação,
   compatibilidade/migração e evidência esperada. Execute apenas o pedido autorizado.
2. Confirme o repositório alvo e leia instruções locais se existirem. Nunca recrie
   o pacote existente nem sobrescreva trabalho do mantenedor. O alvo Windows é
   D:\projects\my-project\xmqr; comandos Linux exigem ambiente Linux/WSL confirmado.
   Esta cópia Windows não está automaticamente sincronizada com outra cópia WSL.
3. Leia Cargo.toml, README.md, CHANGELOG.md, VERSIONING.md, CONTRIBUTING.md,
   docs/conformance/mqtt311-status.md e a matriz prompts/COBERTURA.md. No snapshot
   inspecionado: 0.5.0 em desenvolvimento, Rust 2024, MSRV 1.88, Tokio;
   um pacote com módulos, não uma promessa de workspace multicrate.
4. Binários: mqtt-broker, mqtt-client e mqtt-admin. Configuração do servidor por
   variáveis de ambiente; TOML para usuários/ACL. Não anunciar configuração TOML
   geral, reload, API administrativa, Prometheus ou OpenTelemetry como existentes.
5. MQTT 3.1.1 é o escopo atual. QoS 0/1/2, retained, sessões, UNSUBSCRIBE e filtros
   +/# existem. Last Will e MQTT 5.0 não existem. Propostas antigas não provam features.
6. secure-mtls é o padrão: certificado, usuário/senha e ACL. open-lab,
   password-lab e acl-lab são perfis explícitos sem TLS, restritos a loopback.
   Não remover essa proteção nem reaproveitar diretório de estado entre perfis.
7. Broker e CLI: tópico/filtro até 1024 bytes UTF-8, com constante compartilhada
   após P41. Outras quotas não foram ampliadas. Pacote
   64 KiB, payload 4096, 64 sessões, 256 assinaturas, 64 offline e 32 inflight.
8. Separe codec, conexão, roteamento, persistência, segurança e transporte.
   Preserve deny-by-default, quotas, gerações de conexão e commit antes dos ACKs.
   Não registrar segredos nem confundir ACK MQTT com sucesso da aplicação consumidora.
9. Instruções próprias do XMQR estão em [AGENTS.md](../AGENTS.md); skills locais
   estão em .agents/skills e papéis TOML em .codex/agents. Consulte
   [uso e carregamento](../docs/agent-workflow.md). Nenhum agente, skill, comando
   ou MCP da origem foi instalado. Arquivo configurado não prova ativação na
   sessão; ferramentas ausentes são BLOCKED quando necessárias, nunca PASS.
10. Use OASIS como fonte normativa para mudanças de protocolo; confirme cláusulas
    exatas no trabalho futuro. Esta importação foi baseada em evidência local e
    não fez nova auditoria normativa nem executou testes funcionais.
11. Para alterações funcionais autorizadas, siga CONTRIBUTING.md: fmt, testes,
    Clippy e testes negativos/integração proporcionais. Gate externo só é aprovado
    com resultado real. Não iniciar serviço ou instalar ferramentas por ler um prompt.
12. Não mudar versão em PR comum: CONTRIBUTING.md reserva release ao mantenedor.
    VERSIONING.md governa increments/release quando explicitamente autorizados.
    Não fazer commit, push, tag, publicação ou migração destrutiva automaticamente.
13. O consumidor mqtt-broker mantém firmware, Sheets, web, mobile, API, gateway,
    banco e regras de negócio. Não introduzi-los no núcleo XMQR por esta importação.
14. Atualize o registro com resultados reais e limitações. Inspeção de código e
    existência de teste não são execução de teste. Histórico não é aprovação atual.
