# XMQR Manager Ubuntu 0.1.0 — experimental

Primeiro Manager de desktop para Ubuntu: janela GTK, bandeja Ayatana opcional,
atalho e início no login. Controles individuais e gerais de iniciar, parar e
reiniciar serviços XMQR. Início Broker/Admin/Clients e parada inversa; falha
interrompe as próximas etapas e informa possível execução parcial.

Descobre binários e units XMQR, incluindo instâncias pub/sub/bridge do Client,
e confere o executável antes do controle. Um Admin sem unit permanece CLI;
configuração/URL personalizadas são cadastradas no inventário root protegido.
Não cria serviços, credenciais nem endpoints por conta própria.

systemd/polkit trata a autenticação administrativa. Configurações e pastas
protegidas usam GIO/GVfs admin:///. O journal mostra as últimas 300 entradas,
sem pager, na janela local. Não instala política que dispense autenticação.

Instalação em Ubuntu com desktop GNOME:

```sh
sudo apt install ./xmqr-manager_0.1.0-1_all.deb
xmqr-manager
```

O pacote declara suas dependências; AppIndicator é recomendado. A janela
continua disponível sem bandeja. O Manager deve executar como usuário do desktop.

Validação em Ubuntu26.04 isolado: 29 testes, smoke GTK/D-Bus/Xvfb com reinício
geral simulado, validação de atalhos, modos/ownership e launcher do .deb.
CI da fonte exata e proveniência constam no
[P256](../../prompts/registros/P256-manager-releases.md).

Limites: polkit e GVfs admin reais, serviços reais, login/Wayland e ciclo de
instalação/upgrade/rollback no desktop ainda não homologados. Running não
comprova prontidão MQTT. Pré-release experimental, sem homologação de produção.
Código próprio MIT; bibliotecas do sistema mantêm suas licenças.
[Guia completo](../../tools/linux-manager/README.md).
