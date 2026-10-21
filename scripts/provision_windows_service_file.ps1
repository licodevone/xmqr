# SPDX-License-Identifier: MIT
# Apply a narrowly scoped service-readable DACL to one existing installed file.
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'Medium')]
param(
    [Parameter(Mandatory)]
    [ValidateSet('client', 'admin')]
    [string] $Component,
    [Parameter(Mandatory)]
    [string] $RelativePath,
    [switch] $Writable,
    [switch] $ParentWritable
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

if (-not [Environment]::Is64BitProcess) { throw 'Use 64-bit PowerShell 7.' }
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run from an elevated PowerShell session.'
}

function Get-MachineRegistryValue([string] $Key, [string] $Name) {
    $base = [Microsoft.Win32.RegistryKey]::OpenBaseKey(
        [Microsoft.Win32.RegistryHive]::LocalMachine,
        [Microsoft.Win32.RegistryView]::Registry64)
    try {
        $entry = $base.OpenSubKey($Key, $false)
        if ($null -eq $entry) { throw "Installed component metadata missing: $Key" }
        try { $value = $entry.GetValue($Name, $null, [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames) }
        finally { $entry.Dispose() }
    } finally { $base.Dispose() }
    if ($value -isnot [string] -or [string]::IsNullOrWhiteSpace($value) -or $value.Contains('"')) {
        throw "Invalid installed component metadata: $Key\$Name"
    }
    return $value
}

function Assert-NoReparseAncestors([string] $Path) {
    $full = [IO.Path]::GetFullPath($Path)
    $driveRoot = [IO.Path]::GetPathRoot($full)
    if ($full -notmatch '^[A-Za-z]:\\') { throw 'Only local drive paths are accepted.' }
    $cursor = $driveRoot
    $remainder = $full.Substring($driveRoot.Length)
    foreach ($part in $remainder.Split('\', [StringSplitOptions]::RemoveEmptyEntries)) {
        $cursor = Join-Path $cursor $part
        if (-not (Test-Path -LiteralPath $cursor)) { throw "Missing path ancestor: $cursor" }
        $item = Get-Item -LiteralPath $cursor -Force
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "Reparse points are not accepted in the target path: $cursor"
        }
    }
    return $full
}

function New-PrivateAcl([bool] $AllowLocalServiceWrite, [bool] $IsDirectory) {
    $security = if ($IsDirectory) { [Security.AccessControl.DirectorySecurity]::new() } else { [Security.AccessControl.FileSecurity]::new() }
    $security.SetAccessRuleProtection($true, $false)
    $systemSid = [Security.Principal.SecurityIdentifier]::new('S-1-5-18')
    $adminsSid = [Security.Principal.SecurityIdentifier]::new('S-1-5-32-544')
    $localServiceSid = [Security.Principal.SecurityIdentifier]::new('S-1-5-19')
    $inheritance = if ($IsDirectory) { [Security.AccessControl.InheritanceFlags]::ContainerInherit -bor [Security.AccessControl.InheritanceFlags]::ObjectInherit } else { [Security.AccessControl.InheritanceFlags]::None }
    $propagation = [Security.AccessControl.PropagationFlags]::None
    $full = [Security.AccessControl.FileSystemRights]::FullControl
    $localRights = if ($AllowLocalServiceWrite) { [Security.AccessControl.FileSystemRights]::Modify } else { [Security.AccessControl.FileSystemRights]::ReadAndExecute }
    foreach ($entry in @(@($systemSid, $full), @($adminsSid, $full), @($localServiceSid, $localRights))) {
        $rule = [Security.AccessControl.FileSystemAccessRule]::new(
            $entry[0], $entry[1], $inheritance, $propagation,
            [Security.AccessControl.AccessControlType]::Allow)
        $security.AddAccessRule($rule)
    }
    $security.SetOwner($adminsSid)
    return $security
}

$componentId = if ($Component -eq 'client') { 'client-default' } else { 'admin' }
$componentKey = "SOFTWARE\XMQR\Components\$componentId"
$installKey = "SOFTWARE\XMQR\Install\$componentId"
$configuredDataRoot = Get-MachineRegistryValue $installKey 'DataDirectory'
$expectedDataRoot = Join-Path (Join-Path (Join-Path ([Environment]::GetFolderPath([Environment+SpecialFolder]::CommonApplicationData)) 'XMQR') $componentId) ''
$dataRoot = [IO.Path]::GetFullPath($configuredDataRoot).TrimEnd('\') + '\'
$expectedRoot = [IO.Path]::GetFullPath($expectedDataRoot).TrimEnd('\') + '\'
if (-not [string]::Equals($dataRoot, $expectedRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Only the dedicated default ProgramData component directory is accepted.'
}
$registeredConfig = [IO.Path]::GetFullPath((Get-MachineRegistryValue $componentKey 'ConfigFile'))
$expectedConfig = [IO.Path]::GetFullPath((Join-Path $dataRoot "$Component.toml"))
if (-not [string]::Equals($registeredConfig, $expectedConfig, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'The registered service config is outside the dedicated data directory.'
}

if ([string]::IsNullOrWhiteSpace($RelativePath) -or [IO.Path]::IsPathRooted($RelativePath) -or $RelativePath -match '[:/]' -or $RelativePath.StartsWith('\')) {
    throw 'RelativePath must be a relative Windows path using backslash separators.'
}
$parts = $RelativePath.Split('\', [StringSplitOptions]::None)
if ($parts.Count -eq 0 -or @($parts | Where-Object {
    $_ -in @('', '.', '..') -or $_ -match '[ .]$' -or $_ -match '[<>"|?*]' -or
        $_ -match '^(?i:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)'
}).Count -gt 0) { throw 'RelativePath contains a traversal, stream, device, or invalid path component.' }
$candidate = [IO.Path]::GetFullPath((Join-Path $dataRoot $RelativePath))
if (-not $candidate.StartsWith($dataRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Target escapes the dedicated component directory.'
}
$parent = [IO.Path]::GetDirectoryName($candidate)
if (-not (Test-Path -LiteralPath $candidate -PathType Leaf) -or -not (Test-Path -LiteralPath $parent -PathType Container)) {
    throw 'The target file and its immediate parent must already exist.'
}
$null = Assert-NoReparseAncestors $dataRoot
$null = Assert-NoReparseAncestors $candidate
$fileItem = Get-Item -LiteralPath $candidate -Force
if (($fileItem.Attributes -band [IO.FileAttributes]::Directory) -ne 0 -or
    ($fileItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
    throw 'The target must be a regular file, not a directory or reparse point.'
}

$fileRightsWrite = [bool]$Writable
$parentRightsWrite = [bool]$ParentWritable
if ($PSCmdlet.ShouldProcess($RelativePath, "Set protected SYSTEM/Administrators/LocalService ACL (file-write=$fileRightsWrite, parent-write=$parentRightsWrite)")) {
    $fileAcl = New-PrivateAcl $fileRightsWrite $false
    Set-Acl -LiteralPath $candidate -AclObject $fileAcl
    $parentAcl = New-PrivateAcl $parentRightsWrite $true
    Set-Acl -LiteralPath $parent -AclObject $parentAcl
    foreach ($path in @($candidate, $parent)) {
        $actual = Get-Acl -LiteralPath $path
        $ownerSid = $actual.GetOwner([Security.Principal.SecurityIdentifier]).Value
        if (-not $actual.AreAccessRulesProtected -or $ownerSid -ne 'S-1-5-32-544') {
            throw "Protected ACL or Administrators ownership verification failed: $path"
        }
        $rules = @($actual.GetAccessRules($true, $false, [Security.Principal.SecurityIdentifier]))
        $allowed = @('S-1-5-18', 'S-1-5-32-544', 'S-1-5-19')
        $identities = @($rules | ForEach-Object { $_.IdentityReference.Value } | Sort-Object -Unique)
        if ($rules.Count -ne 3 -or $identities.Count -ne 3 -or
            @($rules | Where-Object { $_.IdentityReference.Value -notin $allowed }).Count -ne 0) {
            throw "Unexpected access rule remains: $path"
        }
        $isDirectory = [string]::Equals($path, $parent, [StringComparison]::OrdinalIgnoreCase)
        foreach ($rule in $rules) {
            $sid = $rule.IdentityReference.Value
            $expectedRights = if ($sid -eq 'S-1-5-19') {
                if ($isDirectory) { if ($parentRightsWrite) { [Security.AccessControl.FileSystemRights]::Modify } else { [Security.AccessControl.FileSystemRights]::ReadAndExecute } }
                else { if ($fileRightsWrite) { [Security.AccessControl.FileSystemRights]::Modify } else { [Security.AccessControl.FileSystemRights]::ReadAndExecute } }
            } else { [Security.AccessControl.FileSystemRights]::FullControl }
            $expectedInheritance = if ($isDirectory) { [Security.AccessControl.InheritanceFlags]::ContainerInherit -bor [Security.AccessControl.InheritanceFlags]::ObjectInherit } else { [Security.AccessControl.InheritanceFlags]::None }
            if ($rule.AccessControlType -ne [Security.AccessControl.AccessControlType]::Allow -or
                $rule.FileSystemRights -ne $expectedRights -or $rule.InheritanceFlags -ne $expectedInheritance -or
                $rule.PropagationFlags -ne [Security.AccessControl.PropagationFlags]::None) {
                throw "Unexpected access rule values: $path"
            }
        }
    }
    Write-Output "Applied and verified protected service ACL for $Component\$RelativePath."
}
