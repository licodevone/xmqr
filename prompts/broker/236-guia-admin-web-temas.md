# P236 v1.0 — operação atual do admin e temas no curso HTML

2026-10-19. Broker main195f9c2 limpo, adminA25 publicado na fonte4c664cf,
aceite local concluído/CI pendente; admin distribuído0.11.0 sem A23–A25.
Usuário solicita incluir novos passos em ../docs/code-guide.html e oferecer
modo claro/escuro. Guia local existe,3.6MB, gerado pelos scripts deste repo.

## Escopo antes do código

- Preservar curso existente e fontes históricas; atualizar o arquivo pedido,
  sem regenerar exemplos de código a partir de trabalho clientC148 não aceito.
- Acrescentar seção/aulas de operação atual do admin com sidebar de títulos
  idênticos, âncoras únicas, expansão/fechamento, busca e checklist manual honesto.
- Explicar broker/client/admin; painel9080, monitor9090/ready e TLS8883;
  tecnologias HTML/CSS/JS nativos + Rust/Axum/Tokio/HTTPJSON.
- Distinguir release distribuída de fonte recente (A23console,A24contas,A25status).
  Comandos de compilação/execução devem usar explicitamente binário da fonte
  correta, sem prometer A24/A25 no pacote antigo. Incluir instalação/contexto
  WSL vs caminhoWindows /mnt/d e confirmação de versão dos três programas.
- Token-init seguro0600, sem sobrescrever existente; bootstrap sóprimeiroadmin,
  senha pessoal escolhida no navegador/Argon2id, papéis, cookie/CSRF/logout,
  perfisMQTT separados e arquivos de senha privados. Sem credenciais reais.
- Explicar indicadores: broker ready pelo monitor; client somente assinatura
  compartilhada após SUBACK; admin resposta válida; perda de contato invalida
  estados sem afirmar morte do broker. Poll3s + duração da consulta.
- Procedimentos completos de limpeza: parar processos próprios/serviços,
  backup privado e movimentação com variável definida no mesmo subshell,
  set-eu e validação de destino; jamais mover pasta para dentro dela mesma.
  Retém pacotes e /var/lib/xmqr. Não executar limpeza nem exclusão nesta tarefa.
- Exclusão de backup: listar, escolher nome real sem copiar ABCD1234;
  comando com caminho validado sob /var/backups/xmqr-reset-*, sem wildcard
  destrutivo, rm-rI pede y/n em inglês; inexistente não significa perda de dados.
  Evitar exemplo executável com nome fictício que foi fonte de erro no chat.
- Novo bootstrap após reset não restaura senha/certificado antigo. Não incluir
  token,senha,CAprivada,cookie,URLsprivadas ou estado do operador no HTML/Git.
- Fase8 permanece aberta: bridgeC148/percursoMQTT5durável/ciclos/aceite e
  distribuição pendentes. Não afirmar certificação MQTT5 integral.

## Tema e manutenção

Modo claro e escuro acessíveis por botão visível desktop/mobile, default pela
preferência do sistema quando não há escolha, preferência local persistida.
Falha/bloqueio de localStorage não quebra a navegação. Texto legível, foco
visível, contrastes coerentes em fonte/pre/tabelas/sidebar/formulários.
Inicialização de tema no head antes da pintura; print mantém estilo legível.
Sem bibliotecas/recursos remotos novos. Preferência visual não contém segredos.

Implementar extensão idempotente versionada em scripts/guide_admin_panel.py
e scripts/guide_theme.py, conteúdo em docs/course-admin-web.html (fragmento).
Ligar extensões à geração existente e oferecer atualização do HTML existente
sem refazer o snapshot histórico. Arquivos isolados por agente, sem concorrência
de edição no HTML final. Documento ../docs fica fora dos três Git roots:
publicar fontes/fragmentos/registro no repo e registrar hash do resultado local.

## Aceite

Validar sintaxePython/JS e HTML, IDs/links/sidebar, idempotência, preservar
capítulos anteriores e ausência de recursos externos/segredos. Browser real:
abrir novas aulas por sidebar, busca, checklist manual, temas claro/escuro,
persistência/reload, preferência de sistema e storage indisponível, desktop/
mobile/print sem overflow; capturas inspecionadas. Executar comandos destrutivos
apenas em fixtures próprias se necessário; nunca no sistema do operador.
Registrar evidências/revisar prompt antes de corrigir falha. Docs sozinhas não
alteram versões nem exigem suite MQTT/Rust sem relação. Commit/push autorizados.

- [x] Prompt preparado antes das mudanças.
- [ ] Conteúdo e passos atuais no guia.
- [ ] Tema claro/escuro persistido.
- [ ] Validação e evidências honestas.
- [ ] Commit/push das fontes e registro do HTML local.
