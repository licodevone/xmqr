# SPDX-License-Identifier: MIT
# Explicit operator action only. The build process never executes this script.
[CmdletBinding(DefaultParameterSetName = 'Components')]
param(
    [Parameter(Mandatory, ParameterSetName = 'Components')]
    [ValidateSet('broker', 'client', 'admin')]
    [string[]] $Components,
    [Parameter(Mandatory, ParameterSetName = 'Manager')]
    [switch] $ManagerOnly,
    [string] $PackageDirectory = $PSScriptRoot
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$manifestPath = Join-Path $PackageDirectory 'manifest.json'
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ($manifest.schema -ne 1 -or $manifest.target -ne 'x86_64-pc-windows-msvc') {
    throw 'Unsupported package manifest.'
}
Write-Warning 'Experimental native packages: storage/ACL and installer acceptance are still pending. Services are not started by installation.'
$selected = if ($ManagerOnly) { @('manager') } else { @('manager') + @($Components | Select-Object -Unique) }
$verified = @()
foreach ($kind in $selected) {
    $matches = @($manifest.packages | Where-Object { $_.kind -eq $kind })
    if ($matches.Count -ne 1) { throw "Exactly one $kind package is required." }
    $package = $matches[0]
    if ($package.file -notmatch '^xmqr-[a-z]+-[0-9]+\.[0-9]+\.[0-9]+-windows-x64-experimental\.msi$') {
        throw 'Invalid package file name.'
    }
    $path = [IO.Path]::GetFullPath((Join-Path $PackageDirectory $package.file))
    if ($path.Contains('"')) { throw 'Invalid package path.' }
    $hash = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
    if ($hash -ine $package.sha256) { throw "Checksum mismatch: $($package.file)" }
    $verified += $path
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
foreach ($path in $verified) {
    $arguments = '/i "' + $path + '" /passive /norestart'
    $process = Start-Process -FilePath $installer -ArgumentList $arguments -Verb RunAs -Wait -PassThru -WindowStyle Hidden
    if ($process.ExitCode -notin @(0, 3010)) { throw "MSI failed ($($process.ExitCode)); later packages were not installed." }
}
# This process normally runs as the interactive user. Do not elevate the tray.
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    $manager = Get-MachinePath 'SOFTWARE\XMQR\Manager' 'Executable'
    if (Test-Path -LiteralPath $manager -PathType Leaf) {
        Start-Process -FilePath $manager -WindowStyle Hidden
    }
} else {
    Write-Output 'The tray starts at the next normal user login. Close this elevated session before launching it manually.'
}
Write-Output 'Installation completed. Provision configuration before starting services. Data is preserved on uninstall.'
