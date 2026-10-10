# P46 — imagem Docker do broker e das ferramentas

Prompt 1.0, 2026-10-10. Estado: preparado antes dos arquivos Docker. Pedido
autorizado: criar e validar uma imagem Docker local para o broker. Base própria
do broker: candidato 0.9.0 após P45.

## Estado de entrada

Repositório independente `xmqr`, Rust/MIT, binários `mqtt-broker` e `mqtt-admin`.
P45 implementa backup/restore offline. O broker usa `MQTT_STATE_DIR`; modo seguro
`secure-mtls` é padrão, monitor HTTP opcional é loopback, `open-lab` rejeita bind
que não seja loopback. Docker Desktop local está instalado e com engine Linux.

## Escopo

Adicionar Dockerfile multi-stage e `.dockerignore` ao repositório, com binários
`mqtt-broker` e `mqtt-admin` no runtime Debian slim compatível com o builder,
usuário sem privilégios, volume documentado para o estado e portas MQTT seguras.
Não embutir certificado, chave, bundle de segurança, usuário ou senha na imagem.
Documentar build, run, persistência, montagem somente leitura dos segredos,
variáveis reais aceitas pelo broker e comandos P45 via `docker exec`.

O container preserva o modo seguro por padrão. Exemplos devem explicar que o
`open-lab` continua limitado a loopback dentro do container e não serve para
publicação de porta Docker; exemplos de aula em rede precisam advertir sobre
ausência de TLS. Healthcheck externo só deve ser incluído se verificar de fato
readiness sem expor monitoramento além de loopback e sem exigir ferramenta não
disponível no runtime.

## Aceite

- `docker build` conclui usando `Cargo.lock` e o source atual; runtime não contém
  compilador/Cargo ou source.
- Container inicia com usuário não-root, grava estado em volume e persiste restart.
- `mqtt-admin` está disponível para inspeção e backup dentro da imagem.
- Testar `docker run --rm IMAGE mqtt-admin --help` ou equivalente, config inválida
  falha fechada e `open-lab` não escuta na interface externa.
- Documentar comandos reais, limites de bind/volume, versionamento e remoção.
- Não rodar como root, não executar `docker push`, não instalar Mosquitto e não
  alterar versão/tag Git.

Registrar plataforma Docker local, imagem/tamanho e resultados. A tag `v0.9.0`
continua a cargo do usuário.
