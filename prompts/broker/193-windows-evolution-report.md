# P193 v1 — relatório de planejamento Windows nativo

Entrada: `main` em `9a18d26` com candidato broker 0.34.0/P192 em validação; client 0.28.0 e admin independente 0.10.0 publicados. O mantenedor esclareceu que Windows nativo é somente planejamento futuro e pediu relatório próprio.

Objetivo: criar `docs/windows-native-evolution-plan.md` com estado real dos três repositórios, dependências, ordem de trabalho, critérios de aceite e distinção entre `.exe` portável, serviço e MSI. Ligar o relatório ao item fase 9 do plano. Não iniciar implementação Windows, mudar versão, criar binário, instalador, tag ou release Windows.

Escopo de leitura: código/documentação/CI de broker, client e admin para pontos Unix-específicos, persistência, credenciais, canal administrativo, sinais, serviços e instalação. Escopo de escrita: relatório, link no plano e registro P193. Preservar P192 e arquivos do operador.

Critérios: etapas independentes com gates verificáveis em Windows real; riscos de fsync/locks/rename, ACL de arquivos, segredo, TLS/SAN, Ctrl+C/serviço, recover/rollback e compatibilidade de estado; checklists `[ ]` sem alegar Windows homologado. Validar links/caminhos e `git diff --check`. Testes funcionais são NOT_APPLICABLE para a documentação; não executar serviços Windows por este prompt.
