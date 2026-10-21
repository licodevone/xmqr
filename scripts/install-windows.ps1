# SPDX-License-Identifier: MIT
# Explicit operator action only. The build process never executes this script.
[CmdletBinding(DefaultParameterSetName = 'Components')]
param(
    [Parameter(ParameterSetName = 'Components')]
    [ValidateSet('broker', 'client', 'admin')]
    [string[]] $Components = @(),
    [Parameter(Mandatory, ParameterSetName = 'Manager')]
    [switch] $ManagerOnly,
    [string] $PackageDirectory = $PSScriptRoot,
    [switch] $Passive,
    [switch] $AcceptLicense
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ($Passive -and -not $AcceptLicense) {
    throw 'Para instalar em modo passivo, leia TERMS.pt-BR.txt e informe -AcceptLicense explicitamente. Sem -Passive, o assistente solicita o aceite.'
}
$manifestPath = Join-Path $PackageDirectory 'manifest.json'
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ($manifest.schema -ne 1 -or $manifest.target -ne 'x86_64-pc-windows-msvc') {
    throw 'Unsupported package manifest.'
}
Write-Host 'XMQR - instalacao dos componentes Windows'
Write-Host 'Cada pacote abre seu assistente. Os servicos exigem configuracao antes de iniciar.'
if (-not $ManagerOnly -and $Components.Count -eq 0) {
    $Components = @($manifest.packages | Where-Object { $_.kind -in @('broker', 'client', 'admin') } | ForEach-Object { $_.kind })
}
$selected = if ($ManagerOnly) { @('manager') } else { @('manager') + @($Components | Select-Object -Unique) }
$verified = @()

function Get-PackageSha256([string] $Path) {
    $stream = [IO.File]::OpenRead($Path)
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($algorithm.ComputeHash($stream)).Replace('-', '').ToLowerInvariant() }
    finally { $algorithm.Dispose(); $stream.Dispose() }
}

foreach ($kind in $selected) {
    $matches = @($manifest.packages | Where-Object { $_.kind -eq $kind })
    if ($matches.Count -ne 1) { throw "Exactly one $kind package is required." }
    $package = $matches[0]
    if ($package.file -notmatch '^xmqr-[a-z]+-[0-9]+\.[0-9]+\.[0-9]+-windows-x64-experimental\.msi$') {
        throw 'Invalid package file name.'
    }
    $path = [IO.Path]::GetFullPath((Join-Path $PackageDirectory $package.file))
    if ($path.Contains('"')) { throw 'Invalid package path.' }
    $hash = Get-PackageSha256 $path
    if ($hash -ine $package.sha256) { throw "Checksum mismatch: $($package.file)" }
    $verified += [pscustomobject]@{ Kind = $kind; Path = $path }
}
# Verify everything before the first installation; MSI performs its own rollback.
# Read protected 64-bit machine metadata, never a mutable SystemRoot environment variable.
function Get-MachinePath([string] $Key, [string] $Name) {
    $base = [Microsoft.Win32.RegistryKey]::OpenBaseKey([Microsoft.Win32.RegistryHive]::LocalMachine, [Microsoft.Win32.RegistryView]::Registry64)
    try {
        $entry = $base.OpenSubKey($Key, $false)
        if ($null -eq $entry) { throw "Machine installation metadata unavailable: $Key" }
        try { $value = $entry.GetValue($Name, $null, [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames) }
        finally { $entry.Dispose() }
    } finally { $base.Dispose() }
    if ($value -isnot [string] -or $value -notmatch '^[A-Za-z]:\\' -or $value.Contains('"')) {
        throw 'Invalid protected installation path.'
    }
    return $value
}
$windowsRoot = Get-MachinePath 'SOFTWARE\Microsoft\Windows NT\CurrentVersion' 'SystemRoot'
$installer = Join-Path $windowsRoot 'System32/msiexec.exe'
$localData = [Environment]::GetFolderPath([Environment+SpecialFolder]::LocalApplicationData)
if ([string]::IsNullOrWhiteSpace($localData)) { throw 'Pasta de logs do usuario indisponivel.' }
$logDirectory = Join-Path (Join-Path $localData 'XMQR\InstallLogs') ([Guid]::NewGuid().ToString('N'))
$null = New-Item -ItemType Directory -Path $logDirectory -Force
$results = @()
$restartRequired = $false

function Get-MsiArguments([string] $MsiPath, [string] $LogPath, [bool] $UsePassive) {
    foreach ($value in @($MsiPath, $LogPath)) {
        if ($value.Contains('"') -or $value.Contains("`r") -or $value.Contains("`n")) { throw 'Caminho MSI/log invalido.' }
    }
    $ui = if ($UsePassive) { ' /passive' } else { ' /qf' }
    return '/i "' + $MsiPath + '"' + $ui + ' /norestart /L*V "' + $LogPath + '"'
}

try {
    foreach ($item in $verified) {
        $logPath = Join-Path $logDirectory ($item.Kind + '.log')
        Write-Host ("Instalando {0}... Log: {1}" -f $item.Kind, $logPath)
        $arguments = Get-MsiArguments $item.Path $logPath ([bool]$Passive)
        if ($AcceptLicense) { $arguments += ' XMQR_ACCEPT_LICENSE=1' }
        try {
            $process = Start-Process -FilePath $installer -ArgumentList $arguments -Verb RunAs -Wait -PassThru
        } catch {
            $results += [pscustomobject]@{ Component = $item.Kind; Result = 'LAUNCH_FAILED_OR_UAC_CANCELLED'; ExitCode = $null; Log = $logPath }
            throw
        }
        $outcome = if ($process.ExitCode -in @(0, 3010)) { 'SUCCESS' } elseif ($process.ExitCode -eq 1602) { 'CANCELLED' } else { 'FAILED' }
        $results += [pscustomobject]@{ Component = $item.Kind; Result = $outcome; ExitCode = $process.ExitCode; Log = $logPath }
        if ($process.ExitCode -eq 1602) { throw "Instalacao cancelada: $($item.Kind). Veja $logPath" }
        if ($outcome -eq 'FAILED') { throw "Falha ao instalar $($item.Kind), codigo $($process.ExitCode). Veja $logPath. Pacotes restantes nao foram executados." }
        if ($process.ExitCode -eq 3010) { $restartRequired = $true }
        $registrationKey = if ($item.Kind -eq 'manager') { 'SOFTWARE\XMQR\Manager' } else {
            $id = if ($item.Kind -eq 'client') { 'client-default' } else { $item.Kind }
            "SOFTWARE\XMQR\Components\$id"
        }
        try {
            $installedExecutable = Get-MachinePath $registrationKey 'Executable'
            if (-not (Test-Path -LiteralPath $installedExecutable -PathType Leaf)) { throw 'Executavel registrado nao encontrado.' }
        } catch {
            $results[-1].Result = 'REGISTRATION_VERIFY_FAILED'
            throw "O MSI retornou sucesso, mas o registro/executavel de $($item.Kind) nao foi confirmado. Veja $logPath e execute diagnose-windows.ps1."
        }
        Write-Host ("Concluido: {0}." -f $item.Kind)
    }
} finally {
    [ordered]@{ Results = @($results); RestartRequired = $restartRequired } |
        ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $logDirectory 'result.json') -Encoding UTF8
    Write-Host "Resultado e logs: $logDirectory"
}
# This process normally runs as the interactive user. Do not elevate the tray.
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    $manager = Get-MachinePath 'SOFTWARE\XMQR\Manager' 'Executable'
    if (Test-Path -LiteralPath $manager -PathType Leaf) {
        Start-Process -FilePath $manager -WindowStyle Hidden
    } else {
        Write-Warning 'O instalador terminou, mas o executavel da bandeja nao foi encontrado. Execute diagnose-windows.ps1.'
    }
} else {
    Write-Host 'Abra XMQR Manager pelo menu Iniciar em sua sessao normal, ou entre novamente no Windows.'
}
Write-Host 'Instalacao concluida. Se escolheu criar atalhos, pesquise XMQR Manager no menu Iniciar ou abra o atalho da Area de Trabalho.'
Write-Host 'Broker, client e admin operam como servicos. Prepare configuracoes e credenciais antes de inicia-los pela bandeja.'
if ($restartRequired) { Write-Host 'O Windows Installer informou que uma reinicializacao esta pendente.' }
