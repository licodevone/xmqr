# P112 rev1 — diagnóstico de recuperação sem mutação

2026-10-15. Entrada broker `fc4ebb1` mais P111 local, admin `a007307` mais A09 local. A08 da matriz da fase 5 exige validação, espaço, backup, versões e saída redigida.

Adicionar versão do broker à resposta `status` do canal local v1, sem alterar estado nem expor configuração. Preservar UID/token, limites e autorização viewer. Provar que a resposta não contém credenciais e que o binário responde com sua própria versão. Documentar compatibilidade com clients do protocolo v1 que ignoram campo extra.

Validar fmt/test/Clippy e integração com o CLI independente. Registrar execução antes de marcar A08 ou a fase 5.
