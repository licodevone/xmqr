# Mitigação operacional no Mosquitto

Use `configs/mosquitto-hardened.conf` como baseline para Mosquitto 2.1.2, não como ajuste universal.

## O que a configuração reduz

- `global_max_connections`, `global_max_clients` e `max_connections` limitam tempestades de conexão e sessões órfãs.
- `max_keepalive 300` recusa keep-alive maior em MQTT 3.x e negocia o teto em MQTT 5; não use `0`, que permite ausência de verificação.
- Limites de packet/payload, inflight e filas contêm OOM e consumidores lentos.
- mTLS obrigatório e ACL deny-by-default reduzem clientes não autorizados.
- Expiração de sessões/retained evita crescimento indefinido.
- Snapshot a cada 120 segundos limita a janela de estado ainda apenas em memória.

## O que ela não corrige

- CVEs exigem atualização do binário e dependências; configuração não corrige memory corruption.
- Limites não tornam o broker multithread nem removem um gargalo do event loop.
- `mosquitto.db` ainda exige armazenamento confiável, cópia antes de upgrade, backup/restore testados e shutdown gracioso. Não execute persistência interna e plugin de persistência simultaneamente.
- `memory_limit` só existe quando o binário foi compilado com memory tracking; os demais limites devem existir mesmo assim.

## Operação complementar

- Use Mosquitto 2.1.2 ou versão de segurança posterior, nunca uma série sem correções.
- Defina `LimitNOFILE`/limites do container acima de conexões + arquivos de persistência, mas mantenha-os finitos.
- Monitore `$SYS/broker/clients`, mensagens armazenadas, bytes, desconexões, RSS, latência e duração do autosave.
- Mantenha o diretório de persistência em filesystem local com journaling; não use share de rede sem semântica de rename/fsync comprovada.
- Antes de upgrade, pare graciosamente, copie `mosquitto.db` e valide restore em uma instância isolada.

