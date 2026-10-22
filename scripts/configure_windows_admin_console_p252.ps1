#requires -Version 7.5
# SPDX-License-Identifier: MIT
# Operator-run P252 Admin binary/config update; credential files are never opened.
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
function New-XmqrP252Security([bool] $Directory, [bool] $ServiceRead) {
    $acl = if ($Directory) { [Security.AccessControl.DirectorySecurity]::new() } else { [Security.AccessControl.FileSecurity]::new() }
    $acl.SetAccessRuleProtection($true,$false)
    $acl.SetOwner([Security.Principal.SecurityIdentifier]::new('S-1-5-32-544'))
    $inherit = if ($Directory) { [Security.AccessControl.InheritanceFlags]::ContainerInherit -bor [Security.AccessControl.InheritanceFlags]::ObjectInherit } else { [Security.AccessControl.InheritanceFlags]::None }
    foreach ($sid in @('S-1-5-18','S-1-5-32-544')) {
        $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($sid),[Security.AccessControl.FileSystemRights]::FullControl,$inherit,[Security.AccessControl.PropagationFlags]::None,[Security.AccessControl.AccessControlType]::Allow))
    }
    if ($ServiceRead) {
        $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new('S-1-5-19'),[Security.AccessControl.FileSystemRights]::ReadAndExecute,$inherit,[Security.AccessControl.PropagationFlags]::None,[Security.AccessControl.AccessControlType]::Allow))
    }
    return $acl
}
function Test-XmqrP252PrivatePolicy([Security.AccessControl.FileSystemSecurity] $Acl, [bool] $Directory, [bool] $AllowInheritedConfig = $false, [bool] $RequireServiceRead = $false) {
    $inheritedConfig = $AllowInheritedConfig -and -not $Directory -and -not $Acl.AreAccessRulesProtected
    if ((-not $Acl.AreAccessRulesProtected -and -not $inheritedConfig) -or $Acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -notin @('S-1-5-18','S-1-5-32-544')) { return $false }
    $raw = [Security.AccessControl.RawSecurityDescriptor]::new($Acl.GetSecurityDescriptorBinaryForm(),0)
    if ($null -eq $raw.DiscretionaryAcl -or $raw.DiscretionaryAcl.Count -lt 2) { return $false }
    $seen = @{}
    if ($inheritedConfig -and $raw.DiscretionaryAcl.Count -ne 3) { return $false }
    $flags = if ($Directory) { 3 } elseif ($inheritedConfig) { 16 } else { 0 }
    foreach ($ace in $raw.DiscretionaryAcl) {
        if ($ace -isnot [Security.AccessControl.CommonAce] -or $ace.IsCallback -or $ace.OpaqueLength -ne 0 -or $ace.AceQualifier -ne [Security.AccessControl.AceQualifier]::AccessAllowed -or [int]$ace.AceFlags -ne $flags) { return $false }
        $sid = $ace.SecurityIdentifier.Value
        if ($seen.ContainsKey($sid)) { return $false }
        $seen[$sid] = $true
        if ($sid -in @('S-1-5-18','S-1-5-32-544')) { if ($ace.AccessMask -ne [int][Security.AccessControl.FileSystemRights]::FullControl) { return $false } }
        elseif ($sid -eq 'S-1-5-19') { if ($ace.AccessMask -ne ([int][Security.AccessControl.FileSystemRights]::ReadAndExecute -bor [int][Security.AccessControl.FileSystemRights]::Synchronize)) { return $false } }
        else { return $false }
    }
    return $seen.ContainsKey('S-1-5-18') -and $seen.ContainsKey('S-1-5-32-544') -and (-not $RequireServiceRead -or $seen.ContainsKey('S-1-5-19'))
}
function Test-XmqrP252AclEqual([Security.AccessControl.FileSystemSecurity] $Actual, [Security.AccessControl.FileSystemSecurity] $Expected, [bool] $CompareGroup = $false) {
    if ($Actual.AreAccessRulesProtected -ne $Expected.AreAccessRulesProtected -or $Actual.GetOwner([Security.Principal.SecurityIdentifier]).Value -ne $Expected.GetOwner([Security.Principal.SecurityIdentifier]).Value) { return $false }
    if ($CompareGroup -and $Actual.GetGroup([Security.Principal.SecurityIdentifier]).Value -ne $Expected.GetGroup([Security.Principal.SecurityIdentifier]).Value) { return $false }
    $keys = @()
    foreach ($acl in @($Actual,$Expected)) {
        $raw = [Security.AccessControl.RawSecurityDescriptor]::new($acl.GetSecurityDescriptorBinaryForm(),0)
        if ($null -eq $raw.DiscretionaryAcl) { return $false }
        $entries = foreach ($ace in $raw.DiscretionaryAcl) { $binary=[byte[]]::new($ace.BinaryLength); $ace.GetBinaryForm($binary,0); [Convert]::ToBase64String($binary) }
        $keys += (($entries | Sort-Object -CaseSensitive) -join '|')
    }
    return $keys[0] -ceq $keys[1]
}
function Assert-XmqrP252Private([string] $Path, [bool] $Directory = $false, [bool] $AllowInheritedConfig = $false) {
    $null = Assert-XmqrP252Path $Path $Directory
    $acl = Get-Acl -LiteralPath $Path
    if ($AllowInheritedConfig) {
        if ($Directory -or -not [string]::Equals([IO.Path]::GetFileName($Path),'admin.toml',[StringComparison]::OrdinalIgnoreCase)) { throw 'Excecao de heranca restrita ao arquivo admin.toml.' }
        $parentAcl=Get-Acl -LiteralPath ([IO.Path]::GetDirectoryName($Path))
        if (-not (Test-XmqrP252PrivatePolicy $parentAcl $true $false $true)) { throw 'Parent privado da configuracao nao confirmado.' }
    }
    if (-not (Test-XmqrP252PrivatePolicy $acl $Directory $AllowInheritedConfig $true)) { throw 'Politica privada inesperada; permissoes existentes preservadas.' }
    return $acl
}
function New-XmqrP252PrivateDirectory([string] $Path, [bool] $ServiceRead) {
    if (Test-Path -LiteralPath $Path) { throw 'Diretorio privado existente preservado; nao repita a aplicacao.' }
    $null = Assert-XmqrP252Path ([IO.Path]::GetDirectoryName($Path)) $true
    $acl = New-XmqrP252Security $true $ServiceRead
    if (-not ('XmqrP252PrivateDirectory' -as [type])) {
        Add-Type -TypeDefinition @'
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
public static class XmqrP252PrivateDirectory {
    [StructLayout(LayoutKind.Sequential)] struct Attributes { public int Length; public IntPtr Descriptor; [MarshalAs(UnmanagedType.Bool)] public bool Inherit; }
    [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] [return:MarshalAs(UnmanagedType.Bool)]
    static extern bool CreateDirectoryW(string path, ref Attributes attributes);
    public static void Create(string path, byte[] security) {
        IntPtr data=Marshal.AllocHGlobal(security.Length);
        try {
            Marshal.Copy(security,0,data,security.Length);
            var attributes=new Attributes {Length=Marshal.SizeOf<Attributes>(),Descriptor=data,Inherit=false};
            if(!CreateDirectoryW(path,ref attributes)) throw new Win32Exception(Marshal.GetLastWin32Error(),"Create private directory");
        } finally { Marshal.FreeHGlobal(data); }
    }
}
'@
    }
    [XmqrP252PrivateDirectory]::Create($Path,$acl.GetSecurityDescriptorBinaryForm())
    $null = Assert-XmqrP252Path $Path $true
    if (-not (Test-XmqrP252AclEqual (Get-Acl -LiteralPath $Path) $acl)) { throw 'ACL do novo diretorio nao confirmada.' }
}
function Write-XmqrP252PrivateText([string] $Path, [string] $Text, [Security.AccessControl.FileSecurity] $Acl) {
    $stream = [IO.FileSystemAclExtensions]::Create([IO.FileInfo]::new($Path),[IO.FileMode]::CreateNew,[Security.AccessControl.FileSystemRights]::FullControl,[IO.FileShare]::None,4096,[IO.FileOptions]::WriteThrough,$Acl)
    try { $bytes=[Text.UTF8Encoding]::new($false).GetBytes($Text); $stream.Write($bytes); $stream.Flush($true) }
    finally { $stream.Dispose() }
    if (-not (Test-XmqrP252AclEqual (Get-Acl -LiteralPath $Path) $Acl)) { throw 'ACL do novo arquivo nao confirmada.' }
}
function Add-XmqrP252ConsoleConfig([string] $Text) {
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
    return $Text + "`n`n# P252: perfis locais mTLS; credenciais permanecem nos arquivos privados existentes.`n[mqtt_console]`nclient_bin = 'C:\Program Files\XMQR\Client\mqtt-client.exe'`nsub_profile = 'C:\ProgramData\XMQR\admin\console\sub.toml'`npub_profile = 'C:\ProgramData\XMQR\admin\console\pub.toml'`nlabel = 'XMQR local'`n"
}
function Get-XmqrP252ProfileText {
    return "version = 1`n[connection]`nhost = '127.0.0.1'`nport = 8883`nusername = 'xmqr-local'`nca = 'C:\ProgramData\XMQR\client-default\certificates\ca.crt'`ncert = 'C:\ProgramData\XMQR\client-default\certificates\client.crt'`nkey = 'C:\ProgramData\XMQR\client-default\certificates\client.key'`npassword_file = 'C:\ProgramData\XMQR\client-default\certificates\password'`nprotocol_version = '3.1.1'`nclean_session = true`nkeepalive_seconds = 30`ntimeout_seconds = 8`nreconnect_attempts = 2`n"
}
function Enter-XmqrP252RestorePrivilege {
    if (-not ('XmqrP252RestorePrivilege' -as [type])) {
        Add-Type -TypeDefinition @'
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
public sealed class XmqrP252RestorePrivilege : IDisposable {
    [StructLayout(LayoutKind.Sequential)] struct Luid { public uint Low; public int High; }
    [StructLayout(LayoutKind.Sequential)] struct Privileges { public uint Count; public Luid Id; public uint Attributes; }
    [DllImport("kernel32.dll")] static extern IntPtr GetCurrentProcess();
    [DllImport("kernel32.dll",SetLastError=true)] [return:MarshalAs(UnmanagedType.Bool)] static extern bool CloseHandle(IntPtr handle);
    [DllImport("advapi32.dll",SetLastError=true)] [return:MarshalAs(UnmanagedType.Bool)]
    static extern bool OpenProcessToken(IntPtr process,uint access,out IntPtr token);
    [DllImport("advapi32.dll",CharSet=CharSet.Unicode,SetLastError=true)] [return:MarshalAs(UnmanagedType.Bool)]
    static extern bool LookupPrivilegeValueW(string system,string name,out Luid id);
    [DllImport("advapi32.dll",SetLastError=true)] [return:MarshalAs(UnmanagedType.Bool)]
    static extern bool AdjustTokenPrivileges(IntPtr token,[MarshalAs(UnmanagedType.Bool)] bool disableAll,ref Privileges state,uint length,out Privileges previous,out uint required);
    IntPtr token;
    Privileges previous;
    XmqrP252RestorePrivilege() {
        if(!OpenProcessToken(GetCurrentProcess(),0x28,out token)) throw new Win32Exception(Marshal.GetLastWin32Error(),"Open current process token");
        try {
            Luid id;
            if(!LookupPrivilegeValueW(null,"SeRestorePrivilege",out id)) throw new Win32Exception(Marshal.GetLastWin32Error(),"Lookup SeRestorePrivilege");
            var requested=new Privileges {Count=1,Id=id,Attributes=2}; uint required;
            if(!AdjustTokenPrivileges(token,false,ref requested,(uint)Marshal.SizeOf<Privileges>(),out previous,out required))
                throw new Win32Exception(Marshal.GetLastWin32Error(),"Enable SeRestorePrivilege");
            int error=Marshal.GetLastWin32Error();
            if(error!=0) throw new Win32Exception(error,"SeRestorePrivilege unavailable; no service/files changed");
        } catch { CloseHandle(token);token=IntPtr.Zero;throw; }
    }
    public static XmqrP252RestorePrivilege Acquire() { return new XmqrP252RestorePrivilege(); }
    public void Dispose() {
        if(token==IntPtr.Zero) return;
        try {
            if(previous.Count!=0) {
                Privileges ignored; uint required;
                if(!AdjustTokenPrivileges(token,false,ref previous,(uint)Marshal.SizeOf<Privileges>(),out ignored,out required))
                    throw new Win32Exception(Marshal.GetLastWin32Error(),"Restore previous privilege state; close this PowerShell process");
                int error=Marshal.GetLastWin32Error();
                if(error!=0) throw new Win32Exception(error,"Restore previous privilege state; close this PowerShell process");
            }
        } finally { CloseHandle(token);token=IntPtr.Zero; }
    }
}
'@
    }
    return [XmqrP252RestorePrivilege]::Acquire()
}
function Assert-XmqrP252AdminCapabilities([string] $Executable) {
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
function Stop-XmqrP252Admin($Service) {
    $Service.Refresh()
    if ($Service.Status -eq [ServiceProcess.ServiceControllerStatus]::Stopped) { return }
    if ($Service.Status -ne [ServiceProcess.ServiceControllerStatus]::Running -or @($Service.DependentServices | Where-Object Status -ne 'Stopped').Count -ne 0) { throw 'Admin em transicao ou com dependentes ativos; parada recusada.' }
    $Service.Stop($false)
    $Service.WaitForStatus([ServiceProcess.ServiceControllerStatus]::Stopped,[TimeSpan]::FromSeconds(20))
}
function Start-XmqrP252Admin($Service) {
    $Service.Refresh()
    if ($Service.Status -eq [ServiceProcess.ServiceControllerStatus]::Stopped) { $Service.Start() }
    elseif ($Service.Status -ne [ServiceProcess.ServiceControllerStatus]::Running) { throw 'Admin em transicao; inicio recusado.' }
    $Service.WaitForStatus([ServiceProcess.ServiceControllerStatus]::Running,[TimeSpan]::FromSeconds(20))
}
function Watch-XmqrP252Admin($Service) {
    foreach ($step in 1..10) {
        Start-Sleep -Seconds 2; $Service.Refresh()
        if ($Service.Status -ne [ServiceProcess.ServiceControllerStatus]::Running) { throw 'Admin parou durante a observacao de 20s.' }
    }
}

# Main: only Admin SCM and its binary/config; credential files are metadata-only.
Assert-XmqrP252Administrator
$installed=Assert-XmqrP252Path 'C:\Program Files\XMQR\Admin\xmqr-admin.exe'
$installFolder=Assert-XmqrP252Path 'C:\Program Files\XMQR\Admin' $true
Assert-XmqrP252BinaryAcl $installed
Assert-XmqrP252BinaryAcl $installFolder
$root='C:\ProgramData\XMQR\admin'; $config=Join-Path $root 'admin.toml'; $console=Join-Path $root 'console'
$null=Assert-XmqrP252Private $root $true
$configAcl=Assert-XmqrP252Private $config $false $true
if (Test-Path -LiteralPath $console) { throw 'console/ ja existe; preserve seus perfis e solicite revisao antes de reaplicar.' }
$key='SOFTWARE\XMQR\Components\admin'
foreach ($field in @(@('Executable',$installed),@('ConfigFile',$config),@('ServiceName','xmqr-admin'),@('Kind','admin'))) {
    if (-not [string]::Equals((Get-XmqrP252MachineValue $key $field[0]),$field[1],[StringComparison]::OrdinalIgnoreCase)) { throw 'Registro do Admin diverge da instalacao padrao.' }
}
$expected='"C:\Program Files\XMQR\Admin\xmqr-admin.exe" --windows-service xmqr-admin "C:\ProgramData\XMQR\admin\logs\." --config "C:\ProgramData\XMQR\admin\admin.toml"'
$record=Get-CimInstance -ClassName Win32_Service -Filter "Name='xmqr-admin'"
if ($null -eq $record -or $record.StartName -ne 'NT AUTHORITY\LocalService' -or -not [string]::Equals($record.PathName,$expected,[StringComparison]::OrdinalIgnoreCase) -or $record.State -notin @('Running','Stopped')) { throw 'Conta/caminho/estado do servico Admin inesperado.' }
$client=Assert-XmqrP252Path 'C:\Program Files\XMQR\Client\mqtt-client.exe'
Assert-XmqrP252BinaryAcl $client
if (-not [string]::Equals((Get-XmqrP252MachineValue 'SOFTWARE\XMQR\Components\client-default' 'Executable'),$client,[StringComparison]::OrdinalIgnoreCase)) { throw 'Registro do Client diverge do caminho esperado.' }
$credentialRoot='C:\ProgramData\XMQR\client-default\certificates'
$null=Assert-XmqrP252Private $credentialRoot $true
foreach ($name in @('ca.crt','client.crt','client.key','password')) { $null=Assert-XmqrP252Private (Join-Path $credentialRoot $name) } # No contents/hash are read.
$candidate=Get-XmqrP252Candidate 'admin' 'xmqr-admin.exe'
Assert-XmqrP252AdminCapabilities $candidate.Path
if ((Get-XmqrP252Hash $candidate.Path) -cne $candidate.Hash) { throw 'Candidato mudou apos consulta de capacidades.' }
$oldHash=Get-XmqrP252Hash $installed
$oldConfigHash=Get-XmqrP252Hash $config
if ((Get-Item -LiteralPath $config).Length -gt 65536) { throw 'Configuracao excede 64KiB.' }
$configText=[Text.UTF8Encoding]::new($false,$true).GetString([IO.File]::ReadAllBytes($config))
$newConfigText=Add-XmqrP252ConsoleConfig $configText
if ((Get-XmqrP252Hash $config) -cne $oldConfigHash) { throw 'Configuracao mudou durante preflight.' }
$service=Get-Service -Name 'xmqr-admin'; $service.Refresh()
if ($service.Status.ToString() -notin @('Running','Stopped')) { throw 'Admin mudou para estado transitorio.' }
$wasRunning=$service.Status -eq [ServiceProcess.ServiceControllerStatus]::Running
$binaryFolder=Join-Path $installFolder ('p252-backup-'+[Guid]::NewGuid().ToString('N'))
$privateFolder=Join-Path $root ('p252-backup-'+[Guid]::NewGuid().ToString('N'))
$binaryBackup=Join-Path $binaryFolder 'xmqr-admin.previous.exe'; $configBackup=Join-Path $privateFolder 'admin.previous.toml'
$binaryAttempted=$false; $configAttempted=$false; $createdConsole=$false; $newConfigHash=$null; $restoreScope=$null; $serviceStopAttempted=$false
try {
    # This can fail before any SCM operation or filesystem mutation. The previous
    # process privilege state is restored as soon as identity-preserving staging ends.
    $restoreScope=Enter-XmqrP252RestorePrivilege
    $serviceStopAttempted=$true
    Stop-XmqrP252Admin $service
    if ((Get-XmqrP252Hash $installed) -cne $oldHash -or (Get-XmqrP252Hash $config) -cne $oldConfigHash -or -not (Test-XmqrP252AclEqual (Get-Acl -LiteralPath $config) $configAcl $true)) { throw 'Binario/config/ACL mudou antes da aplicacao; preserve alteracoes.' }
    if (Test-Path -LiteralPath $binaryFolder) { throw 'Backup binario existente preservado.' }
    $null=[IO.Directory]::CreateDirectory($binaryFolder); $null=Assert-XmqrP252Path $binaryFolder $true
    New-XmqrP252PrivateDirectory $privateFolder $false
    New-XmqrP252PrivateDirectory $console $true; $createdConsole=$true
    $profileText=Get-XmqrP252ProfileText
    foreach ($name in @('sub.toml','pub.toml')) { Write-XmqrP252PrivateText (Join-Path $console $name) $profileText (New-XmqrP252Security $false $true) }
    $stagedConfig=Join-Path $privateFolder 'admin.new.toml'
    $stageAcl=New-XmqrP252Security $false $false
    $stageAcl.SetOwner($configAcl.GetOwner([Security.Principal.SecurityIdentifier]))
    $stageAcl.SetGroup($configAcl.GetGroup([Security.Principal.SecurityIdentifier]))
    Write-XmqrP252PrivateText $stagedConfig $newConfigText $stageAcl
    if (-not (Test-XmqrP252AclEqual (Get-Acl -LiteralPath $stagedConfig) $stageAcl $true)) { throw 'Identidade original do staging nao confirmada.' }
    $restoreScope.Dispose(); $restoreScope=$null
    $newConfigHash=Get-XmqrP252Hash $stagedConfig
    $stage=Join-Path $binaryFolder 'xmqr-admin.new.exe'; Copy-XmqrP252NewFile $candidate.Path $stage
    $binaryAttempted=$true
    Replace-XmqrP252File $stage $installed $binaryBackup $candidate.Hash $oldHash
    Assert-XmqrP252BinaryAcl $installed
    $configAttempted=$true
    Replace-XmqrP252File $stagedConfig $config $configBackup $newConfigHash $oldConfigHash
    if (-not (Test-XmqrP252AclEqual (Get-Acl -LiteralPath $config) $configAcl $true)) { throw 'ACL original da configuracao nao preservada.' }
    Start-XmqrP252Admin $service
    Watch-XmqrP252Admin $service
    Write-Output "Admin atualizado e em execucao. Backups preservados: $binaryFolder ; $privateFolder"
    Write-Output 'Abra http://127.0.0.1:9080/ e entre com sua conta existente. Console MQTT: topico autorizado xmqr/local/test.'
} catch {
    $failure=$_
    if (-not $serviceStopAttempted) { throw $failure }
    try {
        Stop-XmqrP252Admin $service
        $currentConfig=Get-XmqrP252Hash $config; $currentBinary=Get-XmqrP252Hash $installed
        # Validate BOTH destinations before restoring either, preserving unexpected edits.
        if ($currentConfig -cne $oldConfigHash -and (-not $configAttempted -or $currentConfig -cne $newConfigHash)) { throw 'Edicao inesperada da configuracao preservada.' }
        if ($currentBinary -cne $oldHash -and (-not $binaryAttempted -or $currentBinary -cne $candidate.Hash)) { throw 'Edicao inesperada do binario preservada.' }
        if (-not (Test-XmqrP252AclEqual (Get-Acl -LiteralPath $config) $configAcl $true)) { throw 'Edicao inesperada de ACL preservada.' }
        if ($currentConfig -cne $oldConfigHash) { Replace-XmqrP252File $configBackup $config (Join-Path $privateFolder 'admin.failed.toml') $oldConfigHash $newConfigHash }
        if ($currentBinary -cne $oldHash) { Replace-XmqrP252File $binaryBackup $installed (Join-Path $binaryFolder 'xmqr-admin.failed.exe') $oldHash $candidate.Hash }
        if (-not (Test-XmqrP252AclEqual (Get-Acl -LiteralPath $config) $configAcl $true)) { throw 'ACL apos rollback nao confirmada.' }
        if ($wasRunning) { Start-XmqrP252Admin $service }
        Write-Warning 'Aplicacao interrompida; binario/config anteriores confirmados. Admin reiniciado somente se ja estava em execucao.'
    } catch { Write-Warning "Recuperacao automatica incompleta; preserve backups: $binaryFolder ; $privateFolder" }
    # New profiles contain references only. Preserve them and all backups for review;
    # an existing console/ is never removed or overwritten on a later invocation.
    if ($createdConsole) { Write-Warning 'Perfis novos preservados em console/ para revisao; nao reaplique sem revisar esse diretorio.' }
    throw $failure
} finally {
    try { if ($null -ne $restoreScope) { $restoreScope.Dispose() } }
    finally { $service.Dispose() }
}
