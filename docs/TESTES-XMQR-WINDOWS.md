# Comandos de teste — XMQR no Windows

22/10/2026 · P249 v1.0 · instalação local preparada por P247, Client corrigido por P248/C152.

Abra **PowerShell 7 de 64 bits como administrador**. Copie um bloco de cada vez,
na ordem. Este documento não é um script para executar inteiro. Os testes 1–7
consultam o sistema e o teste 8 publica uma mensagem sintética. Os testes 9–11
incluem ações manuais na interface e interrupções opcionais dos serviços.
Não precisa reinstalar nem executar o inicializador ou o atualizador novamente.

## 1. Preparar a sessão

Não precisa criar variável de ambiente nem configurar PATH. Estas variáveis
são temporárias e valem somente nesta janela do PowerShell.

```powershell
$xmqrProjeto = 'D:\projects\my-project\acmebr-projects\acmebr-broker-client'
$xmqrDados = Join-Path $env:ProgramData 'XMQR'
$xmqrCliente = 'C:\Program Files\XMQR\Client\mqtt-client.exe'
$xmqrServicos = @('xmqr-broker', 'xmqr-client-default', 'xmqr-admin')
$PSVersionTable.PSVersion
[Environment]::Is64BitProcess
$xmqrIdentidade = [Security.Principal.WindowsIdentity]::GetCurrent()
try {
    ([Security.Principal.WindowsPrincipal]::new($xmqrIdentidade)).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator)
} finally { $xmqrIdentidade.Dispose() }
```

Esperado: PowerShell 7.5 ou superior e dois resultados `True`.

## 2. Conferir serviços após o reinício

```powershell
Get-Service -Name $xmqrServicos | Format-Table Name, Status, StartType -AutoSize
Get-CimInstance Win32_Service |
    Where-Object Name -in $xmqrServicos |
    Select-Object Name, State, StartMode, StartName, ExitCode, ServiceSpecificExitCode |
    Format-Table -AutoSize
(Get-CimInstance Win32_OperatingSystem).LastBootUpTime
```

Esperado: os três `Running`, início automático e conta `NT AUTHORITY\LocalService`.
Uma captura confirma aquele instante; o teste 7 verifica permanência.
Se aparecer acesso negado, confirme a elevação. “Não encontrado” em uma sessão
restrita não prova desinstalação: use o coletor do teste 12 como administrador.

## 3. Versões e capacidade de serviço

```powershell
& 'C:\Program Files\XMQR\Broker\mqtt-broker.exe' --version
& $xmqrCliente --version
& 'C:\Program Files\XMQR\Admin\xmqr-admin.exe' --version
& 'C:\Program Files\XMQR\Broker\mqtt-broker.exe' --windows-service-capabilities
& $xmqrCliente --windows-service-capabilities
& 'C:\Program Files\XMQR\Admin\xmqr-admin.exe' --windows-service-capabilities
```

Esperado nesta instalação: Broker 0.43.0, Client 0.43.0 e Admin 0.11.0;
capacidade `service_entrypoint: true` com o componente correspondente.
O Manager é a interface da bandeja, não um quarto serviço; não use nele as
opções de serviço desses três executáveis.

Verificar também o Client P248, pois a versão 0.43.0 foi preservada:

```powershell
$xmqrHash = (Get-FileHash -LiteralPath $xmqrCliente -Algorithm SHA256).Hash.ToLowerInvariant()
$xmqrHash
$xmqrHash -eq 'e9228b317a9618ee7502b7aa007d822f48ad07b109e8ac85fceceb72e014bf51'
```

Esperado: `True` para o executável entregue no P248. Uma compilação posterior
pode ter outro hash; não substitua arquivos só por essa diferença.

## 4. Portas locais

```powershell
Get-NetTCPConnection -State Listen |
    Where-Object LocalPort -in @(8883, 9090, 9080) |
    Select-Object LocalAddress, LocalPort, OwningProcess |
    Format-Table -AutoSize
```

Esperado no perfil local: ouvintes em `127.0.0.1`, portas 8883 (MQTT mTLS),
9090 (monitor do Broker) e 9080 (Admin). Porta aberta não comprova autenticação
nem entrega MQTT; o teste 8 verifica publicação e recebimento.

## 5. Saúde do Broker e resposta do Admin

```powershell
foreach ($xmqrUrl in @(
    'http://127.0.0.1:9090/health',
    'http://127.0.0.1:9090/ready',
    'http://127.0.0.1:9080/api/auth/config'
)) {
    try {
        $xmqrResposta = Invoke-WebRequest -Uri $xmqrUrl -TimeoutSec 5 -NoProxy -ErrorAction Stop
        [pscustomobject]@{ URL = $xmqrUrl; HTTP = [int]$xmqrResposta.StatusCode }
    } catch {
        [pscustomobject]@{ URL = $xmqrUrl; HTTP = 'FALHOU: conferir serviço/porta' }
    }
}
```

Esperado: três respostas HTTP 200. Isso não significa que o login do Admin
ou uma entrega MQTT já tenham sido testados.

## 6. Conexão MQTT ativa

```powershell
$xmqrMetricas = (Invoke-WebRequest -Uri 'http://127.0.0.1:9090/metrics' -TimeoutSec 5 -NoProxy).Content
$xmqrMetricas -split "`n" |
    Where-Object { $_ -match '^xmqr_connections_(active|total) ' }
```

Com o Client conectado, espere pelo menos uma conexão ativa. O contador total
é acumulado, pode crescer a cada reconexão e não identifica sozinho o Client.

## 7. Observar 120 segundos sem parar nada

```powershell
$xmqrRelogio = [Diagnostics.Stopwatch]::StartNew()
try {
    do {
        $xmqrEstado = @(Get-Service -Name $xmqrServicos -ErrorAction Stop)
        $xmqrParados = @($xmqrEstado | Where-Object Status -ne 'Running')
        if ($xmqrParados.Count -gt 0) {
            $xmqrParados | Format-Table Name, Status
            throw 'Um serviço deixou de estar Running durante a observação.'
        }
        '{0}s: três serviços Running' -f [int]$xmqrRelogio.Elapsed.TotalSeconds
        if ($xmqrRelogio.Elapsed.TotalSeconds -ge 120) { break }
        Start-Sleep -Seconds 10
    } while ($true)
} finally { $xmqrRelogio.Stop() }
```

Esperado: chegar a 120s sem erro. Depois repita o teste 6. Isso ajuda a verificar
a correção do encerramento do Client após 90s, sem substituir um teste prolongado.

## 8. Publicar e confirmar uma mensagem MQTT de teste

Este bloco **envia uma mensagem sintética** ao tópico local autorizado
`xmqr/local/test`. Usa a CA, certificado e senha privada já preparados; não
exibe seus conteúdos e não altera configurações. O Client serviço deve estar
Running. O publicador usa um client-id diferente para não derrubar a assinatura.

```powershell
$xmqrCertificados = Join-Path $xmqrDados 'client-default\certificates'
$xmqrMensagem = 'xmqr-check-' + [Guid]::NewGuid().ToString('N')
$xmqrPublicacao = @(
    'pub', '--host', '127.0.0.1', '--port', '8883',
    '--username', 'xmqr-local',
    '--ca', (Join-Path $xmqrCertificados 'ca.crt'),
    '--cert', (Join-Path $xmqrCertificados 'client.crt'),
    '--key', (Join-Path $xmqrCertificados 'client.key'),
    '--password-file', (Join-Path $xmqrCertificados 'password'),
    '--topic', 'xmqr/local/test', '--message', $xmqrMensagem,
    '--qos', '1', '--protocol-version', '3.1.1',
    '--client-id', ('xmqr-check-' + [Guid]::NewGuid().ToString('N')),
    '--timeout-seconds', '8', '--total-timeout-seconds', '20'
)
& $xmqrCliente @xmqrPublicacao
if ($LASTEXITCODE -ne 0) { throw 'Publicação recusada; não altere TLS/ACL. Colete diagnóstico.' }
$xmqrSink = Join-Path $xmqrDados 'client-default\state\messages.ndjson'
$xmqrRecebido = $false
for ($xmqrTentativa = 0; $xmqrTentativa -lt 10; $xmqrTentativa++) {
    $xmqrRecebido = Test-Path -LiteralPath $xmqrSink
    if ($xmqrRecebido) {
        $xmqrRecebido = [bool](Select-String -LiteralPath $xmqrSink -Pattern $xmqrMensagem -SimpleMatch -Quiet)
    }
    if ($xmqrRecebido) { break }
    Start-Sleep -Seconds 1
}
if (-not $xmqrRecebido) { throw 'Mensagem sintética não confirmada no sink em até 10s.' }
'PASS: mensagem sintética recebida pelo Client serviço.'
```

Esperado: publicação com código de saída zero e a linha PASS. Não despeje o
sink inteiro no chat: ele pode conter mensagens reais. Esse teste demonstra
entrega interna Broker/Client, não interoperabilidade com outro fabricante ou
garantia de processamento pelo seu aplicativo final. Caso tenha personalizado
portas, usuário, tópico ou caminhos, adapte ao perfil local antes de executar.

## 9. Abrir Admin e conferir Manager/bandeja

```powershell
Start-Process 'http://127.0.0.1:9080/'
Get-Process -Name 'xmqr-manager' -ErrorAction SilentlyContinue |
    Select-Object ProcessName, Id, SessionId
Get-ItemPropertyValue -LiteralPath 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run' -Name 'XMQR Manager'
```

Admin: confirme abertura da página e login. Se ainda for o primeiro acesso,
configure a conta pela interface local; o código de ativação fica no arquivo
privado `C:\ProgramData\XMQR\admin\state\token`. Não envie esse código no chat.
Um HTTP 401 em endpoint protegido sem login é esperado.

Manager: confira a bandeja e os ícones ocultos perto do relógio. A chave Run
mostra a configuração de login; não comprova que o Windows a executou. O Manager
deve aparecer na sessão normal do usuário. Se estiver ausente, execute o próximo
comando **em PowerShell normal, sem administrador**, para abrir a interface:

```powershell
Start-Process 'C:\Program Files\XMQR\Manager\xmqr-manager.exe'
```

Confira visualmente: apenas componentes instalados no menu; verde quando em
execução e apagado quando parado; iniciar/parar/reiniciar com UAC; acesso do
Broker ao arquivo de configuração e à pasta de certificados. Não desinstale
componentes desta máquina apenas para testar ausência; esse cenário exige VM.
Os testes de controle seguintes causam interrupção e são opcionais.

## 10. Controle de serviços — temporariamente suspenso

**Revisão de 22/10/2026:** foi relatada falha do Client após parte dos testes.
Não repita os ciclos anteriores de parar/iniciar/reiniciar até obter o
resultado do diagnóstico. A versão anterior colocou Start e Restart no mesmo
bloco, sem espera de estabilidade; essa sequência não deve ser usada para
aceitar o serviço. O estado Running sozinho pode anteceder a conexão MQTT.

Use a coleta da seção 12 em PowerShell administrativo e envie o JSON ao Codex.
O coletor não inicia nem para serviços. Não reinstale, não rode o inicializador,
não apague mensagens/certificados e não altere permissões para tentar corrigir.
Os testes de controle serão retomados com espera por estado, prontidão do
Broker e observação da conexão, depois de identificarmos o erro real.

## 11. Atalhos e acesso às pastas

```powershell
$xmqrAtalhos = @(
    [Environment]::GetFolderPath('CommonDesktopDirectory'),
    [Environment]::GetFolderPath('DesktopDirectory'),
    (Join-Path $env:ProgramData 'Microsoft\Windows\Start Menu\Programs\XMQR')
)
foreach ($xmqrPasta in $xmqrAtalhos) {
    Get-ChildItem -LiteralPath $xmqrPasta -Filter '*XMQR*.lnk' -ErrorAction SilentlyContinue |
        Select-Object Name, FullName
}
explorer.exe 'C:\Program Files\XMQR'
explorer.exe 'C:\ProgramData\XMQR\broker'
explorer.exe 'C:\ProgramData\XMQR\broker\certificates'
```

Confira também pelo menu da bandeja e pela pesquisa do Windows. Acesso negado
em pastas privadas pode exigir elevação; não mude ACLs para liberar o acesso.
Listar um atalho não comprova que o destino abre: clique nos atalhos instalados.

## 12. Diagnóstico para enviar ao Codex Desktop

```powershell
& (Join-Path $xmqrProjeto 'xmqr\scripts\collect_windows_installed_diagnostics.ps1')
explorer.exe (Join-Path $xmqrProjeto 'xmqr\target\p244-diagnostic')
```

Envie `installed-diagnostics.json` e os resultados PASS/erro dos testes. O coletor
consulta metadados/status e mensagens permitidas; não inicia nem para serviços.
Não envie token, senha, chaves privadas, TOMLs privados ou o sink de mensagens.

## Anotar o resultado

Marque PASS, FAIL ou NÃO EXECUTADO para: boot dos serviços; versões/hash;
HTTP; conexão ativa; 120s; publicação/recebimento; login Admin; Manager no login;
cores e controles da bandeja; atalhos; acesso às pastas do Broker.
Registre a mensagem de erro e o teste onde ocorreu, sem segredos.
Não reinstale nem execute o inicializador como tentativa genérica de correção.

## Hospedar em outro servidor: certificados

O preparo local usou certificado de servidor para localhost/127.0.0.1.
Para acesso por outro domínio ou IP, emita um certificado de servidor cujo
Subject Alternative Name (SAN) contenha exatamente esse domínio/IP. Não basta
copiar o certificado local para uma VPS. No modo secure-mtls atual do XMQR,
provisione certificado/chave próprios por dispositivo, CA confiável e suas
credenciais/permissões MQTT. A CA pode assinar vários certificados; não precisa
criar outra CA para cada servidor ou dispositivo. Para produção, separe o
material de confiança e as chaves do laboratório local. Certificados não
substituem configuração de listener, firewall, usuários e ACL de produção.
Nenhum certificado de produção foi gerado por este roteiro.

Referências: https://www.rfc-editor.org/rfc/rfc9525.html (SAN/identidade do
servidor) e https://mosquitto.org/man/mosquitto-tls-7.html (TLS e certificados).

## Reparo P251 para o incidente de acesso negado

O relatório de 22/10/2026 04:27:53UTC confirmou uma permissão individual
adicional na pasta client-default, incompatível com a política do processo
LocalService. Os arquivos privados e o sink vazio não são a causa identificada.
Para ESTE caso, foi preparado reparo restrito. Em PowerShell7.5+x64 elevado:

```powershell
& (Join-Path $xmqrProjeto 'xmqr\scripts\repair_windows_client_directory_acl.ps1') -StartServices
```

O script exige a pasta, conta, imagem, estado e permissões do caso diagnosticado;
remove somente a regra adicional do usuário atual. Guarda SDDL anterior no
target do projeto, verifica proteção dos filhos para impedir propagação e
preserva owner/grupo/regras de serviço. Não modifica certificados, senha,
configuração ou mensagens. Se algo divergir, interrompe e pede diagnóstico.
Depois inicia Broker, espera /ready200, inicia Client/Admin e observa120s.
Aguarde a conclusão; se falhar, execute a coleta da seção12 e informe o erro.
Não restaure permissões genéricas nem reinstale como tentativa de correção.
