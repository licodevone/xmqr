# P253 — Recuperação da atualização Admin

2026-10-22. Entrada: screenshot image(20261022-055409).png. Manager P252
atualizado com backup; configurador Admin reporta diferença de ACL após
File.Replace e falha de recuperação. Console/ e backups preservados.

## Diagnóstico comprovado

O script P252 realiza a troca de binário/configuração antes de exigir igualdade
de owner, grupo, proteção e bytes das ACEs com a configuração anterior. O catch
repete a exigência, bloqueando também uma diferença produzida pela própria
troca. Trata-se de uma falha no fluxo do atualizador, não de evidência de erro
do operador ou do antivírus. A fixture P252 não cobriu origem protegida com
destino herdado de política distinta.

A diferença precisa no arquivo instalado continua desconhecida: token das
ferramentas não elevado e Get-Acl de ProgramData/admin/admin.toml recusado.
Get-Service nesta ferramenta não encontrou os serviços e não permite inferir
desinstalação nem estado SCM real. Nenhum comando Start/Stop foi executado.
Inspeção de binário público confirma Admin A28 já substituído; P252 não deve
ser repetido após falha, pois preserva console/ existente e recusa reaplicação.

Revisão independente por dois agentes somente leitura. Fontes primárias
consultadas: Microsoft ReplaceFileW (mescla/preservação de DACL) e
SECURITY_DESCRIPTOR_CONTROL (SE_DACL_PROTECTED e flags de herança são controles
distintos). Isto fundamenta a hipótese de representação diferente; não prova
qual campo mudou na máquina.

- https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-replacefilew
- https://learn.microsoft.com/en-us/windows/win32/secauthz/security-descriptor-control

## Abordagem

Novo recuperador, separado do P252: diagnóstico por padrão; -Resume somente
após todos os preflights, sem setters de ACL e sem substituir arquivos. Valida
footprint, conteúdo não secreto e direitos exatos reconhecidos; caso divergente
recusa e preserva relatório de metadados. Não abre token, senha, chaves,
certificados, usuários ou estado. Inicia apenas Admin se parado e validado.
Conclusão instalada depende de aplicação elevada pelo operador.
