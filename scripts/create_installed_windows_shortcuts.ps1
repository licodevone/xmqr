# SPDX-License-Identifier: MIT
# Only creates requested desktop links for installed XMQR products.
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$principal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not [Environment]::Is64BitProcess -or -not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Execute como administrador em PowerShell 64-bit para criar atalhos no desktop publico.'
}
$base = [Microsoft.Win32.RegistryKey]::OpenBaseKey([Microsoft.Win32.RegistryHive]::LocalMachine, [Microsoft.Win32.RegistryView]::Registry64)
try {
    $key = $base.OpenSubKey('SOFTWARE\XMQR\Manager', $false)
    if ($null -eq $key) { throw 'XMQR Manager nao esta instalado.' }
    try { $manager = $key.GetValue('Executable') } finally { $key.Dispose() }
    if ($manager -isnot [string] -or $manager -notmatch '^[A-Za-z]:\\' -or $manager.Substring(2).Contains(':') -or $manager.Contains('"') -or
        -not (Test-Path -LiteralPath $manager -PathType Leaf)) { throw 'Executavel do Manager indisponivel ou registro invalido.' }
    $desktop = [Environment]::GetFolderPath([Environment+SpecialFolder]::CommonDesktopDirectory)
    if ([string]::IsNullOrEmpty($desktop) -or -not (Test-Path -LiteralPath $desktop -PathType Container)) { throw 'Desktop publico indisponivel.' }
    $cursor = Get-Item -LiteralPath $desktop -Force
    while ($null -ne $cursor) {
        if (($cursor.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Desktop com reparse point recusado.' }
        $cursor = $cursor.Parent
    }
    $names = @('XMQR Manager')
    foreach ($entry in @(
        @{ Id='broker'; Name='XMQR Broker' },
        @{ Id='client-default'; Name='XMQR Client' },
        @{ Id='admin'; Name='XMQR Admin' }
    )) {
        $registration = $base.OpenSubKey(('SOFTWARE\XMQR\Components\' + $entry.Id), $false)
        if ($null -eq $registration) { continue }
        try { $exe = $registration.GetValue('Executable') } finally { $registration.Dispose() }
        if ($exe -is [string] -and (Test-Path -LiteralPath $exe -PathType Leaf)) { $names += $entry.Name }
    }
    $shell = New-Object -ComObject WScript.Shell
    foreach ($name in $names) {
        $path = Join-Path $desktop ($name + '.lnk')
        if (Test-Path -LiteralPath $path) { Write-Output ("Atalho existente preservado: " + $name); continue }
        $link = $shell.CreateShortcut($path)
        $link.TargetPath = $manager
        $link.WorkingDirectory = [IO.Path]::GetDirectoryName($manager)
        $link.Description = 'Abrir o gerenciador da bandeja XMQR'
        $link.Save()
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($link)
        Write-Output ("Atalho criado: " + $name)
    }
    [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($shell)
} finally { $base.Dispose() }
