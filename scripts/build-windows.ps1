#requires -Version 7.0
# SPDX-License-Identifier: MIT
[CmdletBinding()]
param(
    [ValidateSet('broker', 'client', 'admin')]
    [string[]] $Components = @('broker', 'client', 'admin'),
    [switch] $ManagerOnly,
    [string] $OutputDirectory,
    [ValidateSet('x86_64-pc-windows-msvc')]
    [string] $Target = 'x86_64-pc-windows-msvc'
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$repoRoot = Split-Path $PSScriptRoot -Parent
$groupRoot = Split-Path $repoRoot -Parent
if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path $repoRoot ('dist/windows/candidate-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
}
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $OutputDirectory) {
    throw 'Choose a new output directory; existing artifacts are never overwritten.'
}
foreach ($command in @('cargo', 'wix', 'git', 'python')) { $null = Get-Command $command -ErrorAction Stop }

function Invoke-Checked([string] $Command, [string[]] $Arguments) {
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Command failed with exit code $LASTEXITCODE" }
}

function Get-PackageVersion([string] $Manifest) {
    $text = Get-Content -LiteralPath $Manifest -Raw
    $package = [regex]::Match($text, '(?ms)^\[package\]\s*(.*?)(?=^\[|\z)')
    $version = [regex]::Match($package.Groups[1].Value, '(?m)^version\s*=\s*"([0-9]+\.[0-9]+\.[0-9]+)"')
    if (-not $version.Success) { throw "Cannot read package version: $Manifest" }
    return $version.Groups[1].Value
}

$definitions = @{
    broker = @{
        Root = $repoRoot; Binary = 'mqtt-broker'; Name = 'XMQR Broker'; Folder = 'Broker'
        Id = 'broker'; Service = 'xmqr-broker'; Upgrade = 'B2DE9967-4A95-4873-87C6-DF2B9F1C07F1'
    }
    client = @{
        Root = (Join-Path $groupRoot 'xmqr-client'); Binary = 'mqtt-client'; Name = 'XMQR Client'; Folder = 'Client'
        Id = 'client-default'; Service = 'xmqr-client-default'; Upgrade = 'F82944CA-6F7B-42EB-B331-AF399B193574'
    }
    admin = @{
        Root = (Join-Path $groupRoot 'xmqr-admin'); Binary = 'xmqr-admin'; Name = 'XMQR Admin'; Folder = 'Admin'
        Id = 'admin'; Service = 'xmqr-admin'; Upgrade = '02128577-D65D-4B3F-963C-617424FBCB20'
    }
    manager = @{
        Root = (Join-Path $repoRoot 'tools/windows-manager'); Binary = 'xmqr-manager'; Name = 'XMQR Manager'; Folder = 'Manager'
    }
}
if ($ManagerOnly -and $PSBoundParameters.ContainsKey('Components')) {
    throw 'Use either -ManagerOnly or -Components, not both.'
}
$selected = if ($ManagerOnly) { @('manager') } else { @('manager') + @($Components | Select-Object -Unique) }
$built = @{}

# Always build current locked source first; never silently package an old .exe.
foreach ($kind in $selected) {
    $definition = $definitions[$kind]
    $manifest = if ($kind -eq 'manager') {
        Join-Path $definition.Root 'Cargo.toml'
    } else {
        Join-Path $definition.Root 'packaging/windows-service/Cargo.toml'
    }
    $lock = Join-Path (Split-Path $manifest -Parent) 'Cargo.lock'
    if (-not (Test-Path -LiteralPath $lock -PathType Leaf)) {
        throw "Missing service/manager lockfile. Resolve dependencies online first: cargo generate-lockfile --manifest-path `"$manifest`". No old root binary will be packaged."
    }
    $targetDirectory = Join-Path $definition.Root 'target/windows-msi'
    Invoke-Checked 'cargo' @('build', '--locked', '--release', '--target', $Target,
        '--manifest-path', $manifest, '--target-dir', $targetDirectory, '--bin', $definition.Binary)
    $binary = Join-Path $targetDirectory "$Target/release/$($definition.Binary).exe"
    if (-not (Test-Path -LiteralPath $binary -PathType Leaf)) { throw "Build did not produce $binary" }
    if ($kind -ne 'manager') {
        $probe = & $binary '--windows-service-capabilities'
        if ($LASTEXITCODE -ne 0) { throw "The $kind binary has no service entrypoint; refusing to package it." }
        $capability = $probe | ConvertFrom-Json
        if ($capability.schema -ne 1 -or $capability.component -ne $kind -or
            $capability.service_entrypoint -isnot [bool] -or -not $capability.service_entrypoint) {
            throw "Unexpected service capability marker for $kind."
        }
    }
    $sourceRoot = if ($kind -eq 'manager') { $repoRoot } else { $definition.Root }
    $revision = & git -C $sourceRoot rev-parse HEAD
    if ($LASTEXITCODE -ne 0) { throw 'Cannot determine source revision.' }
    $status = & git -C $sourceRoot status --porcelain
    if ($LASTEXITCODE -ne 0) { throw 'Cannot determine source status.' }
    $built[$kind] = @{
        Binary = $binary; Manifest = $manifest; Version = (Get-PackageVersion (Join-Path $definition.Root 'Cargo.toml')); Revision = "$revision"
        Dirty = [bool]$status; Sha256 = (Get-FileHash -LiteralPath $binary -Algorithm SHA256).Hash.ToLowerInvariant()
    }
}

$null = New-Item -ItemType Directory -Path $OutputDirectory
$packages = @()
foreach ($kind in $selected) {
    $definition = $definitions[$kind]
    $build = $built[$kind]
    $fileName = "xmqr-$kind-$($build.Version)-windows-x64-experimental.msi"
    $msi = Join-Path $OutputDirectory $fileName
    $binaryDirectory = Split-Path $build.Binary -Parent
    $noticesDirectory = Join-Path $OutputDirectory "notices/$kind"
    Invoke-Checked 'python' @((Join-Path $repoRoot 'tools/windows-manager/scripts/collect-licenses.py'),
        '--manifest-path', $build.Manifest, '-o', $noticesDirectory)
    if ($kind -eq 'manager') {
        $wixArguments = @('build', (Join-Path $repoRoot 'packaging/windows/Manager.wxs'),
            (Join-Path $repoRoot 'packaging/windows/InstallerUI.wxs'),
            '-arch', 'x64', '-d', "ProductVersion=$($build.Version)", '-d', "BinaryDir=$binaryDirectory",
            '-d', "NoticesDir=$noticesDirectory", '-out', $msi)
    } else {
        $wixArguments = @('build', (Join-Path $repoRoot 'packaging/windows/Product.wxs'),
            (Join-Path $repoRoot 'packaging/windows/InstallerUI.wxs'), '-arch', 'x64',
            '-d', "ProductName=$($definition.Name)", '-d', "ProductVersion=$($build.Version)",
            '-d', "UpgradeCode=$($definition.Upgrade)", '-d', "ProductFolder=$($definition.Folder)",
            '-d', "BinaryDir=$binaryDirectory", '-d', "ExecutableName=$($definition.Binary).exe",
            '-d', "ComponentId=$($definition.Id)", '-d', "Kind=$kind",
            '-d', "ServiceName=$($definition.Service)", '-d', "ConfigName=$kind.toml",
            '-d', "ConfigSource=$(Join-Path $repoRoot "packaging/windows/$kind.toml")",
            '-d', "NoticesDir=$noticesDirectory", '-out', $msi)
    }
    Invoke-Checked 'wix' $wixArguments
    $packages += [ordered]@{
        kind = $kind; file = $fileName; version = $build.Version
        sha256 = (Get-FileHash -LiteralPath $msi -Algorithm SHA256).Hash.ToLowerInvariant()
        executable_sha256 = $build.Sha256; source_commit = $build.Revision; source_dirty = $build.Dirty
    }
}
$record = [ordered]@{
    schema = 1; target = $Target; experimental = $true; native_acceptance = $false
    built_at_utc = [DateTime]::UtcNow.ToString('o')
    limitations = @(
        'Broker Windows durable storage has passed native persistence and MQTT recovery proof; MSI/SCM acceptance remains pending.',
        'Admin private token and web-user files, bootstrap authentication, and authenticated status have passed native Windows runtime proof; MSI/SCM acceptance remains pending.',
        'Client private password and service-config ACLs plus bounded private JSONL subscriber output have passed native Windows runtime proof; MSI/SCM acceptance remains pending.',
        'MSI installation, effective ACLs, boot, logon, upgrade and rollback require disposable elevated Windows VM validation.'
    )
    packages = $packages
}
$record | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $OutputDirectory 'manifest.json') -Encoding utf8
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'install-windows.ps1') -Destination $OutputDirectory
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'Instalar-XMQR.cmd') -Destination $OutputDirectory
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'diagnose-windows.ps1') -Destination $OutputDirectory
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'provision_windows_service_file.ps1') -Destination $OutputDirectory
Copy-Item -LiteralPath (Join-Path $repoRoot 'packaging/windows/README.md') -Destination $OutputDirectory
Copy-Item -LiteralPath (Join-Path $repoRoot 'packaging/windows/TERMS.pt-BR.txt') -Destination $OutputDirectory
Copy-Item -LiteralPath (Join-Path $repoRoot 'packaging/windows/TERMS.pt-BR.rtf') -Destination $OutputDirectory
$checksums = Get-ChildItem -LiteralPath $OutputDirectory -File -Recurse |
    Where-Object { $_.Extension -ne '.wixpdb' } | Sort-Object FullName | ForEach-Object {
        $relative = [IO.Path]::GetRelativePath($OutputDirectory, $_.FullName).Replace('\', '/')
        "$((Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant())  $relative"
    }
$checksums | Set-Content -LiteralPath (Join-Path $OutputDirectory 'SHA256SUMS.txt') -Encoding ascii
Write-Output "Experimental packages built at $OutputDirectory. No service was installed or started."
