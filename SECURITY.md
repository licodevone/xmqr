# Política de segurança

## Versões suportadas

Enquanto o XMQR permanecer em `0.x`, somente a versão experimental mais recente
e a série anterior receberão correções de segurança quando viável. A tabela será
atualizada a cada release.

| Série | Suporte |
| --- | --- |
| `0.4.x` | sim |
| `0.3.x` | correções críticas, quando possível |
| `< 0.3` | não |

## Relatar uma vulnerabilidade

Não abra issue, discussão ou pull request pública para uma vulnerabilidade não
corrigida. Use o formulário privado
[Report a vulnerability](https://github.com/licodevone/xmqr/security/advisories/new).
Se o formulário não estiver disponível, não publique detalhes técnicos: avise o
mantenedor pelo perfil do GitHub e aguarde a abertura de um canal privado.

Inclua, quando possível:

- versão ou commit afetado;
- impacto e cenário de ameaça;
- passos mínimos para reprodução;
- configuração usada, removendo segredos e payloads sensíveis;
- mitigação temporária conhecida.

O mantenedor procurará confirmar o recebimento em até sete dias. Prazos de
correção e divulgação serão combinados conforme gravidade, alcance e
complexidade. Não há programa de recompensa financeira neste momento.

## Escopo prioritário

- bypass de autenticação, certificado ou ACL;
- corrupção, perda ou exposição de estado persistente;
- violações de QoS que causem confirmação prematura;
- consumo não limitado de CPU, memória, disco ou conexões;
- travamento remoto, panic não isolado ou traversal de caminhos;
- vazamento de credenciais, chaves, hashes ou payloads.

Os modos `open-lab`, `password-lab` e `acl-lab` são deliberadamente inseguros e
restritos a loopback. Expor esses modos fora do computador local não é uma
vulnerabilidade do modo `secure-mtls`.
