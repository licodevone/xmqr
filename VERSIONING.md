# Versionamento

Broker e client têm versões independentes. Tags publicadas não são alteradas.
A base do broker é v0.9.0 (688fa4f); P47 cria o marco0.10.0 para systemd/deb.
A base do client é v0.4.0 (3e7c16a); C31 cria o marco0.5.0.

Minor0.x.0 adiciona uma fatia; patch0.x.1 corrige defeitos. Pacotes Debian usam
revisão separada (ex.:0.10.0-1). Tag identifica código; GitHub Release inclui
notas e anexos e não equivale a pacote num repositório APT.

Releases permanecem experimentais/pre-release até conformidade, interop,
recuperação e operação comprovadas. Commit/push/tag/publicação só com autorização.
Esta etapa tem autorização explícita; confirmar gates e registrar limitações
antes de tag/publicação. Não reescrever tags0.9/0.4 para incluir novos binários.

MIT, MQTT3.1.1, quotas e formato de estado preservados. MQTT5 não implementado.
1.0 depende dos gates de produção; sem promessa de API estável em0.x.
