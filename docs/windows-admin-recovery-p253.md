# Recuperar a atualização do Admin — P253

Use este procedimento depois da mensagem **ACL original da configuração não
preservada** no configurador P252. O Manager já atualizado não precisa ser
atualizado novamente. Preserve todas as pastas `p252-backup-*` e `console/`.

Abra PowerShell 7 de 64 bits **como administrador** e execute:

```powershell
& "D:\projects\my-project\acmebr-projects\acmebr-broker-client\xmqr\scripts\recover_windows_admin_p253.ps1" -Resume
```

O recuperador primeiro registra os metadados e verifica os arquivos deixados
pela atualização. Se configuração, perfis, binários e permissões corresponderem
ao estado esperado e seguro, ele inicia somente o Admin. Não substitui
arquivos, não altera permissões e não controla Broker, Client ou Manager.

Sem `-Resume`, faz somente diagnóstico. Caso a validação recuse o estado
encontrado, envie o resultado mostrado. O relatório fica em
`xmqr\target\p253-diagnostic`; ele contém metadados e indicadores, sem tokens,
senhas ou conteúdo de chaves privadas. Não repita o configurador P252.

Após confirmação de sucesso, abra <http://127.0.0.1:9080/>, entre com sua conta
existente e conecte o console. O tópico local autorizado é `xmqr/local/test`.
Estado Running do serviço sozinho não comprova a conexão MQTT.
