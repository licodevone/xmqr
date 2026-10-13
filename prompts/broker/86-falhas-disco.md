# P86 v1 — fase 3/B06: falhas de armazenamento sem confirmação fictícia

## Estado de entrada e autorização

2026-10-13; broker/admin0.11.4, main8e3f57cbee416279475a6cf9d32576e52c1d38e6;
client0.8.1 em repositório separado. Fase2 aceita porP85/C44. Broker limpo;
preservar os dois arquivos0.7.1 não rastreados do client. O mantenedor autorizou
continuar, registrar prompts antes do código, validar, commit/push e distribuir
marcos de runtime aceitos. Esta entrega é a primeira fatia B06 da fase3, não
o encerramento da fase nem autorização para alterar serviços/dados reais.

Hipótese a verificar: replay_wal trata qualquer erro ao completar os quatro
bytes do tamanho como cauda truncada. Extrair a leitura em helper genérico
preservando a semântica inicial, reproduzir EIO após leitura curta com Reader
controlado e, se falhar, corrigir distinguindo UnexpectedEof de erro real de
leitura. Registrar RED/GREEN antes de anunciar correção; patch0.11.5 se aprovado.

## Objetivo, escopo e arquivos

Demonstrar, pelo caminho real Store -> writer -> MqttStore -> router -> handler,
que falhas de I/O não produzem confirmação de ownership nem fan-out fictícios.
Criar injetor determinístico por instância, compilado exclusivamente com
`cfg(test)`, sem variável de ambiente, feature pública, dependência ou segredo.
Arquivos: src/persistence/{mod,actor,faults,fault_tests}.rs;
src/mqtt/{store,router,mod,storage_fault_tests}.rs; src/transport/mod.rs (ponte
somente cfg(test) para inicialização loopback real);
testes novos nesses módulos; docs/architecture/persistence.md;
docs/{evolution-plan,plano-paridade-mosquitto,conformance/mqtt311-status}.md;
README e registro P86. Corrigir defeito funcional apenas se reproduzido e
registrado no escopo de persistência, sem mudanças especulativas.

## Invariantes e transições

- Estado/seq em memória só avançam após `sync_data` bem-sucedido. Erro após
  início da escrita envenena Store; writer recusa put/delete/get/probe/snapshot.
- Router torna-se fatal, fecha todas as sessões e não entrega candidato não
  confirmado. Handler não envia PUBACK/PUBREC/PUBCOMP após erro do commit.
- Reopen é obrigatório: cauda realmente incompleta pode ser descartada; registro
  completo sem ACK pode reaparecer. Erro de fsync tem resultado incerto, NÃO
  equivale a garantir que nada foi gravado. Corrupção completa falha fechada.
- Snapshot: temporário -> sync -> rename -> sync do diretório -> compactação;
  falhas em cada fronteira não podem perder o último estado confirmado.
- Preservar formato WAL/snapshot1 e documentoMQTT2, compatibilidade de leitura,
  gerações/takeover, ACL/restore, mTLS padrão, MIT e todas as quotas existentes.

Fonte consultada: [OASIS MQTT3.1.1 §§4.3.2/4.3.3/4.4](https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html).
MQTT-4.3.2-2 e MQTT-4.3.3-2 governam ownership/ACKs; a barreira fsync é contrato
local de durabilidade, não imposição de filesystem pela especificação MQTT.

## Validação e aceite

1. ENOSPC Linux (erro28) e EIO (erro5) injetados; escrita curta com progresso
   deve completar, Interrupted deve repetir, zero deve retornar WriteZero;
   prefixo incompleto + erro deve ser truncado na reabertura. Sem preencher disco.
2. Falhas no append/sync e snapshot create/write/sync/rename/directory-sync/
   truncate/header-write/compact-sync; lock, poison e reopen observados.
3. Corrupção CRC/versão/seq/tamanho em cópias temporárias; não ignorar registro
   completo inválido nem alocar acima dos limites.
4. Writer, router e frames independentes no TCP loopback: ausência de ACK nos
   QoS1, QoS2/PUBLISH e QoS2/PUBREL; fechamento e recuperação/retentiva observados.
   Deadline nos testes, sem daemon permanente ou credenciais reais.
5. Ubuntu26/WSL: fmt/test/clippy -Dwarnings/build bins/inventário; regressão do
   client0.8.1. Registrar números, códigos, cenários, limites e diff reais.
6. Atualizar checklist apenas no recorte aceito; fuzzing/prolongados/B08/C07
   ficam pendentes. Commit e push autorizados, revisar arquivos antes de incluir.

## Distribuição e limites

Se somente instrumentação `cfg(test)`, testes e documentação mudarem, manter
runtime0.11.4/client0.8.1 e as tags/.deb/imagens publicadas imutáveis; não gerar
binário supostamente novo sem alteração funcional. Publicar evidência sanitizada
com provenance nas releases existentes quando aceita. Se houver correção real,
preparar prompt de release patch novo e gates do commit exato antes de publicar
tag/.deb/Hub. Nenhuma alegação de disco físico cheio, perda de energia, todos
os filesystems, conformidade integral ou produção.
