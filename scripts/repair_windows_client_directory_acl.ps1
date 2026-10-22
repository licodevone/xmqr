#requires -Version 7.5
# SPDX-License-Identifier: MIT
[CmdletBinding()]
param([switch] $StartServices)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Get-XmqrClientRepairedAcl {
    param([Security.AccessControl.DirectorySecurity] $Acl, [string] $OperatorSid)
    if ($OperatorSid -notmatch '^S-1-5-21-(\d+-){3}\d+$') { throw 'SID pessoal do operador inesperado.' }
    if ($Acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -cne 'S-1-5-18' -or
        -not $Acl.AreAccessRulesProtected) { throw 'Proprietario ou protecao da pasta divergem do diagnostico.' }
    $rules = @($Acl.GetAccessRules($true, $true, [Security.Principal.SecurityIdentifier]))
    $raw = [Security.AccessControl.RawSecurityDescriptor]::new($Acl.GetSecurityDescriptorBinaryForm(), 0)
    if ($null -eq $raw.DiscretionaryAcl -or $raw.DiscretionaryAcl.Count -ne $rules.Count) { throw 'ACL nao representavel pelo caso diagnosticado.' }
    foreach ($ace in $raw.DiscretionaryAcl) {
        if ($ace -isnot [Security.AccessControl.CommonAce] -or $ace.IsCallback -or $ace.OpaqueLength -ne 0 -or
            $ace.AceQualifier -ne [Security.AccessControl.AceQualifier]::AccessAllowed) {
            throw 'Tipo de ACE inesperado; preservado.'
        }
    }
    $expected = @{'S-1-5-18'=2032127; 'S-1-5-19'=1179817; 'S-1-5-32-544'=2032127}
    $seen = @{}
    $extra = $null
    foreach ($rule in $rules) {
        $sid = $rule.IdentityReference.Value
        if ($rule.IsInherited -or $rule.AccessControlType -ne [Security.AccessControl.AccessControlType]::Allow -or
            [int]$rule.InheritanceFlags -ne 3 -or [int]$rule.PropagationFlags -ne 0 -or $seen.ContainsKey($sid)) {
            throw 'Regra de permissao diferente do caso diagnosticado; preservada.'
        }
        $seen[$sid] = $true
        if ($expected.ContainsKey($sid)) {
            if ([int]$rule.FileSystemRights -ne $expected[$sid]) { throw 'Permissao de sistema/servico inesperada.' }
        } elseif ($sid -ceq $OperatorSid -and [int]$rule.FileSystemRights -eq 2032127) {
            $extra = $rule
        } else { throw 'Outro principal ou permissao encontrado; nenhuma mudanca autorizada.' }
    }
    foreach ($sid in $expected.Keys) { if (-not $seen.ContainsKey($sid)) { throw 'Regra de sistema/servico ausente.' } }
    if ($rules.Count -notin @(3,4) -or ($rules.Count -eq 4 -and $null -eq $extra)) { throw 'Quantidade de regras inesperada.' }
    $result = [Security.AccessControl.DirectorySecurity]::new()
    $result.SetSecurityDescriptorBinaryForm($Acl.GetSecurityDescriptorBinaryForm())
    if ($null -ne $extra) { $result.RemoveAccessRuleSpecific($extra) }
    [pscustomobject]@{ Acl=$result; ChangeRequired=($null -ne $extra) }
}

function Assert-XmqrRepairPath([string] $Path) {
    $item = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    while ($null -ne $item) {
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Reparse point recusado.' }
        $item = if ($item -is [IO.FileInfo]) { $item.Directory } else { $item.Parent }
    }
}

function Start-XmqrRepairService([string] $Name) {
    $service = Get-Service -Name $Name -ErrorAction Stop
    try {
        if ($service.Status -eq 'Stopped') { $service.Start() }
        elseif ($service.Status -ne 'Running') { throw "Servico em transicao: $Name" }
        $service.WaitForStatus([ServiceProcess.ServiceControllerStatus]::Running, [TimeSpan]::FromSeconds(20))
    } finally { $service.Dispose() }
}

function Get-XmqrProtectedChildSnapshot([string] $Directory) {
    $snapshot = @{}
    foreach ($item in @(Get-ChildItem -LiteralPath $Directory -Force -ErrorAction Stop)) {
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Filho reparse recusado.' }
        $security = Get-Acl -LiteralPath $item.FullName -ErrorAction Stop
        if (-not $security.AreAccessRulesProtected) { throw 'Filho sem DACL protegida; reparo recusado para impedir propagacao.' }
        $snapshot[$item.Name] = $security.Sddl
    }
    return $snapshot
}

if (-not $IsWindows -or -not [Environment]::Is64BitProcess) { throw 'Use PowerShell 7.5+ Windows x64 como administrador.' }
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
try {
    if (-not ([Security.Principal.WindowsPrincipal]::new($identity)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Execute em PowerShell como administrador.'
    }
    $operatorSid = $identity.User.Value
} finally { $identity.Dispose() }
$folder = 'C:\ProgramData\XMQR\client-default'
Assert-XmqrRepairPath $folder
if (-not (Get-Item -LiteralPath $folder).PSIsContainer) { throw 'Pasta esperada ausente.' }
$expectedCommand = '"C:\Program Files\XMQR\Client\mqtt-client.exe" --windows-service xmqr-client-default "C:\ProgramData\XMQR\client-default\logs\." --config "C:\ProgramData\XMQR\client-default\client.toml"'
$service = Get-CimInstance Win32_Service -Filter "Name='xmqr-client-default'" -ErrorAction Stop
if ($null -eq $service -or $service.StartName -ine 'NT AUTHORITY\LocalService' -or
    $service.PathName -ine $expectedCommand -or $service.State -ne 'Stopped') {
    throw 'Client deve estar parado, na conta e caminho padrao do diagnostico.'
}
$before = Get-Acl -LiteralPath $folder
$repair = Get-XmqrClientRepairedAcl -Acl $before -OperatorSid $operatorSid
Import-Module (Join-Path $PSScriptRoot 'windows_private_acl.psm1') -Force
if ($repair.ChangeRequired) {
    $childrenBefore = Get-XmqrProtectedChildSnapshot $folder
    $target = Join-Path (Split-Path $PSScriptRoot -Parent) 'target'
    Assert-XmqrRepairPath $target
    $backup = Join-Path $target ('p251-acl-before-' + [Guid]::NewGuid().ToString('N') + '.json')
    $text = [ordered]@{ Schema=1; CreatedUtc=[DateTime]::UtcNow.ToString('o'); Path=$folder; BeforeSddl=$before.Sddl; ExpectedSddl=$repair.Acl.Sddl } | ConvertTo-Json
    $stream = [IO.File]::Open($backup, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    try { $bytes=[Text.UTF8Encoding]::new($false).GetBytes($text); $stream.Write($bytes,0,$bytes.Length); $stream.Flush($true) }
    finally { $stream.Dispose() }
    $live = Get-Acl -LiteralPath $folder
    if (-not (Test-XmqrPrivateAcl -Actual $live -Expected $before) -or
        $live.GetGroup([Security.Principal.SecurityIdentifier]).Value -cne $before.GetGroup([Security.Principal.SecurityIdentifier]).Value) { throw 'Permissoes mudaram durante a verificacao; nenhuma alteracao aplicada.' }
    $liveRule = @($live.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]) | Where-Object { $_.IdentityReference.Value -ceq $operatorSid })
    if ($liveRule.Count -ne 1) { throw 'Regra pessoal mudou; nenhuma alteracao aplicada.' }
    $live.RemoveAccessRuleSpecific($liveRule[0])
    [IO.FileSystemAclExtensions]::SetAccessControl([IO.DirectoryInfo]::new($folder), $live)
    $childrenAfter = Get-XmqrProtectedChildSnapshot $folder
    if ($childrenBefore.Count -ne $childrenAfter.Count) { throw 'Filhos mudaram durante o reparo; colete diagnostico.' }
    foreach ($name in $childrenBefore.Keys) {
        if (-not $childrenAfter.ContainsKey($name) -or $childrenAfter[$name] -cne $childrenBefore[$name]) { throw 'Metadados de filho mudaram; colete diagnostico.' }
    }
    Write-Output "Regra pessoal removida somente da pasta client-default. Backup de metadados: $backup"
} else { Write-Output 'Pasta ja possui as tres regras privadas esperadas.' }
if (-not (Test-XmqrPrivateAcl -Actual (Get-Acl -LiteralPath $folder) -Expected $repair.Acl)) { throw 'ACL final nao confirmada; colete diagnostico.' }
if ((Get-Acl -LiteralPath $folder).GetGroup([Security.Principal.SecurityIdentifier]).Value -cne $before.GetGroup([Security.Principal.SecurityIdentifier]).Value) { throw 'Grupo final diverge; colete diagnostico.' }
Write-Output 'ACL privada confirmada. Nenhum arquivo filho foi modificado.'
if (-not $StartServices) { return }

Start-XmqrRepairService 'xmqr-broker'
$handler = [Net.Http.HttpClientHandler]::new()
$handler.UseProxy = $false
$handler.AllowAutoRedirect = $false
$http = [Net.Http.HttpClient]::new($handler)
$http.Timeout = [TimeSpan]::FromSeconds(2)
$ready = $false
try {
    for ($attempt=0; $attempt -lt 10; $attempt++) {
        try {
            $response = $http.GetAsync('http://127.0.0.1:9090/ready').GetAwaiter().GetResult()
            try { $ready = [int]$response.StatusCode -eq 200 } finally { $response.Dispose() }
        } catch { $ready=$false }
        if ($ready) { break }
        Start-Sleep -Seconds 1
    }
} finally { $http.Dispose() }
if (-not $ready) { throw 'Broker nao atingiu readiness200; Client nao foi iniciado. Colete diagnostico.' }
Start-XmqrRepairService 'xmqr-client-default'
Start-XmqrRepairService 'xmqr-admin'
for ($elapsed=0; $elapsed -le 120; $elapsed+=2) {
    $states = @(Get-Service -Name 'xmqr-broker','xmqr-client-default','xmqr-admin' -ErrorAction Stop)
    if (@($states | Where-Object Status -ne 'Running').Count -gt 0) { throw 'Servico deixou de estar Running; preserve os dados e colete novo diagnostico.' }
    if ($elapsed % 20 -eq 0) { Write-Output "Tres servicos Running: $elapsed/120 segundos." }
    if ($elapsed -lt 120) { Start-Sleep -Seconds 2 }
}
Write-Output 'Reparo concluido e observacao de 120 segundos aprovada.'
