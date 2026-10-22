# Atualizar Manager e habilitar o console — P252

Esta atualização dispensa desinstalação. O X ocupa mais da área útil do ícone,
sem palavras nem bolinha. Fica verde quando todos os serviços instalados estão
em execução; nos demais estados fica cinza apagado. O Windows determina o
tamanho físico da área da bandeja. A cor indica estado dos serviços, não uma
prova de conexão MQTT; consulte os estados individuais no menu.

O console web usa processos próprios do Client para PUB/SUB, separados do
Client que já funciona como serviço. O Admin passa a receber os caminhos dos
perfis pelo seu arquivo de configuração. Não precisa criar variável de ambiente.

1. No ícone atual do Manager, selecione **Sair da bandeja (mantém os serviços)**.
2. Abra **PowerShell 7 de 64 bits como administrador**. Execute, uma linha de
   cada vez, e avance somente se a anterior concluir sem erro:

```powershell
& "D:\projects\my-project\acmebr-projects\acmebr-broker-client\xmqr\scripts\update_windows_manager_p252.ps1"
& "D:\projects\my-project\acmebr-projects\acmebr-broker-client\xmqr\scripts\configure_windows_admin_console_p252.ps1"
```

3. Feche a janela administrativa e abra o **XMQR Manager pelo atalho normal**.
   Também pode usar este comando num PowerShell comum:

```powershell
Start-Process 'C:\Program Files\XMQR\Manager\xmqr-manager.exe'
```

4. Abra <http://127.0.0.1:9080/>. Entre com sua conta existente; o reinício do
   Admin pode exigir novo login. Abra o console MQTT e clique em **Conectar**.
   Use o tópico `xmqr/local/test`, QoS 1. Assine esse tópico, publique uma
   mensagem de teste e confira seu recebimento.

Se estiver usando o ZIP em outra pasta, extraia todo o conteúdo e execute os
dois scripts dessa pasta, mantendo os executáveis e `manifest.json` ao lado.
Não execute scripts diretamente dentro do ZIP.

Os scripts verificam caminhos, hashes e permissões antes de aplicar. O primeiro
atualiza somente o Manager fechado. O segundo faz backup, acrescenta os perfis
privados e reinicia somente o Admin. Broker e Client serviço são preservados,
assim como conta web, token e certificados. Os backups ficam nas pastas
informadas ao concluir. Se houver erro, pare e envie o texto; não desinstale nem
reaplique o script sobre uma configuração parcialmente atualizada.

Foi validado em ambiente isolado: autenticação web, CSRF, SUB e PUB mTLS com
recebimento da mesma mensagem. A aplicação desta atualização nos serviços
instalados e a aparência final na bandeja ainda dependem da execução acima.

Executáveis P252: Manager `0.1.0`, Admin `0.11.0`; versões mantidas, identificados
pelos hashes do manifesto. O pacote contém somente esses dois componentes.
