# P226 — distribuição experimental da bridge T02

Entrada: P223–P225/C125–C127, sidecar em `xmqr-client/main` sem pacote/tag. Este prompt precede alteração de empacotamento.

Objetivo: distribuir `mqtt-bridge` no pacote Ubuntu 26.04 amd64 do client e na imagem do client, com versão exibida e unidade systemd de instância **desabilitada** por padrão. Configuração/credenciais privadas devem ser criadas pelo operador, sem senha na CLI, logs ou imagem. Parâmetros de serviço precisam manter a identidade estável da origem; versão anterior do `.deb` deve continuar instalável em rollback sem destruir credenciais.

Aceite: build reproduzível, `dpkg-deb` inclui binário e unit, `systemd-analyze verify`, instalação e remoção em ambiente descartável, bridge real a partir do pacote ou imagem com configuração montada, upgrade/rollback para client 0.36.0, imagem por digest remoto e hashes dos anexos. CI da fonte/tag exata; criar v0.37.0 apenas depois dos gates, sem declarar fase 8 concluída. Broker/admin continuam 0.42.0/0.10.0 sem release nova.
