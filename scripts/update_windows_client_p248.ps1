#requires -Version 7.5
# SPDX-License-Identifier: MIT
# Operator-run binary hotfix only. Never rewrites configuration, credentials or ACLs.
[CmdletBinding()]
param([switch] $ProbeBroker)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Assert-XmqrP248Path([string] $Path, [bool] $Directory = $false) {
    if (-not [IO.Path]::IsPathFullyQualified($Path) -or $Path -notmatch '^[A-Za-z]:\\' -or $Path.Substring(2).Contains(':')) {
        throw 'Caminho local explicito necessario; UNC/device/streams recusados.'
    }
    $item = Get-Item -LiteralPath $Path -Force
    if ($item.PSIsContainer -ne $Directory) { throw 'Tipo inesperado de arquivo/diretorio.' }
    $cursor = $item
    while ($null -ne $cursor) {
        if (($cursor.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Reparse point recusado.' }
        $cursor = if ($cursor -is [IO.FileInfo]) { $cursor.Directory } else { $cursor.Parent }
    }
    return $item.FullName
}
function Get-XmqrP248Hash([string] $Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}
function Get-XmqrP248MachineValue([string] $Key, [string] $Name) {
    $base = [Microsoft.Win32.RegistryKey]::OpenBaseKey([Microsoft.Win32.RegistryHive]::LocalMachine, [Microsoft.Win32.RegistryView]::Registry64)
    try {
        $entry = $base.OpenSubKey($Key, $false)
        if ($null -eq $entry) { throw 'Registro do Client instalado ausente.' }
        try { $value = $entry.GetValue($Name, $null, [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames) }
        finally { $entry.Dispose() }
    } finally { $base.Dispose() }
    if ($value -isnot [string] -or [string]::IsNullOrWhiteSpace($value)) { throw 'Registro do Client instalado invalido.' }
    return $value
}
function Assert-XmqrP248Capabilities([string] $Executable) {
    $start = [Diagnostics.ProcessStartInfo]::new()
    $start.FileName = $Executable
    $start.ArgumentList.Add('--windows-service-capabilities')
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $start
    try {
        if (-not $process.Start()) { throw 'Falha ao consultar capacidades do candidato.' }
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit(15000)) { throw 'Candidato excedeu limite de consulta de capacidades.' }
        $text = $stdout.GetAwaiter().GetResult()
        $null = $stderr.GetAwaiter().GetResult()
        if ($process.ExitCode -ne 0 -or $text.Length -gt 4096) { throw 'Candidato recusado na consulta de capacidades.' }
        $capabilities = $text | ConvertFrom-Json
        if ($capabilities.schema -ne 1 -or $capabilities.component -cne 'client' -or
            $capabilities.service_entrypoint -isnot [bool] -or -not $capabilities.service_entrypoint) {
            throw 'Candidato nao identifica o adaptador Windows do Client.'
        }
    } finally {
        try { if (-not $process.HasExited) { $process.Kill($true) } } catch {}
        $process.Dispose()
    }
}
function Copy-XmqrP248NewFile([string] $Source, [string] $Destination) {
    $inputStream = [IO.File]::Open($Source, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
    try {
        $outputStream = [IO.File]::Open($Destination, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
        try { $inputStream.CopyTo($outputStream); $outputStream.Flush($true) }
        finally { $outputStream.Dispose() }
    } finally { $inputStream.Dispose() }
}
function Replace-XmqrP248Binary {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string] $Source,
        [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string] $Destination,
        [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string] $BackupPath,
        [Parameter(Mandatory)][ValidatePattern('^[a-fA-F0-9]{64}$')][string] $SourceHash,
        [Parameter(Mandatory)][ValidatePattern('^[a-fA-F0-9]{64}$')][string] $DestinationHash
    )
    if (Test-Path -LiteralPath $BackupPath) { throw 'Backup existente preservado.' }
    if ((Get-XmqrP248Hash $Source) -ne $SourceHash -or (Get-XmqrP248Hash $Destination) -ne $DestinationHash) {
        throw 'Executavel mudou; substituicao cancelada e arquivos preservados.'
    }
    [IO.File]::Replace($Source, $Destination, $BackupPath)
}
function Stop-XmqrP248Client($Service) {
    $Service.Refresh()
    if ($Service.Status -eq [ServiceProcess.ServiceControllerStatus]::Stopped) { return }
    if ($Service.Status -ne [ServiceProcess.ServiceControllerStatus]::Running -or
        @($Service.DependentServices | Where-Object { $_.Status -ne 'Stopped' }).Count -ne 0) {
        throw 'Client em transicao ou com dependentes ativos; parada recusada.'
    }
    # Explicit false prevents ServiceController from stopping dependent services.
    $Service.Stop($false)
    $Service.WaitForStatus([ServiceProcess.ServiceControllerStatus]::Stopped, [TimeSpan]::FromSeconds(20))
}
function Start-XmqrP248Client($Service) {
    $Service.Refresh()
    if ($Service.Status -eq [ServiceProcess.ServiceControllerStatus]::Stopped) { $Service.Start() }
    elseif ($Service.Status -ne [ServiceProcess.ServiceControllerStatus]::Running) { throw 'Client em transicao; inicio recusado.' }
    $Service.WaitForStatus([ServiceProcess.ServiceControllerStatus]::Running, [TimeSpan]::FromSeconds(20))
}
function Watch-XmqrP248Client($Service) {
    $watch = [Diagnostics.Stopwatch]::StartNew()
    $nextProgress = 20
    try {
        while ($watch.Elapsed.TotalSeconds -lt 100) {
            $Service.Refresh()
            if ($Service.Status -ne [ServiceProcess.ServiceControllerStatus]::Running) { throw 'Client parou durante a observacao de 100 segundos.' }
            if ($watch.Elapsed.TotalSeconds -ge $nextProgress) {
                Write-Output ("Client em execucao: $nextProgress/100 segundos.")
                $nextProgress += 20
            }
            Write-Progress -Activity 'Validando estabilidade do XMQR Client' -Status 'Observacao de 100 segundos' -PercentComplete ([Math]::Min(99, [int]$watch.Elapsed.TotalSeconds))
            Start-Sleep -Seconds 2
        }
        $Service.Refresh()
        if ($Service.Status -ne [ServiceProcess.ServiceControllerStatus]::Running) { throw 'Client nao permaneceu em execucao.' }
        Write-Output 'Client em execucao: 100/100 segundos.'
    } finally { Write-Progress -Activity 'Validando estabilidade do XMQR Client' -Completed; $watch.Stop() }
}
function Show-XmqrP248BrokerProbe {
    $handler = [Net.Http.HttpClientHandler]::new()
    $handler.AllowAutoRedirect = $false
    $handler.UseProxy = $false
    $http = [Net.Http.HttpClient]::new($handler)
    $http.Timeout = [TimeSpan]::FromSeconds(3)
    try {
        foreach ($endpoint in @('ready', 'metrics')) {
            try {
                $response = $http.GetAsync(('http://127.0.0.1:9090/' + $endpoint), [Net.Http.HttpCompletionOption]::ResponseHeadersRead).GetAwaiter().GetResult()
                try { Write-Output ("Broker /${endpoint}: HTTP " + [int]$response.StatusCode) }
                finally { $response.Dispose() }
            } catch { Write-Output ("Broker /${endpoint}: consulta indisponivel.") }
        }
    } finally { $http.Dispose() }
}

if (-not $IsWindows -or -not [Environment]::Is64BitProcess) { throw 'Use PowerShell 7.5+ Windows 64-bit como administrador.' }
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
try {
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Execute este atualizador em PowerShell como administrador.' }
} finally { $identity.Dispose() }
$serviceName = 'xmqr-client-default'
$installed = Assert-XmqrP248Path 'C:\Program Files\XMQR\Client\mqtt-client.exe'
$config = Assert-XmqrP248Path 'C:\ProgramData\XMQR\client-default\client.toml'
$installFolder = Assert-XmqrP248Path 'C:\Program Files\XMQR\Client' $true
$null = Assert-XmqrP248Path 'C:\ProgramData\XMQR\client-default\logs' $true
$componentKey = 'SOFTWARE\XMQR\Components\client-default'
foreach ($field in @(@('Executable', $installed), @('ConfigFile', $config), @('ServiceName', $serviceName), @('Kind', 'client'))) {
    if (-not [string]::Equals((Get-XmqrP248MachineValue $componentKey $field[0]), $field[1], [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Registro nao corresponde ao Client padrao; atualizacao recusada.'
    }
}
$record = Get-CimInstance -ClassName Win32_Service -Filter "Name='xmqr-client-default'"
$expectedCommand = '"C:\Program Files\XMQR\Client\mqtt-client.exe" --windows-service xmqr-client-default "C:\ProgramData\XMQR\client-default\logs\." --config "C:\ProgramData\XMQR\client-default\client.toml"'
if ($null -eq $record -or $record.StartName -ne 'NT AUTHORITY\LocalService' -or
    -not [string]::Equals($record.PathName, $expectedCommand, [StringComparison]::OrdinalIgnoreCase) -or
    $record.State -notin @('Stopped', 'Running')) { throw 'Servico Client nao esta na conta/caminho/estado esperados.' }
$sourceFolder = Join-Path (Split-Path $PSScriptRoot -Parent) 'dist/windows/p248-client-hotfix'
if (-not (Test-Path -LiteralPath (Join-Path $sourceFolder 'mqtt-client.exe')) -and
    -not (Test-Path -LiteralPath (Join-Path $sourceFolder 'manifest.json'))) { $sourceFolder = $PSScriptRoot }
$null = Assert-XmqrP248Path $sourceFolder $true
$candidate = Assert-XmqrP248Path (Join-Path $sourceFolder 'mqtt-client.exe')
$manifestPath = Assert-XmqrP248Path (Join-Path $sourceFolder 'manifest.json')
$manifestFile = Get-Item -LiteralPath $manifestPath
if ($manifestFile.Length -gt 16384) { throw 'Manifesto do hotfix excede limite.' }
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ($manifest.schema -ne 1 -or $manifest.component -cne 'client' -or $manifest.sha256 -isnot [string] -or
    $manifest.sha256 -cnotmatch '^[a-f0-9]{64}$') { throw 'Manifesto do hotfix invalido.' }
$newHash = $manifest.sha256
if ((Get-XmqrP248Hash $candidate) -cne $newHash) { throw 'SHA-256 do candidato diverge do manifesto; nada foi alterado.' }
Assert-XmqrP248Capabilities $candidate
if ((Get-XmqrP248Hash $candidate) -cne $newHash) { throw 'Candidato mudou durante a verificacao; nada foi alterado.' }
$oldHash = Get-XmqrP248Hash $installed
$service = Get-Service -Name $serviceName
$service.Refresh()
if ($service.Status.ToString() -notin @('Stopped', 'Running')) { throw 'Client mudou de estado antes da atualizacao.' }
$wasRunning = $service.Status -eq [ServiceProcess.ServiceControllerStatus]::Running
$backupFolder = $null; $backupPath = $null; $swapAttempted = $false
try {
    Write-Output 'Atualizando somente o executavel do XMQR Client; aguarde a observacao de 100 segundos.'
    Stop-XmqrP248Client $service
    if ((Get-XmqrP248Hash $installed) -cne $oldHash) { throw 'Executavel instalado mudou; atualizacao interrompida.' }
    $backupFolder = Join-Path $installFolder ('p248-backup-' + [Guid]::NewGuid().ToString('N'))
    if (Test-Path -LiteralPath $backupFolder) { throw 'Diretorio de backup existente preservado.' }
    $null = [IO.Directory]::CreateDirectory($backupFolder)
    $null = Assert-XmqrP248Path $backupFolder $true
    $staged = Join-Path $backupFolder 'mqtt-client.new.exe'
    $backupPath = Join-Path $backupFolder 'mqtt-client.previous.exe'
    Copy-XmqrP248NewFile $candidate $staged
    $swapAttempted = $true
    Replace-XmqrP248Binary -Source $staged -Destination $installed -BackupPath $backupPath -SourceHash $newHash -DestinationHash $oldHash
    if ((Get-XmqrP248Hash $installed) -cne $newHash -or (Get-XmqrP248Hash $backupPath) -cne $oldHash) { throw 'Verificacao da substituicao/backup falhou.' }
    Start-XmqrP248Client $service
    Watch-XmqrP248Client $service
    if ($ProbeBroker) { Show-XmqrP248BrokerProbe }
    Write-Output "Atualizacao concluida. Backup anterior preservado em: $backupPath"
} catch {
    $failure = $_
    $restored = $false
    try {
        $currentHash = Get-XmqrP248Hash $installed
        if ($swapAttempted -and $currentHash -ceq $newHash) {
            if (-not $backupPath -or -not (Test-Path -LiteralPath $backupPath) -or (Get-XmqrP248Hash $backupPath) -cne $oldHash) {
                throw 'Backup nao confirmado; arquivos preservados para revisao.'
            }
            Stop-XmqrP248Client $service
            $failedPath = Join-Path $backupFolder 'mqtt-client.failed.exe'
            Replace-XmqrP248Binary -Source $backupPath -Destination $installed -BackupPath $failedPath -SourceHash $oldHash -DestinationHash $newHash
            if ((Get-XmqrP248Hash $installed) -cne $oldHash) { throw 'Restauracao do executavel nao confirmada.' }
            $restored = $true
        } elseif ($currentHash -ceq $oldHash) { $restored = $true }
        else { throw 'Mudanca inesperada no executavel preservada; restauracao automatica recusada.' }
        if ($restored -and $wasRunning) { Start-XmqrP248Client $service }
        Write-Warning 'Atualizacao nao concluida; executavel anterior confirmado. Client anterior reiniciado somente se ja estava em execucao.'
    } catch { Write-Warning 'Recuperacao automatica incompleta. Preserve o backup e colete diagnostico antes de repetir.' }
    throw $failure
} finally { $service.Dispose() }
