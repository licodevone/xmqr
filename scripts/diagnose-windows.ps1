# SPDX-License-Identifier: MIT
# Read-only inventory. Does not use Win32_Product, start services, or read secrets.
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$items = @()
$base = [Microsoft.Win32.RegistryKey]::OpenBaseKey([Microsoft.Win32.RegistryHive]::LocalMachine, [Microsoft.Win32.RegistryView]::Registry64)
try {
    foreach ($entry in @(
        @{ Id = 'manager'; Key = 'SOFTWARE\XMQR\Manager'; Service = $null },
        @{ Id = 'broker'; Key = 'SOFTWARE\XMQR\Components\broker'; Service = 'xmqr-broker' },
        @{ Id = 'client'; Key = 'SOFTWARE\XMQR\Components\client-default'; Service = 'xmqr-client-default' },
        @{ Id = 'admin'; Key = 'SOFTWARE\XMQR\Components\admin'; Service = 'xmqr-admin' }
    )) {
        $record = [ordered]@{ Component = $entry.Id; Registration = 'UNKNOWN'; ExecutableExists = $null; Service = $entry.Service; ServiceStatus = 'NOT_APPLICABLE' }
        try {
            $key = $base.OpenSubKey($entry.Key, $false)
            if ($null -eq $key) { $record.Registration = 'ABSENT' }
            else {
                try {
                    $record.Registration = 'PRESENT'
                    $path = $key.GetValue('Executable', $null, [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames)
                    $record.ExecutableExists = ($path -is [string] -and (Test-Path -LiteralPath $path -PathType Leaf))
                } finally { $key.Dispose() }
            }
        } catch { $record.Registration = 'QUERY_FAILED' }
        if ($entry.Service) {
            try { $record.ServiceStatus = (Get-Service -Name $entry.Service -ErrorAction Stop).Status.ToString() }
            catch { $record.ServiceStatus = 'QUERY_FAILED_OR_ABSENT' }
        }
        $items += [pscustomobject]$record
    }
} finally { $base.Dispose() }
$programs = [Environment]::GetFolderPath([Environment+SpecialFolder]::CommonPrograms)
$shortcut = Join-Path $programs 'XMQR\XMQR Manager.lnk'
[ordered]@{ Components = @($items); ManagerStartMenuShortcut = (Test-Path -LiteralPath $shortcut); ShortcutPath = $shortcut } | ConvertTo-Json -Depth 5
