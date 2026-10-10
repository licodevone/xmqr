# P47 rev.1 — systemd, Ubuntu e release

Base: main 688fa4f, tag v0.9.0, árvore limpa. Pedido autoriza implementação,
commit, push e releases dos dois projetos. Ubuntu 26.04/WSL é o alvo solicitado.

Objetivo: SIGTERM/SIGINT coordenam parada do broker, fechamento do listener,
publicação durável dos Wills de conexões encerradas e shutdown do writer.
Criar unit systemd, pacote deb amd64 e instruções de instalação/upgrade/remoção.
Não iniciar serviço de produção, alterar estado real ou sobrescrever tags.

Arquivos: src/main.rs, src/mqtt/router.rs, packaging, scripts, docs,
README/CHANGELOG/VERSIONING, testes e registro P47. Versão nova 0.10.0,
pois o marco 0.9.0 já foi tagueado; release experimental própria.

Invariantes: MQTT3.1.1, quotas, ACL, commit antes de ACK, MIT, formato de estado.
OASIS 3.1.2.5 / MQTT-3.1.2-8 e -10: parada do servidor não é DISCONNECT do cliente.
Clientes persistentes conservam inbound QoS2 e mensagens pendentes.
Configuração/estado preservados em upgrade/remove. Pacote não inicia/ativa
serviço automaticamente; credenciais reais são externas. Sem repositório APT
assinado público até existir destino e chave; instalar deb local via apt.

Aceite: fmt/test/clippy/build Linux, negativos e integração de sinais/Will/restart;
deb construído no Ubuntu26 amd64, verificação de unit, instalação/upgrade/remove
isolados; documentação atual alinhada sem reescrever registros históricos.
Publicar prerelease e anexar deb/checksum após gates. Registrar limitações reais.
