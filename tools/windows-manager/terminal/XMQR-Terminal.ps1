#requires -Version 7.0
# SPDX-License-Identifier: MIT
[CmdletBinding()]
param(
    [ValidateSet('menu','status','start','stop','restart','logs','help','version')]
    [string]$Action = 'menu',
    [string]$Target = 'all',
    [string]$ManagerPath,
    [switch]$DryRun
)

function Find-XmqrManager {
    param([string]$Path)
    $candidates = if ($Path) { @($Path) } else { @(
        (Join-Path $PSScriptRoot 'helper/xmqr-manager.exe'),
        [IO.Path]::Combine([Environment]::GetFolderPath('ProgramFiles'), 'XMQR','Manager','xmqr-manager.exe'),
        'C:\XMQR\Manager\xmqr-manager.exe'
    ) }
    foreach ($candidate in $candidates) {
        if ($candidate -notmatch '^[A-Za-z]:[\\/]' -or $candidate.StartsWith('\\') -or
            $candidate.Substring(2).Contains(':') -or $candidate -match '[\x00-\x1f"\x7f]' -or
            [IO.Path]::GetFileName($candidate) -ine 'xmqr-manager.exe') { throw 'Caminho local do Manager invalido.' }
        if (-not [IO.File]::Exists($candidate)) { continue }
        $hash = (Get-FileHash -LiteralPath $candidate -Algorithm SHA256 -ErrorAction Stop).Hash
        if ($hash -ine '3c4e11e1ae9e67e7a01d632d84d6dbf69addda4a85e2202ae0bc12c1e7c5943e') {
            throw 'Executavel difere do Manager Windows 0.1.1 publicado. Use o pacote oficial.'
        }
        return [IO.Path]::GetFullPath($candidate)
    }
    throw 'Manager Windows 0.1.1 nao encontrado. Instale o pacote oficial ou informe -ManagerPath.'
}

function Test-XmqrAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    try { return [Security.Principal.WindowsPrincipal]::new($identity).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator) }
    finally { $identity.Dispose() }
}

function Invoke-XmqrHelper {
    param([string]$ManagerExe, [string[]]$Arguments, [int]$Seconds = 20)
    # Only known verbs and restricted IDs reach ArgumentList; never a command string.
    $valid = ($Arguments.Count -eq 1 -and $Arguments[0] -eq '--diagnose') -or
        ($Arguments.Count -eq 2 -and $Arguments[0] -eq '--control-all' -and $Arguments[1] -cin @('start','stop','restart')) -or
        ($Arguments.Count -eq 3 -and $Arguments[0] -eq '--control' -and $Arguments[1] -cin @('start','stop','restart') -and $Arguments[2] -cmatch '^[A-Za-z0-9-]{1,80}$')
    if (-not $valid) { throw 'Argumentos de helper fora da lista permitida.' }
    $info = [Diagnostics.ProcessStartInfo]::new()
    $info.FileName = $ManagerExe
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $true
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    $info.StandardOutputEncoding = [Text.UTF8Encoding]::new($false)
    $info.StandardErrorEncoding = [Text.UTF8Encoding]::new($false)
    foreach ($argument in $Arguments) { $info.ArgumentList.Add($argument) }
    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $info
    try {
        if (-not $process.Start()) { throw 'Nao foi possivel iniciar o helper.' }
        $output = $process.StandardOutput.ReadToEndAsync()
        $errors = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit($Seconds * 1000)) {
            throw 'Prazo excedido; o helper pode continuar. Reconsulte status antes de repetir.'
        }
        if (-not $output.Wait(1000) -or -not $errors.Wait(1000)) { throw 'Saida do helper indisponivel.' }
        if ($output.Result.Length -gt 2097152 -or $errors.Result.Length -gt 2097152) { throw 'Saida do helper excedeu o limite.' }
        if ($process.ExitCode -ne 0) { throw "Helper recusou a operacao (exit $($process.ExitCode)). Pode haver etapas concluidas; reconsulte status." }
        return $output.Result
    } finally { $process.Dispose() }
}

function Get-XmqrSnapshot {
    param([string]$ManagerExe)
    $raw = Invoke-XmqrHelper -ManagerExe $ManagerExe -Arguments @('--diagnose')
    try { $snapshot = $raw | ConvertFrom-Json -ErrorAction Stop } catch { throw 'JSON de inventario invalido.' }
    if ($null -eq $snapshot -or 'components' -notin $snapshot.PSObject.Properties.Name -or $snapshot.error) {
        throw 'Inventario indisponivel; nenhuma acao de controle autorizada.'
    }
    $entries = @($snapshot.components)
    if ($entries.Count -gt 64) { throw 'Inventario excede 64 componentes.' }
    $ids = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    foreach ($entry in $entries) {
        if ($null -eq $entry -or $entry.id -cnotmatch '^[A-Za-z0-9-]{1,80}$' -or -not $ids.Add($entry.id) -or
            $entry.name -isnot [string] -or $entry.name.Length -gt 120 -or $entry.name -match '[\x00-\x1f\x7f]' -or
            $entry.state -cnotin @('Em execução','Parado','Ainda não iniciado','Em transição','Falha','Estado indisponível','CLI instalada; sem serviço') -or
            ($entry.service -and $entry.service -cnotmatch '^xmqr-(broker|admin|client-[A-Za-z0-9-]{1,64})$') -or
            ($entry.detail -and ($entry.detail -isnot [string] -or $entry.detail.Length -gt 4096 -or $entry.detail -match '[\x00-\x1f\x7f]'))) {
            throw 'Componente invalido no inventario.'
        }
    }
    return $entries
}

function Select-XmqrTargets {
    param([object[]]$Entries, [string]$Name)
    if ($Name -eq 'all') { return $Entries }
    if ($Name -cnotmatch '^[A-Za-z0-9-]{1,80}$') { throw 'ID de componente invalido.' }
    $matches = @($Entries | Where-Object { $_.id -ceq $Name })
    if ($Name -eq 'client') {
        $instances = @($Entries | Where-Object { $_.service -cmatch '^xmqr-client-' })
        if ($instances.Count -gt 1) { throw 'Varios clients instalados; use o ID completo do status.' }
        if ($instances.Count -eq 1) { $matches = $instances }
    }
    if ($matches.Count -ne 1) { throw 'Componente nao instalado; consulte status.' }
    return $matches
}

function Show-XmqrStatus {
    param([object[]]$Entries)
    if ($Entries.Count -eq 0) { Write-Output 'Nenhum software XMQR instalado.'; return }
    $Entries | Select-Object @{n='ID';e={$_.id}}, @{n='Estado';e={$_.state}}, @{n='Servico';e={$_.service}} | Format-Table -AutoSize | Out-Host
    foreach ($entry in $Entries) { if ($entry.detail) { Write-Output "$($entry.id): $($entry.detail)" } }
    Write-Output 'Estado SCM nao comprova readiness MQTT ou entrega de mensagens.'
}

function Get-XmqrServiceEvents {
    param([object[]]$Entries)
    $names = @($Entries | Where-Object service | ForEach-Object { $_.service; $_.name })
    if ($names.Count -eq 0) { throw 'Nenhum servico neste alvo.' }
    $events = @(Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Service Control Manager'; StartTime=(Get-Date).AddDays(-7)} -MaxEvents 1000 -ErrorAction Stop)
    $selected = @($events | Where-Object {
        $values = @(([xml]$_.ToXml()).Event.EventData.Data | ForEach-Object { $_.InnerText })
        @($values | Where-Object { $_ -in $names }).Count -gt 0
    } | Select-Object -First 100)
    if ($selected.Count -eq 0) { Write-Output 'Nenhum evento correspondente nas ultimas 1000 entradas SCM dos sete dias recentes.' }
    else { $selected | Select-Object TimeCreated,Id,LevelDisplayName,Message | Format-List | Out-Host }
}

function Invoke-XmqrTerminalAction {
    param([string]$ManagerExe, [string]$Verb, [string]$Name = 'all', [switch]$Plan)
    if ($Verb -cnotin @('status','start','stop','restart','logs')) { throw 'Acao invalida.' }
    if ($Plan -and $Verb -cnotin @('start','stop','restart')) { throw 'DryRun requer start, stop ou restart.' }
    $control = $Verb -cin @('start','stop','restart')
    if ($control -and -not $Plan -and -not (Test-XmqrAdministrator)) { throw 'Abra o PowerShell como Administrador para controlar servicos.' }
    $entries = @(Get-XmqrSnapshot -ManagerExe $ManagerExe)
    $selected = @(Select-XmqrTargets -Entries $entries -Name $Name)
    if ($Verb -eq 'status') { Show-XmqrStatus $selected; return }
    if ($Verb -eq 'logs') { Get-XmqrServiceEvents $selected; return }
    $services = @($selected | Where-Object service)
    if ($services.Count -eq 0) { throw 'Nenhum servico instalado neste alvo.' }
    foreach ($entry in $services) {
        if ($entry.state -cin @('Em transição','Estado indisponível','CLI instalada; sem serviço') -or
            ($entry.detail -and $entry.state -cnotin @('Falha','Ainda não iniciado'))) { throw 'Estado indisponivel ou em transicao; controle bloqueado.' }
        if ($Name -ne 'all') {
            $allowed = if ($Verb -eq 'start') { $entry.state -cin @('Parado','Ainda não iniciado','Falha') } else { $entry.state -ceq 'Em execução' }
            if (-not $allowed) { throw 'Acao indisponivel para o estado atual.' }
        }
    }
    $arguments = if ($Name -eq 'all') { @('--control-all', $Verb) } else { @('--control', $Verb, $services[0].id) }
    if ($Plan) {
        Write-Output ('PLANO: ' + ($arguments -join ' ') + '. Nenhuma alteracao executada; o helper revalida o inventario e a ordem na execucao.')
        return
    }
    $timeout = if ($Name -eq 'all') { 4600 } else { 60 }
    $null = Invoke-XmqrHelper -ManagerExe $ManagerExe -Arguments $arguments -Seconds $timeout
    $after = @(Get-XmqrSnapshot -ManagerExe $ManagerExe)
    $observed = @(Select-XmqrTargets -Entries $after -Name $Name | Where-Object service)
    Show-XmqrStatus $after
    foreach ($before in $services) {
        $now = @($observed | Where-Object { $_.id -ceq $before.id })
        $wanted = if ($Verb -eq 'stop') { @('Parado','Ainda não iniciado','Falha') } else { @('Em execução') }
        if ($now.Count -ne 1 -or $now[0].state -cnotin $wanted) { throw 'Helper terminou mas estado final nao foi confirmado; confira os servicos.' }
    }
}

function Start-XmqrTerminalMenu {
    param([string]$ManagerExe)
    $options = @{'1'='status';'2'='start';'3'='stop';'4'='restart';'5'='logs'}
    while ($true) {
        Write-Output "`nXMQR Manager Terminal Windows 0.1.0-rc.1"
        Invoke-XmqrTerminalAction -ManagerExe $ManagerExe -Verb status
        Write-Output '1 Status | 2 Iniciar | 3 Parar | 4 Reiniciar | 5 Eventos SCM | 0 Sair'
        $choice = Read-Host 'Opcao'
        if ($choice -eq '0') { return }
        if (-not $options.ContainsKey($choice)) { Write-Output 'Opcao invalida.'; continue }
        $verb = $options[$choice]
        $name = if ($verb -eq 'status') { 'all' } else { Read-Host 'Alvo (broker/admin/client/all ou ID completo)' }
        Invoke-XmqrTerminalAction -ManagerExe $ManagerExe -Verb $verb -Name $name
    }
}

if ($MyInvocation.InvocationName -ne '.') {
    try {
        if ($Action -eq 'version') { Write-Output 'XMQR Manager Terminal Windows 0.1.0-rc.1'; exit 0 }
        if ($Action -eq 'help') {
            Write-Output '.\XMQR-Terminal.ps1 [-Action menu|status|start|stop|restart|logs] [-Target all|broker|admin|client|ID] [-ManagerPath CAMINHO] [-DryRun]'
            exit 0
        }
        if (-not $IsWindows) { throw 'Esta interface requer Windows e PowerShell7.' }
        if ($DryRun -and $Action -notin @('start','stop','restart')) { throw 'DryRun requer start, stop ou restart.' }
        $manager = Find-XmqrManager -Path $ManagerPath
        if ($Action -eq 'menu') { Start-XmqrTerminalMenu $manager }
        else { Invoke-XmqrTerminalAction -ManagerExe $manager -Verb $Action -Name $Target -Plan:$DryRun }
    } catch { Write-Error -Message $_.Exception.Message -ErrorAction Continue; exit 1 }
}
