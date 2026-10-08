# P43 - 0.7.0 monitoramento opcional

Versao1.0,2026-10-07. Base HEADbc4cc55, tag v0.6.0 local/remota confirmada;
working tree limpo. P42 antecedeu sua implementacao. Este prompt precede P43.

Criar monitoramento HTTP opcional por MQTT_MONITOR_ENABLED=true, bind configuravel
MQTT_MONITOR_BIND (default127.0.0.1:9090), somente loopback. Disabled por padrao.
Endpoints GET /health(liveness), /ready(ator vivo, listener pronto e writer
operacional; nao detector de energia/espaco livre), /metrics(texto Prometheus).
Readiness exige probe real com timeout e mailbox bounded. Falha nao bloqueia
MQTT; HTTP16 conexoes, header4096, read/write1s, probe500ms, sem keepalive/body.

Metricas globais e labels finitos: conexoes handler/aceitas; PUBLISH aceito QoS;
frames PUBLISH enviados QoS; filas agregadas(offline,inflight,delivery,comandos);
rejeicoes(auth,ACL,quota,admission,delivery,storage); commits/erros/duracao e
snapshots; Will. Nunca payload/topico/ClientId/username/credencial como label.
Instrumentar depois de commit/escrita conforme semantica documentada; failed
commit nao incrementa sucesso. HTTP e sinais de encerramento nao alteram MQTT.
Server teardown cancela listener/requests e readiness. Falha HTTP apos startup
nao encerra broker; bind configurado invalido falha inicial explicitamente.

Arquivos: novo monitoring.rs,main/lib,mqtt handler/router/store,persistence actor,
transport se necessario,tests/scripts,docs,manifests0.7.0 e registros.
Sem novas dependencias se Tokio existente bastar; MIT inalterada. Nao0.8/reload.
Aceite: endpoints/status/negativos, cardinalidade, readiness0/1 e writerfatal,
metricas sob fluxo real QoS/retained/Will1024, isolamento MQTT com HTTPlento;
fmt,test,Clippy,inventario,build e integracoes proprias. Mosquitto/TLSexterno
NOT_RUN. Mesmo D:/repo via WSL/mnt/d; nao/homeclone. Sem commit/push/tag/release.
Avisar prontidao0.7 e parar para publicacao do mantenedor.

## Revisão 1.1 - retomada somente broker, 2026-10-08

HEAD bc4cc55 e alterações locais P43/C25 preservados. Cliente independente
sob responsabilidade separada: não editar xmqr-client ou sua versão/tag.
Fechamento P43 mantém gates Unix e integração no /mnt/d; sem instalação,
reinício ou novos recursos. Verificação portátil adicional executa recusas de
configuração inválida no processo real, antes de tocar estado. Windows não
substitui aceite de serving/durabilidade Unix. Parar no marco 0.7 validado.
