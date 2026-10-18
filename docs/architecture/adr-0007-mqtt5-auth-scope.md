# ADR 0007 — recorte de autenticação estendida MQTT 5

Data: 2026-10-18. Decisão de escopo M10/P227; não é aceite global da fase6
nem declaração de produção. Código existente P158–P160, clientC91/C92.

## Decisão

Suportar o método `PLAIN` inicial exclusivamente sobre TLS, nos perfis
TLS-senha e mTLS existentes. Em mTLS permanecem os vínculos de identidade,
certificado e ACL. Não aceitar sua combinação ambígua com os campos
Username/Password do CONNECT; CA, SAN e validade continuam obrigatórios
nos clientes. PLAIN transporta credenciais, não as cifra: nunca usá-lo em
conexão sem TLS nem colocar Authentication Data em logs/artefatos públicos.

Suportar reautenticação explícita iniciada pelo cliente com AUTH0x19 e
sucesso0x00, para a mesma identidade e método negociados, sem mudar a
identidade da sessão. A geração de segurança deve continuar válida; falha
não concede principal nem permissão nova. O caminho usa a autenticação
existente, não um armazenamento paralelo de credenciais.

Não implementar neste recorte mecanismos adicionais de desafio/resposta,
troca de identidade em sessão, reautenticação periódica do servidor ou
provisionamento/rotação de segredos pelo AUTH. Ausência dessas extensões
é explícita, não teste aprovado. Rotação TLS e reload administrativo têm
seus próprios contratos e não constituem mecanismos SASL novos.

## Justificativa e consequências

O gate da fase6D pede decisão dos mecanismos suportados, não todos os
mecanismos possíveis. O recorte preserva a fronteira de autenticação/ACL,
quotas e TLS já existentes, sem anunciar autenticação estendida genérica.
Método desconhecido é recusado com CONNACK0x8c; credenciais inválidas com
0x86. Validações de propriedades, fases e limites continuam obrigatórias,
inclusive negativos. A referência é a [norma OASIS MQTT5](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html),
seções3.1.2.11.9–10,3.15 e4.12.

## Evidência e limites

`verify_mqtt5_plain_auth.py`, `verify_mqtt5_reauth.py` e
`verify_mqtt5_auth_refusal.py` exercitam wire/client próprios. Precisam
passar novamente no conjunto final; sua existência não é execução.

P227 executou `verify_phase6_paho_auth.py` com Paho2.1.0 independente no
candidato identificado no [registro](../../prompts/registros/P227-fechamento-integrado-fase6.md):
PLAIN inicial TLS/mTLS, pub/subQoS1, senha inválida e método desconhecido
passaram, com verificaçãoCA/SAN. Isso **não** comprova reautenticação AUTH
com Paho nem qualquer mecanismo de desafio. Não estender esse resultado
à certificação MQTT5 integral ou aos fluxos excluídos acima.
