$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
$owner = New-Object System.Windows.Forms.Form
$owner.TopMost = $true
[void][System.Windows.Forms.MessageBox]::Show($owner, $env:XMQR_ERROR_MESSAGE,
    'XMQR Manager', [System.Windows.Forms.MessageBoxButtons]::OK,
    [System.Windows.Forms.MessageBoxIcon]::Error)
$owner.Dispose()
