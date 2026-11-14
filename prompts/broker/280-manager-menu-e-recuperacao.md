# P280 v1.0 — menu compacto e recuperação no Manager Windows

Base Manager 0.1.1 na árvore do Broker `fbea7e0`. Separar este trabalho
da release 0.45.0. A imagem enviada mostra o menu nativo de bandeja.

- Encurtar títulos, ações e estados. Mover explicações longas para o
  tooltip e manter o detalhe de erros no aviso de diagnóstico. Acrescentar
  ícones locais em controles, atalhos e serviços, com rótulos legíveis.
- Adicionar `Recuperar serviços` e `--control-all recover`. O plano inicia
  apenas serviços em estado Falha, em ordem de dependência. Reusar o
  inventário, a verificação de executável e a elevação já existentes.
  Serviços saudáveis ou parados pelo usuário ficam fora da operação.
- Sem exclusão de dados, mudança de ACL ou ação administrativa no painel.
  Verificar negativos de CLI, plano, build, Clippy e uso real quando o SCM
  permitir. Registrar tentativa de reparo do Windows separadamente.
