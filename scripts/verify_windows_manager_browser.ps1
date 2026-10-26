#requires -Version 7.0
# SPDX-License-Identifier: MIT
# Own fixtures only. Does not open installed configurations or alter ACLs.
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$fixture = Join-Path ([IO.Path]::GetTempPath()) ('xmqr-browser-qa-' + [guid]::NewGuid().ToString('N'))
$null = New-Item -ItemType Directory -Path $fixture
$null = New-Item -ItemType Directory -Path (Join-Path $fixture 'Pasta com espaços e acentuação')
[IO.File]::WriteAllText((Join-Path $fixture "Arquivo com 'aspas'.txt"), 'fixture only')
$process = $null
try {
    $source = [IO.File]::ReadAllText((Join-Path $repo 'tools/windows-manager/src/browse-folder.ps1'))
    $smoke = @'
    if ($list.Items.Count -ne 2) { exit 31 }
    if ($address.Text -ne $root -or $up.Enabled) { exit 32 }
    $folder = @($list.Items | Where-Object { $_.Tag })
    if ($folder.Count -ne 1) { exit 33 }
    Show-Directory ([string]$folder[0].Tag)
    if ($list.Items.Count -ne 0 -or -not $up.Enabled) { exit 34 }
    Show-Directory $root
    $qaTimer = New-Object System.Windows.Forms.Timer
    $qaTimer.Interval = 600
    $qaTimer.Add_Tick({ $qaTimer.Stop(); $form.Close() })
    $qaTimer.Start()
    [void]$form.ShowDialog()
    $qaTimer.Dispose()
'@
    $needle = '[void]$form.ShowDialog()'
    if (-not $source.Contains($needle)) { throw 'Browser dialog entry point changed; review this smoke.' }
    $source = $source.Replace($needle, $smoke)
    $start = [Diagnostics.ProcessStartInfo]::new()
    $start.FileName = Join-Path $env:SystemRoot 'System32/WindowsPowerShell/v1.0/powershell.exe'
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    foreach ($argument in @('-NoLogo','-NoProfile','-NonInteractive','-STA','-Command',$source)) {
        $start.ArgumentList.Add($argument)
    }
    $start.Environment['XMQR_BROWSE_ROOT'] = $fixture
    $start.Environment['PSModulePath'] = Join-Path $env:SystemRoot 'System32/WindowsPowerShell/v1.0/Modules'
    $process = [Diagnostics.Process]::Start($start)
    $stdout = $process.StandardOutput.ReadToEndAsync()
    $stderr = $process.StandardError.ReadToEndAsync()
    if (-not $process.WaitForExit(15000)) {
        $process.Kill()
        $process.WaitForExit()
        throw 'Browser smoke timed out.'
    }
    $errorText = $stderr.GetAwaiter().GetResult()
    if ($process.ExitCode -ne 0) { throw "Browser smoke failed: $($process.ExitCode) $errorText" }
    Write-Output 'PASS: native folder window, listing, child navigation, root boundary and Unicode paths.'
} finally {
    if ($process) { $process.Dispose() }
    # Checked absolute fixture, exclusively created by this script.
    $absolute = [IO.Path]::GetFullPath($fixture)
    $tempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\') + '\'
    if (-not $absolute.StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase) -or
        -not ([IO.Path]::GetFileName($absolute)).StartsWith('xmqr-browser-qa-')) {
        throw 'Refusing cleanup outside the owned test fixture.'
    }
    Remove-Item -LiteralPath $absolute -Recurse -Force
}
