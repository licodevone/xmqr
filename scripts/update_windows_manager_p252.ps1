#requires -Version 7.5
# SPDX-License-Identifier: MIT
# Operator-run P252 update. Close Manager normally before running this script.
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Assert-XmqrP252Path([string] $Path, [bool] $Directory = $false) {
    if (-not [IO.Path]::IsPathFullyQualified($Path) -or $Path -notmatch '^[A-Za-z]:\\' -or $Path.Substring(2).Contains(':')) { throw 'Caminho local absoluto sem streams necessario.' }
    $item = Get-Item -LiteralPath $Path -Force
    if ($item.PSIsContainer -ne $Directory) { throw 'Tipo de arquivo/diretorio inesperado.' }
    $cursor = $item
    while ($null -ne $cursor) {
        if (($cursor.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Reparse point recusado.' }
        $cursor = if ($cursor -is [IO.FileInfo]) { $cursor.Directory } else { $cursor.Parent }
    }
    return $item.FullName
}
function Get-XmqrP252Hash([string] $Path) { return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }
function Assert-XmqrP252Administrator {
    if (-not $IsWindows -or -not [Environment]::Is64BitProcess) { throw 'Use PowerShell 7.5+ Windows 64-bit como administrador.' }
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    try {
        if (-not ([Security.Principal.WindowsPrincipal]::new($identity)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Execute em PowerShell como administrador.' }
    } finally { $identity.Dispose() }
}
function Get-XmqrP252MachineValue([string] $Key, [string] $Name) {
    $base = [Microsoft.Win32.RegistryKey]::OpenBaseKey([Microsoft.Win32.RegistryHive]::LocalMachine, [Microsoft.Win32.RegistryView]::Registry64)
    try {
        $entry = $base.OpenSubKey($Key, $false)
        if ($null -eq $entry) { throw 'Registro do componente instalado ausente.' }
        try { $value = $entry.GetValue($Name, $null, [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames) }
        finally { $entry.Dispose() }
    } finally { $base.Dispose() }
    if ($value -isnot [string] -or [string]::IsNullOrWhiteSpace($value)) { throw 'Registro do componente instalado invalido.' }
    return $value
}
function Get-XmqrP252Candidate([string] $Component, [string] $FileName) {
    $folder = Join-Path (Split-Path $PSScriptRoot -Parent) 'dist/windows/p252-manager-console'
    if (-not (Test-Path -LiteralPath (Join-Path $folder $FileName)) -and -not (Test-Path -LiteralPath (Join-Path $folder 'manifest.json'))) { $folder = $PSScriptRoot }
    $null = Assert-XmqrP252Path $folder $true
    $source = Assert-XmqrP252Path (Join-Path $folder $FileName)
    $manifestPath = Assert-XmqrP252Path (Join-Path $folder 'manifest.json')
    if ((Get-Item -LiteralPath $manifestPath).Length -gt 16384) { throw 'Manifesto excede limite.' }
    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    if ($manifest.schema -ne 1 -or $manifest.release -cne 'P252') { throw 'Manifesto P252 invalido.' }
    $artifact = $manifest.$Component
    if ($artifact.file -cne $FileName -or $artifact.sha256 -isnot [string] -or $artifact.sha256 -cnotmatch '^[a-f0-9]{64}$') { throw 'Identidade/hash do artefato invalido.' }
    if ((Get-XmqrP252Hash $source) -cne $artifact.sha256) { throw 'SHA-256 diverge do manifesto; nada alterado.' }
    return @{ Path=$source; Hash=$artifact.sha256 }
}
function Assert-XmqrP252BinaryAcl([string] $Path) {
    $acl = Get-Acl -LiteralPath $Path
    if ($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -notin @('S-1-5-18','S-1-5-32-544')) { throw 'Proprietario do binario/diretorio instalado inesperado.' }
    $writeMask = [long]0x50000000 -bor [long][Security.AccessControl.FileSystemRights]::Write -bor [long][Security.AccessControl.FileSystemRights]::Delete -bor [long][Security.AccessControl.FileSystemRights]::ChangePermissions -bor [long][Security.AccessControl.FileSystemRights]::TakeOwnership -bor [long][Security.AccessControl.FileSystemRights]::DeleteSubdirectoriesAndFiles
    $trustedWriters = @('S-1-5-18','S-1-5-32-544','S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464') # Windows TrustedInstaller, only Program Files binaries.
    foreach ($rule in $acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])) {
        $mask = [long][int]$rule.FileSystemRights -band [long]4294967295
        if ($rule.AccessControlType -ne [Security.AccessControl.AccessControlType]::Allow -or ($writeMask -band $mask) -eq 0 -or $rule.IdentityReference.Value -in $trustedWriters) { continue }
        if ($rule.IdentityReference.Value -eq 'S-1-3-0' -and $rule.PropagationFlags -eq [Security.AccessControl.PropagationFlags]::InheritOnly -and $rule.InheritanceFlags -eq ([Security.AccessControl.InheritanceFlags]::ObjectInherit -bor [Security.AccessControl.InheritanceFlags]::ContainerInherit) -and (Get-Item -LiteralPath $Path).PSIsContainer) { continue }
        throw 'Binario/diretorio gravavel por identidade nao autorizada.'
    }
}
function Copy-XmqrP252NewFile([string] $Source, [string] $Destination) {
    $inputStream = [IO.File]::Open($Source,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
    try {
        $outputStream = [IO.File]::Open($Destination,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
        try { $inputStream.CopyTo($outputStream); $outputStream.Flush($true) } finally { $outputStream.Dispose() }
    } finally { $inputStream.Dispose() }
}
function Replace-XmqrP252File {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string] $Source,
        [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string] $Destination,
        [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string] $BackupPath,
        [Parameter(Mandatory)][ValidatePattern('^[a-f0-9]{64}$')][string] $SourceHash,
        [Parameter(Mandatory)][ValidatePattern('^[a-f0-9]{64}$')][string] $DestinationHash
    )
    if (Test-Path -LiteralPath $BackupPath) { throw 'Backup existente preservado.' }
    if ((Get-XmqrP252Hash $Source) -cne $SourceHash -or (Get-XmqrP252Hash $Destination) -cne $DestinationHash) { throw 'Arquivo mudou; substituicao recusada.' }
    [IO.File]::Replace($Source,$Destination,$BackupPath)
    if ((Get-XmqrP252Hash $Destination) -cne $SourceHash -or (Get-XmqrP252Hash $BackupPath) -cne $DestinationHash) { throw 'Hash da substituicao/backup nao confirmado.' }
}
function Assert-XmqrP252ManagerClosed([string] $Installed) {
    if (@(Get-Process -Name 'xmqr-manager' -ErrorAction SilentlyContinue).Count -ne 0) { throw 'Feche o XMQR Manager normalmente pelo menu Sair antes de atualizar; nenhum processo foi encerrado.' }
    $stream = [IO.File]::Open($Installed,[IO.FileMode]::Open,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
    $stream.Dispose()
}

# Main: no service operations and no automatic elevated GUI launch.
Assert-XmqrP252Administrator
$installed = Assert-XmqrP252Path 'C:\Program Files\XMQR\Manager\xmqr-manager.exe'
$folder = Assert-XmqrP252Path 'C:\Program Files\XMQR\Manager' $true
if (-not [string]::Equals((Get-XmqrP252MachineValue 'SOFTWARE\XMQR\Manager' 'Executable'),$installed,[StringComparison]::OrdinalIgnoreCase)) { throw 'Registro do Manager diverge do caminho padrao.' }
Assert-XmqrP252BinaryAcl $folder
Assert-XmqrP252BinaryAcl $installed
$candidate = Get-XmqrP252Candidate 'manager' 'xmqr-manager.exe'
Assert-XmqrP252ManagerClosed $installed
$oldHash = Get-XmqrP252Hash $installed
$backupFolder = Join-Path $folder ('p252-backup-' + [Guid]::NewGuid().ToString('N'))
$backup = Join-Path $backupFolder 'xmqr-manager.previous.exe'
$attempted = $false
try {
    if (Test-Path -LiteralPath $backupFolder) { throw 'Diretorio de backup existente preservado.' }
    $null = [IO.Directory]::CreateDirectory($backupFolder)
    $null = Assert-XmqrP252Path $backupFolder $true
    $stage = Join-Path $backupFolder 'xmqr-manager.new.exe'
    Copy-XmqrP252NewFile $candidate.Path $stage
    Assert-XmqrP252ManagerClosed $installed
    $attempted = $true
    Replace-XmqrP252File $stage $installed $backup $candidate.Hash $oldHash
    Assert-XmqrP252BinaryAcl $installed
    Write-Output "Manager atualizado. Backup: $backup"
    Write-Output 'Feche esta janela administrativa e abra XMQR Manager pelo menu Iniciar como usuario normal.'
} catch {
    $failure = $_
    try {
        $current = Get-XmqrP252Hash $installed
        if ($attempted -and $current -ceq $candidate.Hash) {
            Assert-XmqrP252ManagerClosed $installed
            Replace-XmqrP252File $backup $installed (Join-Path $backupFolder 'xmqr-manager.failed.exe') $oldHash $candidate.Hash
        } elseif ($current -cne $oldHash) { throw 'Edicao inesperada preservada; rollback recusado.' }
        Write-Warning 'Atualizacao interrompida; binario anterior confirmado. Manager permanece fechado.'
    } catch { Write-Warning "Recuperacao automatica incompleta; preserve o backup: $backupFolder" }
    throw $failure
}
