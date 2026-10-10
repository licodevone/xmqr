# Registro P46 — imagem Docker do broker

Data: 2026-10-10. Imagem local `xmqr-broker:0.9.0`; sem push de imagem,
tag Git ou release. Docker Desktop 4.93.0, Docker Engine 29.8.1,
Linux/amd64 (`desktop-linux`).

## Resultado

Dockerfile multi-stage com builder Rust 1.99.0 e runtime Debian slim. A imagem
contém `mqtt-broker`, `mqtt-admin`, licença MIT e inventário de dependências.
Roda com UID/GID 10001, usa `/var/lib/xmqr` como volume e mantém `secure-mtls`
como padrão. Certificados, chaves e bundle são arquivos externos; não há
healthcheck superficial nem exposição de monitor HTTP.

## Validação executada

- `docker build -t xmqr-broker:0.9.0 .`: PASS.
- Imagem final local: 138,269,871 bytes; usuário configurado `10001:10001`.
- Execução no modo seguro padrão sem certificados: falhou antes de abrir listener,
  exigindo `MQTT_SERVER_CERT`, como esperado.
- `open-lab` com bind `0.0.0.0:1883`: recusado com exit 1 como esperado.
- Integração em containers isolados com a imagem cliente: subscriber e publisher
  comunicaram via namespace de loopback do container; PASS.
- Retained publicado, broker removido e recriado com o mesmo volume; mensagem
  recuperada: PASS.
- `mqtt-admin state backup`, `verify` e `restore` executados em container helper
  depois de parar o broker; PASS.

## Limites

O teste de rede usou `open-lab` dentro do namespace compartilhado, somente para
loopback. Não valida implantação mTLS, gerenciamento de certificados em produção,
hardening do daemon/host, multi-arquitetura, imagem assinada ou publicação em
registry. `v0.9.0` é apenas a etiqueta local da imagem e não uma tag Git.
O runtime contém a licença MIT do projeto e o inventário; textos completos de
licenças de terceiros devem ser incluídos antes de redistribuir a imagem.
