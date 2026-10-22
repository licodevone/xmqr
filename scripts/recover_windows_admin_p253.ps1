#requires -Version 7.5
# SPDX-License-Identifier: MIT
# P253: diagnostic by default; -Resume only starts the verified installed Admin.
[CmdletBinding()]
param([switch] $Resume)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Assert-XmqrP253Path([string] $Path, [bool] $Directory = $false) {
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

function Get-XmqrP253Hash([string] $Path) { return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }

function Assert-XmqrP253Administrator {
    if (-not $IsWindows -or -not [Environment]::Is64BitProcess) { throw 'Use PowerShell 7.5+ Windows 64-bit como administrador.' }
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    try {
        if (-not ([Security.Principal.WindowsPrincipal]::new($identity)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Execute em PowerShell como administrador.' }
    } finally { $identity.Dispose() }
}

function Get-XmqrP253MachineValue([string] $Key, [string] $Name) {
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

function Assert-XmqrP253BinaryAcl([string] $Path) {
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

function Add-XmqrP253ConsoleConfig([string] $Text) {
    if ($Text.Length -gt 65536 -or $Text.Contains([char]0)) { throw 'Configuracao excede limite ou contem NUL.' }
    $keys = @{}
    foreach ($line in ($Text -split '\r?\n')) {
        if ($line -match '^\s*(#.*)?$') { continue }
        if ($line -notmatch '^\s*(?<key>version|bind|monitor|token_file|users_file)\s*=\s*(?<value>1|''[^''\r\n]*''|"(?:[^"\\\r\n]|\\.)*")\s*(?:#.*)?$') { throw 'Configuracao personalizada/tabela existente recusada; arquivo preservado para revisao.' }
        $key = $Matches.key; $value = $Matches.value
        if ($keys.ContainsKey($key) -or ($key -eq 'version' -and $value -cne '1') -or ($key -ne 'version' -and $value -eq '1')) { throw 'Schema de configuracao nao reconhecido.' }
        $keys[$key]=$true
    }
    foreach ($required in @('version','bind','monitor','token_file')) { if (-not $keys.ContainsKey($required)) { throw 'Configuracao Admin incompleta.' } }
    return $Text + "`n`n# P253: perfis locais mTLS; credenciais permanecem nos arquivos privados existentes.`n[mqtt_console]`nclient_bin = 'C:\Program Files\XMQR\Client\mqtt-client.exe'`nsub_profile = 'C:\ProgramData\XMQR\admin\console\sub.toml'`npub_profile = 'C:\ProgramData\XMQR\admin\console\pub.toml'`nlabel = 'XMQR local'`n"
}

function Get-XmqrP253ProfileText {
    return "version = 1`n[connection]`nhost = '127.0.0.1'`nport = 8883`nusername = 'xmqr-local'`nca = 'C:\ProgramData\XMQR\client-default\certificates\ca.crt'`ncert = 'C:\ProgramData\XMQR\client-default\certificates\client.crt'`nkey = 'C:\ProgramData\XMQR\client-default\certificates\client.key'`npassword_file = 'C:\ProgramData\XMQR\client-default\certificates\password'`nprotocol_version = '3.1.1'`nclean_session = true`nkeepalive_seconds = 30`ntimeout_seconds = 8`nreconnect_attempts = 2`n"
}

function Assert-XmqrP253AdminCapabilities([string] $Executable) {
    $start=[Diagnostics.ProcessStartInfo]::new(); $start.FileName=$Executable; $start.ArgumentList.Add('--windows-service-capabilities')
    $start.UseShellExecute=$false; $start.CreateNoWindow=$true; $start.RedirectStandardOutput=$true; $start.RedirectStandardError=$true
    $process=[Diagnostics.Process]::new(); $process.StartInfo=$start
    try {
        if (-not $process.Start()) { throw 'Consulta de capacidades falhou.' }
        $stdout=$process.StandardOutput.ReadToEndAsync(); $stderr=$process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit(15000)) { throw 'Consulta de capacidades excedeu 15s; nenhum processo foi forcado a encerrar.' }
        $text=$stdout.GetAwaiter().GetResult(); $null=$stderr.GetAwaiter().GetResult()
        if ($process.ExitCode -ne 0 -or $text.Length -gt 4096) { throw 'Capacidades do candidato recusadas.' }
        $caps=$text | ConvertFrom-Json
        if ($caps.schema -ne 1 -or $caps.component -cne 'admin' -or $caps.service_entrypoint -isnot [bool] -or -not $caps.service_entrypoint) { throw 'Candidato nao identifica adaptador Admin Windows.' }
    } finally { $process.Dispose() }
}
