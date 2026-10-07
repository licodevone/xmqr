---
name: xmqr-security-review
description: "Revisar segurança de mudanças ou componentes do XMQR quando pedido ou quando necessário para uma alteração de parser, TLS, autenticação, ACL ou persistência."
---

# Revisão de segurança do XMQR

Leia [AGENTS](../../../AGENTS.md), [política](../../../SECURITY.md),
[auth/ACL](../../../docs/security/auth-acl.md) e
[transporte seguro](../../../docs/security/secure-transport.md).
Revisão é leitura; correções exigem prompt preparado e escopo de mudança autorizado.

Inspecione fronteiras: main/perfis, codec, auth, fan-out/restore e admin/users.
Verifique limite antes de alocação, deadline, admissão, Argon2 em fronteira limitada,
vínculo fingerprint/usuário e principal da sessão, ACL literal no filtro e
match concreto nas entregas. Preserve regra $, deny-by-default e gerações.
Não sugerir permissão implícita por normalização ou wildcard mais abrangente.

Confirme TLS/SAN/CA/CRL aplicáveis; proibir fallback aberto por falha de configuração.
Perfis sem TLS são loopback, com variáveis incompatíveis recusadas e diretório
de estado separado. CRUD deve preservar lock, symlink checks, arquivo privado,
temporário validado e rename/sync em Unix. Não presumir revogação dinâmica.

Audite logs e saídas sem exibir secrets; não ler credenciais reais desnecessárias.
WAL/snapshot não devem guardar credenciais e corrupção/commit incerto não pode
gerar ACK de ownership. Testes negativos em recursos isolados só sob execução
autorizada, sem scanner externo, instalação ou serviço real nesta revisão.

Relate achados por severidade, caminho/símbolo, entrada concreta, efeito e evidência.
Separe vulnerabilidade demonstrada, hipótese a validar e hardening opcional.
Se nada relevante for encontrado, diga isso e registre a cobertura/limitação;
não declarar segurança integral por uma revisão parcial.
