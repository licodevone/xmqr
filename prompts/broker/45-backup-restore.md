# P45 — backup e restauração verificáveis, candidato 0.9.0

Prompt 1.0, 2026-10-10. Estado: preparado antes do código. Pedido autorizado:
implementar a próxima fatia do roadmap do broker. Próxima versão própria: 0.9.0.

## Estado de entrada

Broker `mqtt-broker` 0.8.0, tag local/remota `v0.8.0`, HEAD `b3f34b9`; branch
`main` alinhada com `origin/main`, sem alterações prévias do usuário. Client é
projeto separado e não integra o escopo. O bootstrap Serena criou `.serena/`
local durante a inspeção; é estado de ferramenta e não pertence à feature.

O estado durável usa `state.wal`, `state.snapshot`, temporário de snapshot e
lock exclusivo `state.lock`. `Store::open` recupera sob lock; WAL/snapshot têm
versões e CRC e o projeto já depende de `sha2`. P44 adicionou bundle de segurança
externo ao diretório de estado. Broker deve estar parado para backup/restauração.

## Objetivo e escopo

Adicionar ao `mqtt-admin` operações offline `state backup`, `state verify` e
`state restore`. Backup é um diretório versionado de formato próprio, sem
compactação ou dependência nova. Inclui somente os arquivos duráveis MQTT
necessários (`state.wal` e `state.snapshot`), um manifesto com
versão do pacote, versões dos formatos WAL/snapshot, sequência e SHA-256 de cada
arquivo. Não
copiar `state.lock`, temporário, bundle, certificado, chave, configuração ou
variáveis de ambiente. Documentar esses itens excluídos e a necessidade de
preservar separadamente os arquivos externos com suas permissões.

Interface proposta:

```text
mqtt-admin state backup --state-dir DIR --destination NOVO_DIR
mqtt-admin state verify --backup DIR
mqtt-admin state restore --backup DIR --state-dir NOVO_DIR
```

Backup abre/recupera o estado com o lock exclusivo existente e faz snapshot/
compactação antes da cópia, mantendo os mesmos dados lógicos e limitando o WAL;
documentar essa mudança física. Processo ativo deve fazer a operação falhar sem
copiar. Escreve em diretório temporário irmão,
com nomes de arquivos fixos, valida os bytes e publica por rename atômico somente
se o destino ainda não existir. Restore verifica o manifesto, copia para staging
irmão do novo destino, abre o estado copiado para validar recuperação/formato e
faz rename atômico quando tudo passa. Destinos existentes nunca são removidos,
substituídos ou parcialmente alterados. `verify` valida hashes e recuperação em
cópia temporária descartável, sem modificar a fonte do backup.

Manifesto e leitor devem rejeitar versões desconhecidas, campos inesperados,
duplicatas, caminhos arbitrários, links simbólicos, arquivos ausentes, grandes
demais ou com digest incorreto. Usar nomes constantes; não permitir traversal.
Garantir cleanup de staging após falha. Diretórios/arquivos produzidos devem ter
permissões privadas em Unix (0700/0600). O estado pode conter tópicos e payloads:
nunca exibir conteúdo nem registrá-lo. Documentar que SHA-256 detecta corrupção
acidental, mas não autentica backup adulterado.

Não copiar snapshots por leitura concorrente, não alterar o formato WAL/estado,
não fazer backup de credenciais TLS ou bundle dinâmico, não restaurar sobre o
diretório configurado existente e não prometer proteção contra falha de energia
ou filesystem sem garantias de `fsync`/rename. Sem MQTT, bridge, WebSocket,
quotas novas, upgrade de dependências ou alteração do client.

## Arquivos previstos

`src/bin/mqtt-admin/main.rs`, módulo novo de backup sob `src/bin/mqtt-admin/`,
acessores/validação necessários em `src/persistence/mod.rs`, testes Rust,
`docs/architecture/persistence.md`, `docs/administracao-usuarios.md` ou guia
administrativo novo, README/CHANGELOG, matriz e registro P45.

## Aceite e validação

- Backup válido de estado vazio e populado, com e sem snapshot; validar sequência,
  conteúdo, modo/permissões Unix e que o processo broker ativo bloqueia backup.
- `verify` rejeita manifesto desconhecido/malformado, arquivo ausente, alteração
  de bytes, link simbólico e WAL/snapshot corrompido, sem tocar a fonte.
- Restore em diretório novo recupera sessões, retained, offline/QoS2 conforme
  estado capturado; diretório existente permanece idêntico quando recusado.
- Interrupções/falhas durante staging não deixam destino publicado nem staging
  órfão; caminhos com espaços e Unicode funcionam; nenhum secret/payload nos erros.
- Executar `cargo fmt --all -- --check`, `cargo test --locked`, `cargo clippy
  --locked --all-targets -- -D warnings`, inventário MIT e `cargo build --locked
  --bins` em Windows e Ubuntu-26.04/WSL sobre `/mnt/d/projects/my-project`.
  Executar integrações offline próprias em diretórios temporários; ferramentas
  ausentes ficam BLOCKED, sem instalar Mosquitto.

Registrar comandos e resultados reais, PASS/FAIL/BLOCKED, cenário/plataforma,
compatibilidade, limitações e diff. Candidato 0.9.0 deve ser alinhado em manifest
e lock se a feature validar; não criar commit, push, tag ou release.
