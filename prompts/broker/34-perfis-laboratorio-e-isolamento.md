# P34 — Auditar os quatro perfis e o isolamento de estado

Tipo: manutenção de funcionalidade existente. Não executar nesta importação.
Pré-requisito: pedido específico e contrato-base. Leia src/main.rs, src/auth/mod.rs,
src/transport/mod.rs e docs/laboratorio-mqtt-aberto.md.

## Prompt de trabalho

Prepare o estado de entrada e preserve secure-mtls como padrão. Audite open-lab
anônimo, password-lab com senha, acl-lab com senha/ACL e secure-mtls com
certificado+senha+ACL. Verifique bind loopback de todos os perfis sem TLS,
variáveis incompatíveis e falha fechada de usuários/ACL ausentes ou malformados.
Confira ensure_state_profile: diretório marcado, perfil incompatível e diretório
com estado legado não devem virar modo aberto silenciosamente. Preserve principal
e vínculo de sessão por perfil. Não abra portas/firewall nem reutilize estado real.
Não implemente seleção dinâmica de perfil, reload ou listener adicional sem pedido.

## Aceite e evidência futura

Tabela por perfil: transporte, credencial, ACL, bind, variáveis e estado. Testes
negativos de bind LAN, variáveis indevidas, mudança de perfil, estado preexistente
e autenticação inválida; positivos em diretórios isolados. Execução só se autorizada;
registros sem credenciais. Não chamar os perfis de laboratório de produção.
