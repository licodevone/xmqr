# Prompt — identidade mTLS e ACL de tópicos

Defina a política de autenticação/autorização **antes de expor pub/sub**. O transporte já exige certificado de cliente assinado pela CA local. Isso autentica o certificado, mas ainda não define quais tópicos cada dispositivo pode publicar ou assinar. Consulte a [documentação do Mosquitto](https://www.mosquitto.org/man/mosquitto-conf-5.html) para comparação, sem presumir que este broker lê `mosquitto_passwd` ou o formato `acl_file`.

## Decisão a registrar

- Opção A, recomendada para o primeiro MVP: mTLS obrigatório; cada certificado autorizado mapeia para uma identidade própria; ACL local nega tudo por padrão e concede ações `publish`/`subscribe` em tópicos exatos.
- Opção B, se explicitamente escolhida: mTLS **e** usuário/senha no CONNECT, mais ACL. Defina vínculo entre usuário e certificado; nunca aceite que um nome de usuário fornecido pelo cliente substitua a identidade verificada pelo TLS. Armazene apenas hashes de senha adequados, nunca senha em texto puro, e não reutilize o arquivo do Mosquitto sem implementar e testar compatibilidade de formato.
- Decisão deste projeto: **B, confirmada pelo usuário** — mTLS obrigatório **e** usuário/senha no CONNECT **e** ACL. A opção A permanece registrada apenas como alternativa rejeitada para este MVP.

## Requisitos

1. Projete configuração legível para: identidade do certificado, permissão de conexão, tópicos exatos permitidos para publicar e assinar; inclua exemplo de laboratório `teste/mensagem`. Documente como adicionar e revogar um dispositivo. Certificados distintos devem ter identidades distintas; o certificado de laboratório compartilhado entre `pub`/`sub` vale apenas para testes.
2. Faça load e validação completos da configuração antes de abrir o listener; erros ou arquivo ausente devem impedir o servidor de iniciar, sem fallback para autorização aberta. Use cópia imutável da política por conexão ou mecanismo de reload atômico testado.
3. Aplique ACL em CONNECT, SUBSCRIBE e PUBLISH **antes** de alterar estado ou encaminhar mensagens. Defina respostas MQTT 3.1.1 para recusa e desconexão conforme a [especificação OASIS](https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/mqtt-v3.1.1.html). Nunca normalize nome de tópico ou filtro para autorizar; não trate `+` ou `#` como tópico de publicação.
4. Limite entradas de configuração, quantidade de regras e tamanho de tópicos. Não registre certificado completo, senha nem payload em logs; registre apenas identificador seguro e motivo genérico. Inclua testes de identidade desconhecida, permissão negada, regras malformadas, duplicação, certificado revogado e troca de configuração.
5. Crie ferramenta própria para cadastrar e trocar senhas sem expô-las em argumentos de linha de comando ou histórico do shell. Teste hash, comparação, tentativas repetidas e senhas incorretas. A mTLS continua obrigatória.

Tópicos MQTT não são cadastrados previamente: o nome aparece no PUBLISH e o filtro no SUBSCRIBE. O arquivo ACL define **permissões sobre nomes/filtros**, não cria filas ou tópicos persistentes.
