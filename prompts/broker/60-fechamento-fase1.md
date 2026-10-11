# P60 rev1 — coordenação do aceite da fase 1

Entrada: broker57d23c0d3008ad869f81b89abe243c3e9790ee85, client6ee5aa87d0e1eb16c48c625408eeaf227197da14, árvores limpas antes dos prompts paralelos P58/P59/C38. Pedido atual: finalizar fase1; autorizações persistentes para agentes paralelos, commits/push e tags de evoluções aceitas, releases quando necessárias.

Objetivo: conferir todos os critérios de saída, reunir evidência atual e fechar fase1 somente após aprovação real. Escopo do coordenador: docs/evolution-plan.md, docs/phase1-acceptance.md e prompts/registros/P60-fechamento-fase1.md; revisão dos diffs das entregas independentes e publicação autorizada quando os gates técnicos forem satisfeitos. Implementação/código/testes pertencem aos agentes de P58/C38/P59; preservar trabalho compartilhado.

Critérios obrigatórios: quotas TOML/defaults/negativos; recuperação/redução sem truncar dados em Unix, imagensv1/v2 e Will saturada; teto uniforme de pacote completo65536 e payload4096 com N/N+1; integração broker/client com C37, QoS/retained/fila/inflight e regressãoTCP; interop independente pertinente; pacote instalado/upgraded/rollback testado em Ubuntu isolado. Confirmar artefatos/hash/commits exatos antes de tag/release. Não afrouxar fsync, TLS/SAN, loopback, ACKs, quotas ou critérios para contornar plataforma ausente.

Compatibilidade: documentos MQTT/WAL/snapshot e defaults preservados; mudança de contagem do pacote documentada em P58/C38. Versões independentes; sem novas dependências/workspace. Não avançar à fase2. Tags existentes imutáveis. Falhas exigem registro e revisão do prompt responsável antes de correção.

Validação documental: links/formatos e git diff --check. Validações funcionais: aproveitar somente resultados atuais das árvores finais, comandos/logs/códigos explícitos dos agentes; coordenador verifica evidência/escopo e não promove testes ignorados a PASS.

Ambiente inicial: WindowsRust1.98.1; exec_command falha setup refresh, leitura/execução por node_repl fs/child_process. WSL lista vazia; sem Docker/bash/podman no PATH. Python3.12 acessível em caminho UV já instalado. Pergunta assíncrona ao usuário solicita ambiente Linux já disponível; continuar trabalho independente enquanto aguarda. Sem ambiente Unix/Ubuntu acessível, estado de fechamento será ACCEPTANCE_BLOCKED e informar exatamente o que falta; não criar tag de aceite da fase nem release de pacote não testado.
