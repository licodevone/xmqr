#requires -Version 7.5
# SPDX-License-Identifier: MIT
# Initialize only the dedicated, unchanged local installation. Never displays secrets.
[CmdletBinding()]
param(
    [switch] $StartServices,
    [switch] $PrepareOnly,
    [string] $OutputDirectory,
    [ValidateRange(1024,65535)] [int] $MqttPort = 8883,
    [ValidateRange(1024,65535)] [int] $MonitorPort = 9090,
    [ValidateRange(1024,65535)] [int] $AdminPort = 9080
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if (-not $IsWindows -or -not [Environment]::Is64BitProcess) { throw 'Use PowerShell 7 Windows 64-bit.' }
if ($PrepareOnly -and $StartServices) { throw 'PrepareOnly never controls Windows services.' }
if (-not $PrepareOnly -and ($OutputDirectory -or $MqttPort -ne 8883 -or $MonitorPort -ne 9090 -or $AdminPort -ne 9080)) {
    throw 'Installed initialization supports only the existing default local configuration.'
}
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$admins = [Security.Principal.SecurityIdentifier]::new('S-1-5-32-544')
$system = [Security.Principal.SecurityIdentifier]::new('S-1-5-18')
$localService = [Security.Principal.SecurityIdentifier]::new('S-1-5-19')
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $PrepareOnly -and -not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Abra PowerShell 7 como administrador para configurar a instalacao existente.'
}
$repo = Split-Path $PSScriptRoot -Parent
Import-Module (Join-Path $PSScriptRoot 'windows_bootstrap_crypto.psm1') -Force
Import-Module (Join-Path $PSScriptRoot 'windows_private_acl.psm1') -Force
$helper = Join-Path $repo 'bin/xmqr-windows-password-hash.exe'
if (-not (Test-Path -LiteralPath $helper -PathType Leaf)) {
    $helper = Join-Path $repo 'tools/windows-password-hash/target/release/xmqr-windows-password-hash.exe'
}
if (-not (Test-Path -LiteralPath $helper -PathType Leaf)) { throw 'Helper de hash ausente; use o pacote P247 completo.' }

function Assert-LocalPath([string] $Path, [bool] $Exists = $true) {
    $full = [IO.Path]::GetFullPath($Path)
    if ($full -notmatch '^[A-Za-z]:\\' -or $full.Substring(2).Contains(':') -or $full.Contains("'")) {
        throw 'Caminho local com stream/aspas recusado.'
    }
    if ($Exists -and -not (Test-Path -LiteralPath $full)) { throw "Caminho necessario ausente: $full" }
    $cursor = $full
    while (-not (Test-Path -LiteralPath $cursor)) { $cursor = [IO.Path]::GetDirectoryName($cursor) }
    $item = Get-Item -LiteralPath $cursor -Force
    while ($null -ne $item) {
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Reparse point recusado.' }
        $item = if ($item -is [IO.FileInfo]) { $item.Directory } else { $item.Parent }
    }
    return $full
}
function Set-Private([string] $Path, [bool] $Directory, [bool] $ServiceWrite = $false, [bool] $ServiceRead = $false) {
    $acl = if ($Directory) { [Security.AccessControl.DirectorySecurity]::new() } else { [Security.AccessControl.FileSecurity]::new() }
    $acl.SetAccessRuleProtection($true, $false)
    $owner = if ($PrepareOnly) { $identity.User } else { $admins }
    $acl.SetOwner($owner)
    $inherit = if ($Directory) { [Security.AccessControl.InheritanceFlags]::ContainerInherit -bor [Security.AccessControl.InheritanceFlags]::ObjectInherit } else { [Security.AccessControl.InheritanceFlags]::None }
    $sids = @($system, $admins)
    if ($PrepareOnly -and $identity.User.Value -notin @($system.Value, $admins.Value)) { $sids += $identity.User }
    foreach ($sid in $sids) {
        $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($sid, [Security.AccessControl.FileSystemRights]::FullControl, $inherit, [Security.AccessControl.PropagationFlags]::None, [Security.AccessControl.AccessControlType]::Allow))
    }
    if (-not $PrepareOnly -and ($ServiceRead -or $ServiceWrite)) {
        $rights = if ($ServiceWrite) { [Security.AccessControl.FileSystemRights]::Modify } else { [Security.AccessControl.FileSystemRights]::ReadAndExecute }
        $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($localService, $rights, $inherit, [Security.AccessControl.PropagationFlags]::None, [Security.AccessControl.AccessControlType]::Allow))
    }
    if ($Directory) { [IO.FileSystemAclExtensions]::SetAccessControl([IO.DirectoryInfo]::new($Path), $acl) }
    else { [IO.FileSystemAclExtensions]::SetAccessControl([IO.FileInfo]::new($Path), $acl) }
    $actual = Get-Acl -LiteralPath $Path
    if (-not (Test-XmqrPrivateAcl -Actual $actual -Expected $acl)) {
        throw "Politica privada nao confirmada em: $Path. Operacao interrompida; colete diagnostico."
    }
}
function New-PrivateDirectory([string] $Path) {
    $null = Assert-LocalPath $Path $false
    if (Test-Path -LiteralPath $Path) { throw 'Diretorio de preparacao ja existe; escolha um novo.' }
    $null = New-Item -ItemType Directory -Path $Path
    Set-Private $Path $true
}
function Write-NewText([string] $Path, [string] $Text) {
    $stream = [IO.File]::Open($Path, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    try { $bytes = [Text.UTF8Encoding]::new($false).GetBytes($Text); $stream.Write($bytes); $stream.Flush($true) }
    finally { $stream.Dispose() }
}
function Hash([string] $Path) { return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash }
function Replace-XmqrClientConfig {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string] $Source,
        [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string] $Destination,
        [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string] $BackupPath,
        [Parameter(Mandatory)][ValidatePattern('^[a-fA-F0-9]{64}$')][string] $ExpectedHash
    )
    # PowerShell converts an untyped $null string argument into an empty string.
    # Use a real, new backup path for File.Replace, preserving the old file.
    if (Test-Path -LiteralPath $BackupPath) { throw 'Backup atomico existente preservado.' }
    if ((Get-FileHash -LiteralPath $Destination -Algorithm SHA256).Hash -ne $ExpectedHash) {
        throw 'Configuracao Client mudou durante a preparacao.'
    }
    [IO.File]::Replace($Source, $Destination, $BackupPath)
}
function Machine-Value([string] $Key, [string] $Name) {
    $base = [Microsoft.Win32.RegistryKey]::OpenBaseKey([Microsoft.Win32.RegistryHive]::LocalMachine,[Microsoft.Win32.RegistryView]::Registry64)
    try {
        $keyObject = $base.OpenSubKey($Key, $false)
        if ($null -eq $keyObject) { throw "Componente instalado ausente: $Key" }
        try { $value = $keyObject.GetValue($Name) } finally { $keyObject.Dispose() }
    } finally { $base.Dispose() }
    if ($value -isnot [string] -or [string]::IsNullOrWhiteSpace($value)) { throw 'Registro instalado invalido.' }
    return $value
}
$definitions = @(
    @{ Kind='broker'; Id='broker'; Folder='Broker'; Binary='mqtt-broker.exe'; Service='xmqr-broker' },
    @{ Kind='client'; Id='client-default'; Folder='Client'; Binary='mqtt-client.exe'; Service='xmqr-client-default' },
    @{ Kind='admin'; Id='admin'; Folder='Admin'; Binary='xmqr-admin.exe'; Service='xmqr-admin' }
)
$roots = @{}; $executables = @{}; $approvedConfigHashes = @{}
$programData = Join-Path ([Environment]::GetFolderPath([Environment+SpecialFolder]::CommonApplicationData)) 'XMQR'
foreach ($definition in $definitions) {
    $kind = $definition.Kind
    $expectedExe = Join-Path ([Environment]::GetFolderPath([Environment+SpecialFolder]::ProgramFiles)) ("XMQR/" + $definition.Folder + '/' + $definition.Binary)
    $executables[$kind] = Assert-LocalPath $expectedExe
    if (-not $PrepareOnly) {
        $registeredExe = Machine-Value ('SOFTWARE\XMQR\Components\' + $definition.Id) 'Executable'
        $root = Assert-LocalPath (Join-Path $programData $definition.Id)
        $config = Assert-LocalPath (Machine-Value ('SOFTWARE\XMQR\Components\' + $definition.Id) 'ConfigFile')
        if (-not [string]::Equals([IO.Path]::GetFullPath($registeredExe), $expectedExe, [StringComparison]::OrdinalIgnoreCase) -or
            -not [string]::Equals([IO.Path]::GetFullPath($config), (Join-Path $root ($kind + '.toml')), [StringComparison]::OrdinalIgnoreCase)) { throw 'Instalacao fora dos caminhos dedicados padrao recusada.' }
        $approvedHash = Hash $config
        if ($approvedHash -ne (Hash (Join-Path $repo ("packaging/windows/" + $kind + '.toml')))) { throw "Configuracao personalizada de $kind preservada; inicializador nao aplicavel." }
        $approvedConfigHashes[$kind] = $approvedHash
        $service = Get-CimInstance Win32_Service -Filter ("Name='" + $definition.Service + "'")
        $expectedCommand = '"' + $expectedExe + '" --windows-service ' + $definition.Service + ' "' + (Join-Path $root 'logs\.') + '" --config "' + $config + '"'
        if ($null -eq $service -or $service.State -ne 'Stopped' -or $service.StartName -ne 'NT AUTHORITY\LocalService' -or
            -not [string]::Equals($service.PathName, $expectedCommand, [StringComparison]::OrdinalIgnoreCase)) {
            throw "Servico $kind deve estar parado, na conta/caminho esperados."
        }
        foreach ($folder in @('certificates','state','logs')) { $null = Assert-LocalPath (Join-Path $root $folder) }
        $roots[$kind] = $root
    }
}
$targets = @(
    @{ Kind='broker'; Relative='certificates\ca.crt'; Source='ca.crt' },
    @{ Kind='broker'; Relative='certificates\server.crt'; Source='server.crt' },
    @{ Kind='broker'; Relative='certificates\server.key'; Source='server.key' },
    @{ Kind='broker'; Relative='users.toml'; Source='users.toml' },
    @{ Kind='broker'; Relative='acl.toml'; Source='acl.toml' },
    @{ Kind='client'; Relative='certificates\ca.crt'; Source='ca.crt' },
    @{ Kind='client'; Relative='certificates\client.crt'; Source='client.crt' },
    @{ Kind='client'; Relative='certificates\client.key'; Source='client.key' },
    @{ Kind='client'; Relative='certificates\password'; Source='password' },
    @{ Kind='client'; Relative='state\messages.ndjson'; Source='empty-output' },
    @{ Kind='admin'; Relative='state\token'; Source='admin-token' }
)
if ($PrepareOnly) {
    if (-not $OutputDirectory) { throw 'PrepareOnly exige OutputDirectory novo.' }
    $stage = Assert-LocalPath $OutputDirectory $false
    New-PrivateDirectory $stage
    foreach ($definition in $definitions) {
        $roots[$definition.Kind] = Join-Path $stage $definition.Id
        New-PrivateDirectory $roots[$definition.Kind]
        foreach ($folder in @('certificates','state','logs')) { New-PrivateDirectory (Join-Path $roots[$definition.Kind] $folder) }
    }
} else {
    foreach ($path in @((Join-Path $roots.broker 'certificates'),(Join-Path $roots.client 'certificates'),(Join-Path $roots.client 'state'),(Join-Path $roots.admin 'state'))) {
        if (@(Get-ChildItem -LiteralPath $path -Force).Count -ne 0) { throw 'Diretorio de credenciais/estado nao vazio preservado; inicializador nao aplicavel.' }
    }
    foreach ($target in $targets) {
        if (Test-Path -LiteralPath (Join-Path $roots[$target.Kind] $target.Relative)) { throw 'Credencial/saida existente preservada; inicializador nao sobrescreve.' }
    }
    if (Test-Path -LiteralPath (Join-Path $roots.admin 'state\users.json')) { throw 'Contas web existentes preservadas; requer configuracao manual.' }
    $container = Join-Path $programData 'bootstrap'
    if (-not (Test-Path -LiteralPath $container)) { New-PrivateDirectory $container }
    else {
        $null = Assert-LocalPath $container
        $acl = Get-Acl -LiteralPath $container
        $bootstrapOwner = $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value
        if ($bootstrapOwner -notin @($system.Value,$admins.Value)) { throw 'Diretorio bootstrap existente tem proprietario inesperado.' }
        $bootstrapExpected = [Security.AccessControl.DirectorySecurity]::new()
        $bootstrapExpected.SetSecurityDescriptorSddlForm("O:${bootstrapOwner}D:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)")
        if (-not (Test-XmqrPrivateAcl -Actual $acl -Expected $bootstrapExpected)) { throw 'Diretorio bootstrap existente nao e privado para administradores.' }
    }
    $stage = Join-Path $container ([Guid]::NewGuid().ToString('N'))
    New-PrivateDirectory $stage
}
$crypto = Join-Path $stage 'credentials'
New-PrivateDirectory $crypto
$null = New-XmqrLocalCredentials -StagingDirectory $crypto -HashExecutable $helper
Write-NewText (Join-Path $crypto 'empty-output') ''
& $executables.admin token-init --file (Join-Path $crypto 'admin-token') | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Inicializacao privada de token falhou; nenhum servico foi iniciado.' }
Set-Private (Join-Path $crypto 'admin-token') $false
$clientRoot = $roots.client
$arguments = @('sub','--host','127.0.0.1','--port',"$MqttPort",'--username','xmqr-local',
    '--ca',(Join-Path $clientRoot 'certificates\ca.crt'),'--cert',(Join-Path $clientRoot 'certificates\client.crt'),
    '--key',(Join-Path $clientRoot 'certificates\client.key'),'--password-file',(Join-Path $clientRoot 'certificates\password'),
    '--output','jsonl','--topic','xmqr/local/test','--qos','1','--protocol-version','3.1.1',
    '--client-id','xmqr-client-default','--clean-session','false','--reconnect-attempts','10')
$tomlArguments = ($arguments | ForEach-Object { "'$_'" }) -join ', '
$clientConfig = "version = 1`narguments = [$tomlArguments]`noutput_file = '$(Join-Path $clientRoot 'state\messages.ndjson')'`noutput_max_bytes = 8388608`n"
Write-NewText (Join-Path $crypto 'client.toml') $clientConfig
$appliedClientHash = Hash (Join-Path $crypto 'client.toml')
if ($PrepareOnly) {
    $brokerConfig = "version=1`n[broker]`nmode='secure-mtls'`nbind='127.0.0.1:$MqttPort'`nstate_dir='state'`n[tls]`nserver_cert='certificates/server.crt'`nserver_key='certificates/server.key'`nclient_ca='certificates/ca.crt'`n[security]`nusers_file='users.toml'`nacl_file='acl.toml'`n[monitor]`nenabled=true`nbind='127.0.0.1:$MonitorPort'`n"
    Write-NewText (Join-Path $roots.broker 'broker.toml') $brokerConfig
    Write-NewText (Join-Path $roots.admin 'admin.toml') "version=1`nbind='127.0.0.1:$AdminPort'`nmonitor='127.0.0.1:$MonitorPort'`ntoken_file='state/token'`nusers_file='state/users.json'`n"
}
$created = @(); $aclBackups = @{}; $clientChanged = $false; $committed = $false
$clientPath = Join-Path $roots.client 'client.toml'
$backup = Join-Path $stage 'client.toml.before'
$oldClientAcl = $null
try {
    if (-not $PrepareOnly) {
        foreach ($definition in $definitions) {
            if ((Get-Service -Name $definition.Service).Status -ne 'Stopped') { throw 'Servico mudou de estado durante a preparacao; nenhuma aplicacao deve ocorrer.' }
        }
        $oldClientAcl = Get-Acl -LiteralPath $clientPath
        if ((Hash $clientPath) -ne $approvedConfigHashes.client) { throw 'Configuracao Client mudou apos o preflight; arquivo preservado.' }
        [IO.File]::Copy($clientPath, $backup, $false)
        if ((Hash $backup) -ne $approvedConfigHashes.client) { throw 'Backup diverge do modelo aprovado; configuracao preservada.' }
        foreach ($path in @((Join-Path $roots.broker 'certificates'),(Join-Path $roots.client 'certificates'),(Join-Path $roots.client 'state'),(Join-Path $roots.admin 'state'))) {
            $aclBackups[$path] = Get-Acl -LiteralPath $path
            Set-Private $path $true ($path.EndsWith('\state')) $true
        }
    }
    foreach ($target in $targets) {
        $destination = Assert-LocalPath (Join-Path $roots[$target.Kind] $target.Relative) $false
        $source = Join-Path $crypto $target.Source
        [IO.File]::Copy($source, $destination, $false)
        $created += @{ Path=$destination; Hash=(Hash $source) }
        Set-Private $destination $false ($target.Relative -eq 'state\messages.ndjson') $true
    }
    if ($PrepareOnly) { [IO.File]::Copy((Join-Path $crypto 'client.toml'),$clientPath,$false) }
    else {
        # Replace only the exact model verified again immediately before commit.
        Replace-XmqrClientConfig -Source (Join-Path $crypto 'client.toml') -Destination $clientPath -BackupPath (Join-Path $stage 'client.toml.replaced') -ExpectedHash $approvedConfigHashes.client
        $clientChanged = $true
    }
    Set-Private $clientPath $false $false $true
    $committed = $true
} catch {
    if (-not $committed) {
        $rollbackIncomplete = $false
        try {
            if ($clientChanged -and (Hash $clientPath) -eq $appliedClientHash) {
                [IO.File]::Copy($backup,$clientPath,$true)
                [IO.FileSystemAclExtensions]::SetAccessControl([IO.FileInfo]::new($clientPath), $oldClientAcl)
            }
        } catch { $rollbackIncomplete = $true }
        foreach ($entry in $created) {
            try { if ([IO.File]::Exists($entry.Path) -and (Hash $entry.Path) -eq $entry.Hash) { [IO.File]::Delete($entry.Path) } }
            catch { $rollbackIncomplete = $true }
        }
        foreach ($path in $aclBackups.Keys) {
            try { [IO.FileSystemAclExtensions]::SetAccessControl([IO.DirectoryInfo]::new($path), $aclBackups[$path]) }
            catch { $rollbackIncomplete = $true }
        }
        if ($rollbackIncomplete) { Write-Warning 'Reversao parcial: preserve o staging privado e colete diagnostico antes de repetir.' }
    }
    throw
}
$states = @($definitions | ForEach-Object { @{ Component=$_.Kind; State=$(if($StartServices){'Pending'}else{'NotRequested'}) } })
$startupError = $null
try {
    if ($StartServices) {
        foreach ($definition in $definitions) {
            $row = $states | Where-Object { $_.Component -eq $definition.Kind }
            $row.State = 'Failed'
            Start-Service -Name $definition.Service
            $service = Get-Service -Name $definition.Service
            $service.WaitForStatus([ServiceProcess.ServiceControllerStatus]::Running,[TimeSpan]::FromSeconds(20))
            Start-Sleep -Seconds 2
            $service.Refresh()
            if ($service.Status -ne 'Running') { throw "Servico $($definition.Kind) encerrou; arquivos preservados para diagnostico." }
            $row.State = 'Running'
        }
    }
} catch { $startupError = $_ }
$report = [ordered]@{ Schema=1; CreatedUtc=[DateTime]::UtcNow.ToString('o'); Mode= $(if($PrepareOnly){'PrepareOnly'}else{'InstalledLocal'}); FilesPrepared=$true; StartRequested=[bool]$StartServices; StartupSucceeded=($StartServices -and $null -eq $startupError); Services=$states; AdminUrl="http://127.0.0.1:$AdminPort/"; Topic='xmqr/local/test' }
$reportPath = if ($PrepareOnly) { Join-Path $stage 'setup-result.json' } else { Join-Path $repo 'target/p247-setup-result.json' }
$null = New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($reportPath)) -Force
$report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $reportPath -Encoding utf8
Write-Output "Configuracao local preparada. Resultado sem segredos: $reportPath"
$states | ForEach-Object { Write-Output ($_.Component + ': ' + $_.State) }
if ($null -ne $startupError) {
    Write-Warning 'Inicio incompleto. Colete diagnostico; nao repita provisionamento nem reinstale.'
    throw $startupError
}
Write-Output "Painel Admin: http://127.0.0.1:$AdminPort/ (criar conta web com token privado pelo bootstrap)."
