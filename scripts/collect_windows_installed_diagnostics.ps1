# SPDX-License-Identifier: MIT
# Read-only administrative diagnosis; never starts/stops services or changes ACLs.
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not [Environment]::Is64BitProcess -or -not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Execute em PowerShell 64-bit como administrador. O coletor apenas le status e metadados; nao muda servicos.'
}
$project = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$output = Join-Path $project 'target\p244-diagnostic'
$null = New-Item -ItemType Directory -Path $output -Force
$cursor = Get-Item -LiteralPath $output -Force
while ($null -ne $cursor) {
    if (($cursor.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Diretorio de relatorio com reparse point recusado.' }
    $cursor = $cursor.Parent
}

function Get-Sha256([string] $Path) {
    $file = [IO.File]::OpenRead($Path)
    $hash = [Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($hash.ComputeHash($file)).Replace('-', '').ToLowerInvariant() }
    finally { $hash.Dispose(); $file.Dispose() }
}
function Get-FileMetadata([string] $Path) {
    try {
        if (-not (Test-Path -LiteralPath $Path -ErrorAction Stop)) { return [pscustomobject]@{ Exists = $false } }
        $item = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { return [pscustomobject]@{ Exists = $true; Error = 'REPARSE_REFUSED' } }
        $acl = Get-Acl -LiteralPath $Path -ErrorAction Stop
        return [pscustomobject]@{ Exists = $true; OwnerSid = $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value; ProtectedDacl = $acl.AreAccessRulesProtected; Sddl = $acl.Sddl }
    } catch { return [pscustomobject]@{ Exists = $null; Error = 'QUERY_FAILED' } }
}
function Get-SinkMetadata([string] $Path) {
    try {
        if (-not (Test-Path -LiteralPath $Path -PathType Leaf -ErrorAction Stop)) {
            return [pscustomobject]@{ Exists = $false }
        }
        $cursor = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
        while ($null -ne $cursor) {
            if (($cursor.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                return [pscustomobject]@{ Exists = $true; Error = 'REPARSE_REFUSED' }
            }
            $cursor = if ($cursor -is [IO.FileInfo]) { $cursor.Directory } else { $cursor.Parent }
        }
        $file = [IO.File]::Open($Path, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::ReadWrite)
        try {
            $length = $file.Length
            $endsInLf = $null
            if ($length -gt 0) {
                $null = $file.Seek($length - 1, [IO.SeekOrigin]::Begin)
                $endsInLf = $file.ReadByte() -eq 10
            }
            return [pscustomobject]@{
                Exists = $true; Length = $length; EndsInLf = $endsInLf
                LengthUnchangedDuringRead = ($file.Length -eq $length)
                PackagedReferenceLimitBytes = 8388608
            }
        } finally { $file.Dispose() }
    } catch { return [pscustomobject]@{ Exists = $null; Error = 'QUERY_FAILED' } }
}
$base = [Microsoft.Win32.RegistryKey]::OpenBaseKey([Microsoft.Win32.RegistryHive]::LocalMachine, [Microsoft.Win32.RegistryView]::Registry64)
$programData = [Environment]::GetFolderPath([Environment+SpecialFolder]::CommonApplicationData)
$rows = @()
try {
    foreach ($entry in @(
        @{ Id='broker'; Service='xmqr-broker'; Files=@('certificates\server.crt','certificates\server.key','certificates\ca.crt','users.toml','acl.toml') },
        @{ Id='client-default'; Service='xmqr-client-default'; Files=@('state\messages.ndjson') },
        @{ Id='admin'; Service='xmqr-admin'; Files=@('state\token') }
    )) {
        $component = if ($entry.Id -eq 'client-default') { 'client' } else { $entry.Id }
        $data = Join-Path (Join-Path $programData 'XMQR') $entry.Id
        $registration = $base.OpenSubKey(('SOFTWARE\XMQR\Components\' + $entry.Id), $false)
        if ($null -eq $registration) {
            $rows += [pscustomobject]@{ Component=$component; Installed=$false }
            continue
        }
        try { $executable = $registration.GetValue('Executable'); $config = $registration.GetValue('ConfigFile') }
        finally { $registration.Dispose() }
        $expectedConfig = [IO.Path]::GetFullPath((Join-Path $data ($component + '.toml')))
        if ($config -isnot [string] -or -not [string]::Equals([IO.Path]::GetFullPath($config), $expectedConfig, [StringComparison]::OrdinalIgnoreCase)) {
            $rows += [pscustomobject]@{ Component=$component; Installed=$true; Error='NONDEFAULT_CONFIG_NOT_INSPECTED' }
            continue
        }
        try {
            $service = Get-CimInstance -ClassName Win32_Service -Filter ("Name='" + $entry.Service + "'") -ErrorAction Stop
            $status = if ($null -eq $service) { @{ State='MISSING' } } else {
                @{ State=$service.State; ExitCode=$service.ExitCode; ServiceSpecificExitCode=$service.ServiceSpecificExitCode; StartMode=$service.StartMode; Account=$service.StartName; ProcessId=$service.ProcessId }
            }
        } catch { $status = @{ State='QUERY_FAILED' } }
        $metadata = [ordered]@{}
        foreach ($name in @('.', ($component + '.toml'), 'logs', 'state') + $entry.Files) {
            $metadata[$name] = Get-FileMetadata (Join-Path $data $name)
        }
        $template = Join-Path $project ('packaging\windows\' + $component + '.toml')
        $sameTemplate = $null
        try { $sameTemplate = (Get-Sha256 $config) -eq (Get-Sha256 $template) } catch {}
        $log = Join-Path $data 'logs\service.log'
        $allowedMessages = @('starting','running','stopped','control handler failed','start status failed',
            'failure: unsupported platform operation','failure: access denied','failure: required file or directory missing',
            'failure: invalid configuration or data','failure: listener address already in use','failure: operation timed out',
            'failure: input/output operation','failure: application initialization or runtime',
            'failed: initialization or runtime; check platform prerequisites and configuration')
        $lifecycle = @()
        try {
            foreach ($line in @(Get-Content -LiteralPath $log -Tail 35 -ErrorAction Stop)) {
                if ($line -match '^(\d+) (.+)$' -and $Matches[2] -in $allowedMessages) { $lifecycle += $line }
            }
        } catch { $lifecycle = @('LOG_UNAVAILABLE') }
        $sink = if ($component -eq 'client') { Get-SinkMetadata (Join-Path $data 'state\messages.ndjson') } else { $null }
        $rows += [pscustomobject]@{ Component=$component; Installed=$true; ExecutableExists=(Test-Path -LiteralPath $executable -PathType Leaf); Service=$status; ConfigEqualsPackagedTemplate=$sameTemplate; Files=$metadata; Lifecycle=$lifecycle; Sink=$sink }
    }
} finally { $base.Dispose() }
$listeners = @()
$listenerError = $null
try {
    $listeners = @(Get-NetTCPConnection -State Listen -ErrorAction Stop |
        Where-Object LocalPort -in @(8883,9090,9080) |
        Select-Object LocalAddress,LocalPort,OwningProcess)
} catch { $listenerError = 'QUERY_FAILED' }
$report = [ordered]@{ Schema=1; CreatedUtc=[DateTime]::UtcNow.ToString('o'); ReadOnly=$true; Components=@($rows); Listeners=$listeners; ListenerQueryError=$listenerError }
$path = Join-Path $output 'installed-diagnostics.json'
$report | ConvertTo-Json -Depth 9 | Set-Content -LiteralPath $path -Encoding UTF8
Write-Output "Diagnostico somente leitura salvo em $path"
