# ADR-0006 — fronteira de recarga da configuração (B12)

Status: decisão da fase 4, 2026-10-15. O arquivo `MQTT_CONFIG` v1 é lido
somente no início do processo. Editá-lo não muda o broker em execução.

| Entrada | Aplicação atual | Motivo |
| --- | --- | --- |
| Bundle privado de usuários, papéis e ACL | SIGHUP, apenas quando bundle dinâmico foi ativado | O candidato é validado antes da publicação; conexões dinâmicas são encerradas para reautenticar. |
| Certificado/chave do servidor e CA/CRL dos clientes | SIGUSR1 (P100/B11), mesmos caminhos de startup | Candidato TLS completo validado antes de trocar os novos handshakes; falha conserva geração anterior. |
| Bind primário/adicionais, perfil `MQTT_MODE`, diretório de estado | Restart-only | Mudam sockets, fronteira de identidade e ownership do estado durável. |
| Limites de conexão, sessões, assinaturas, offline e inflight | Restart-only | Redução pode contradizer estado/admissões já existentes. |
| Monitor habilitado/bind e demais campos do TOML | Restart-only | Precisam ser preparados e validados junto do processo. |
| Arquivos legados de usuários/ACL | Restart-only | Não participam do watcher de bundle. |

Um reload geral futuro só poderá publicar um snapshot candidato depois de
validar **todos** os campos suportados e reservar recursos necessários. Se um
passo falhar, nenhum campo do candidato deve ficar ativo. Campos que exigem
restart devem produzir resposta explícita de recusa, sem aplicação parcial.
Conexões aceitas antes de uma rotação TLS usam sua sessão TLS original; a
mudança de CA/CRL só vale para novos handshakes, portanto a revogação imediata
de conexões ativas exige encerrá-las por operação controlada. A troca de
política de segurança continua tendo o contrato próprio de SIGHUP. Operações
simultâneas de segurança e TLS não constituem um reload geral atômico.

Rollback operacional: manter os arquivos e configuração anteriores, restaurar
o conjunto aceito e aplicar o mecanismo correspondente; uma falha de validação
preserva automaticamente o snapshot em memória. Não prometer reversão de
efeitos MQTT já confirmados ou de conexões encerradas.
