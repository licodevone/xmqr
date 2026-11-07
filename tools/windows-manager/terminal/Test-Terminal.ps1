#requires -Version 7.0
# SPDX-License-Identifier: MIT
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot/XMQR-Terminal.ps1"
$script:OriginalInvoker = ${function:Invoke-XmqrHelper}
$script:Cases = 0
function Reset-Fixture {
    $script:Entries = @(
        [pscustomobject]@{id='broker';name='SYNTHETIC Broker';service='xmqr-broker';state='Em execução';detail=$null},
        [pscustomobject]@{id='admin';name='SYNTHETIC Admin';service='xmqr-admin';state='Em execução';detail=$null},
        [pscustomobject]@{id='client-oracle';name='SYNTHETIC Client';service='xmqr-client-oracle';state='Em execução';detail=$null}
    )
    $script:Calls = [Collections.Generic.List[string]]::new()
    $script:Admin = $true
    $script:InventoryError = $null
    $script:HelperFailure = $false
    $script:WrongFinal = $false
}
function Invoke-XmqrHelper {
    param([string]$ManagerExe,[string[]]$Arguments,[int]$Seconds=20)
    $script:Calls.Add(($Arguments -join ' '))
    if ($Arguments[0] -eq '--diagnose') {
        return (@{components=$script:Entries;error=$script:InventoryError} | ConvertTo-Json -Depth 5 -Compress)
    }
    if ($script:HelperFailure) { throw 'SYNTHETIC helper failure' }
    if (-not $script:WrongFinal) {
        foreach ($e in $script:Entries) {
            if ($e.service -and ($Arguments[0] -eq '--control-all' -or $e.id -eq $Arguments[2])) {
                $e.state = if ($Arguments[1] -eq 'stop') { 'Parado' } else { 'Em execução' }
            }
        }
    }
    return ''
}
function Test-XmqrAdministrator { return $script:Admin }
function Show-XmqrStatus { param([object[]]$Entries) $script:Displayed = $Entries }
function Assert-True([bool]$Condition,[string]$Message) { if (-not $Condition) { throw $Message } }
function Assert-Throws([scriptblock]$Code) {
    $caught = $false
    try { $null = & $Code } catch { $caught = $true }
    Assert-True $caught 'Expected refusal did not occur'
}
function Case([string]$Name,[scriptblock]$Code) {
    Reset-Fixture
    & $Code
    $script:Cases++
    Write-Output "PASS $Name"
}
Case 'snapshot preserves three components' {
    $entries = @(Get-XmqrSnapshot 'C:\SYNTHETIC\xmqr-manager.exe')
    Assert-True ($entries.Count -eq 3) 'Snapshot should contain three records'
}
Case 'status never controls' {
    Invoke-XmqrTerminalAction -ManagerExe 'C:\SYNTHETIC\xmqr-manager.exe' -Verb status
    Assert-True (($script:Calls -join ',') -eq '--diagnose') 'Status mutated services'
}
Case 'non-admin denied before helper' {
    $script:Admin=$false
    Assert-Throws { Invoke-XmqrTerminalAction X stop broker }
    Assert-True ($script:Calls.Count -eq 0) 'Helper was called without privilege'
}
Case 'external units and shell fragments refused' {
    foreach ($target in @('sshd','broker; echo injected','../admin','--help')) {
        Assert-Throws { Invoke-XmqrTerminalAction X stop $target }
    }
    Assert-True (@($script:Calls | Where-Object { $_ -ne '--diagnose' }).Count -eq 0) 'Unsafe control happened'
}
Case 'unknown state blocks all' {
    $script:Entries[1].state='Estado indisponível'
    Assert-Throws { Invoke-XmqrTerminalAction X restart all }
    Assert-True ($script:Calls.Count -eq 1) 'Mutation despite unknown state'
}
Case 'global inventory error blocks all' {
    $script:InventoryError='SYNTHETIC blocked'
    Assert-Throws { Invoke-XmqrTerminalAction X restart all }
    Assert-True ($script:Calls.Count -eq 1) 'Mutation despite inventory error'
}
Case 'dry-run works without admin and never controls' {
    $script:Admin=$false
    $plan=Invoke-XmqrTerminalAction X restart all -Plan
    Assert-True ($plan -like 'PLANO:*') 'Missing plan'
    Assert-True ($script:Calls.Count -eq 1) 'Dry-run mutation'
}
Case 'ambiguous client refused' {
    $script:Entries += [pscustomobject]@{id='client-other';name='Other';service='xmqr-client-other';state='Em execução';detail=$null}
    Assert-Throws { Invoke-XmqrTerminalAction X stop client }
    Assert-True ($script:Calls.Count -eq 1) 'Ambiguous client control'
}
Case 'CLI component does not become service' {
    $script:Entries=@([pscustomobject]@{id='admin';name='Admin';service=$null;state='CLI instalada; sem serviço';detail=$null})
    Assert-Throws { Invoke-XmqrTerminalAction X start all }
    Assert-True ($script:Calls.Count -eq 1) 'CLI was controlled'
}
Case 'helper failure propagated' {
    $script:HelperFailure=$true
    Assert-Throws { Invoke-XmqrTerminalAction X stop broker }
    Assert-True ($script:Calls.Count -eq 2) 'Failure unexpectedly retried'
}
Case 'single control confirms final state' {
    Invoke-XmqrTerminalAction X stop broker
    Assert-True (($script:Calls -join ',') -eq '--diagnose,--control stop broker,--diagnose') 'Wrong helper calls'
    Assert-True ($script:Entries[0].state -eq 'Parado') 'Final state not updated'
}
Case 'successful helper without final state is failure' {
    $script:WrongFinal=$true
    Assert-Throws { Invoke-XmqrTerminalAction X stop broker }
}
Case 'bulk delegated to original helper' {
    Invoke-XmqrTerminalAction X restart all
    Assert-True ($script:Calls[1] -eq '--control-all restart') 'Bulk was reimplemented'
}
Case 'invalid helper arguments rejected before process' {
    Assert-Throws { & $script:OriginalInvoker -ManagerExe 'C:\SYNTHETIC\xmqr-manager.exe' -Arguments @('--control','stop','broker;bad') }
    Assert-Throws { & $script:OriginalInvoker -ManagerExe 'C:\SYNTHETIC\xmqr-manager.exe' -Arguments @('--open','logs','broker') }
}
Case 'unrecognized executable hash and absent path refused' {
    $fixtureDirectory=Join-Path ([IO.Path]::GetTempPath()) ('xmqr-terminal-'+[guid]::NewGuid().ToString('N'))
    $null=New-Item -ItemType Directory -Path $fixtureDirectory
    $fixtureFile=Join-Path $fixtureDirectory 'xmqr-manager.exe'
    try {
        [IO.File]::WriteAllText($fixtureFile,'SYNTHETIC-NOT-AN-EXECUTABLE')
        Assert-Throws { Find-XmqrManager $fixtureFile }
        Assert-Throws { Find-XmqrManager (Join-Path $fixtureDirectory 'absent/xmqr-manager.exe') }
    } finally {
        Remove-Item -LiteralPath $fixtureFile
        Remove-Item -LiteralPath $fixtureDirectory
    }
}
Write-Output "TERMINAL_WINDOWS_TEST_PASS cases=$script:Cases real_service_mutations=0"
