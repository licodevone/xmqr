# P279 v1.0 — fechar a distribuição Broker 0.45.0

## Entrada e objetivo

Base `fbea7e0`, candidato P275/P276, com P277 e P278 no diretório de
trabalho. Consolidar as entregas em um commit de validação da 0.45.0.
Preservar registros históricos, alterações do operador e o estado v16.

## Escopo e aceite

- Incluir taxa por identidade, caso QoS 1 offline e evidências existentes.
- Atualizar as notas e a matriz de versão. Testar recuperação também
  com o binário do `.deb` em CI, após a instalação descartável.
- Repetir formatação, testes e Clippy. Na branch de validação, exigir
  TCP/WS, admissão de 1.000 conexões, recuperação, instalação, retorno
  à versão anterior e pacote com checksums.
- Enviar a branch `release/validation-0.45.0`. Criar a tag anotada
  `v0.45.0` e publicar somente após aceite dos artefatos do commit
  exato. Registrar as evidências em `prompts/registros/P279-finalizar-0.45.0.md`.
