# P241 - Broker nativo Windows: persistencia e ciclo SCM

Versao 1.2 - 2026-10-21. Execucao autorizada pelo usuario: comecar pelo broker.

Revisao 1.2: metadados de timestamps antigos de alguns arquivos de licenca
nao cabem no formato ZIP. Ao gerar o arquivo de entrega, limitar apenas os
timestamps do container ao intervalo ZIP; preservar os bytes e hashes dos
arquivos originais. Fallback de licencas deve permanecer restrito aos tres
crates/versoes revisados, com proveniencia e hashes dos textos.

Revisao 1.1: primeira compilacao dos testes novos encontrou import faltante;
corrigido. Testes em Temp herdado encontraram PermissionDenied, e o cache
profundo encontrou limite de include C do AWS-LC. Usar TMP/TEMP em target
proprio e CARGO_HOME curto permitido, sem elevar nem alterar ACL do host.
Manter as versoes existentes do lock raiz ao adicionar atomicwrites; a
validacao Cargo --locked comprova o grafo. O empacotamento deve incluir textos
reais de licenca, incluindo dependencias cujo crate omitiu o arquivo.

Estado de entrada: adaptador P239 e bandeja compilados em evidencias anteriores;
persistencia recusava sync de diretorio Unix no Windows. Dependencia de servico
ja disponivel. Preservar AGENTS.md e arquivos P240/docs/chat modificados pelo
operador. Nao instalar no host, publicar ou alterar versoes.

Objetivo: permitir inicializacao, gravacao e recuperacao do broker no Windows
sem substituir a barreira de durabilidade por sucesso vazio. Publicar WAL novo
e snapshot no mesmo diretorio com conteudo sincronizado e MoveFileExW com
WRITE_THROUGH via API segura de atomicwrites 0.4.4. Manter o WAL ate sucesso
da publicacao do snapshot; fsync de diretorio Unix continua inalterado.

Escopo: manifests/locks broker comum e experimental, src/persistence/mod.rs,
src/main.rs, src/windows_service.rs, testes de falhas/crash existentes,
runner de interoperabilidade MQTT, runner SCM somente VM descartavel e docs.
Backup/restauracao do admin legado e credenciais client/admin permanecem fora.

Aceite: build real do adaptador; falhas de IO envenenam estado; crash em WAL e
snapshot conserva estado confirmado; bloqueio de escritor concorrente; MQTT
retained recuperado apos reinicio; parada antes de Running drena ator; MSI
broker+manager com marcador, licencas e checksums. Controle SCM/ACL/UAC so pode
ser aceito apos execucao real em Windows elevado descartavel. Nao inferir
garantia de queda de energia por encerramento de processo.

Validacao: fmt, testes dirigidos de armazenamento e binario, Clippy aplicavel,
smoke MQTT em loopback com estado temporario proprio, build e WiX. Registrar
falhas e limites concretos em prompts/registros/P241-windows-broker-runtime.md.
Sem migracao de formato de estado ou alteracao do protocolo MQTT.
