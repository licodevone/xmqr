#requires -Version 7.5
# SPDX-License-Identifier: MIT
# In-memory regression/negative tests only: never reads or changes host ACLs.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
Import-Module (Join-Path $PSScriptRoot 'windows_private_acl.psm1') -Force

function Security([string] $Sddl, [switch] $File) {
    $value = if ($File) { [Security.AccessControl.FileSecurity]::new() } else { [Security.AccessControl.DirectorySecurity]::new() }
    $value.SetSecurityDescriptorSddlForm($Sddl)
    return $value
}
$expected = Security 'O:BAD:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)'
$cases = @(
    @{ Name='Exact policy'; Sddl='O:BAD:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)'; Accept=$true },
    @{ Name='Operator screenshot AI and primary group'; Sddl='O:BAG:S-1-5-21-1052470259-4011911723-875344149-1001D:PAI(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)'; Accept=$true },
    @{ Name='Reordered allow entries'; Sddl='O:BAD:PAI(A;OICI;FA;;;BA)(A;OICI;FA;;;SY)'; Accept=$true },
    @{ Name='Wrong owner'; Sddl='O:SYD:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)'; Accept=$false },
    @{ Name='Unprotected policy'; Sddl='O:BAD:(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)'; Accept=$false },
    @{ Name='Extra Everyone'; Sddl='O:BAD:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)(A;OICI;FA;;;WD)'; Accept=$false },
    @{ Name='Missing Administrators'; Sddl='O:BAD:P(A;OICI;FA;;;SY)'; Accept=$false },
    @{ Name='Reduced Administrators rights'; Sddl='O:BAD:P(A;OICI;FA;;;SY)(A;OICI;FR;;;BA)'; Accept=$false },
    @{ Name='LocalService forbidden in staging'; Sddl='O:BAD:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)(A;OICI;FR;;;LS)'; Accept=$false },
    @{ Name='Deny entry'; Sddl='O:BAD:P(D;OICI;FA;;;SY)(A;OICI;FA;;;BA)'; Accept=$false },
    @{ Name='Identical allow entries consolidated by Windows API'; Sddl='O:BAD:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)(A;OICI;FA;;;BA)'; Accept=$true },
    @{ Name='Additional grant to different SID'; Sddl='O:BAD:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)(A;OICI;FW;;;AU)'; Accept=$false },
    @{ Name='Inherited ACE flag'; Sddl='O:BAD:P(A;OICIID;FA;;;SY)(A;OICI;FA;;;BA)'; Accept=$false },
    @{ Name='Different propagation'; Sddl='O:BAD:P(A;OICINP;FA;;;SY)(A;OICI;FA;;;BA)'; Accept=$false },
    @{ Name='Missing inheritance'; Sddl='O:BAD:P(A;;FA;;;SY)(A;OICI;FA;;;BA)'; Accept=$false },
    @{ Name='Empty DACL'; Sddl='O:BAD:P'; Accept=$false },
    @{ Name='Null DACL'; Sddl='O:BAD:PNO_ACCESS_CONTROL'; Accept=$false }
)
$passed = 0
foreach ($case in $cases) {
    $result = Test-XmqrPrivateAcl -Actual (Security $case.Sddl) -Expected $expected
    if ($result -ne $case.Accept) { throw "FAIL: $($case.Name)" }
    $passed++
    Write-Output "PASS $($case.Name)"
}
$fileExpected = Security 'O:BAD:P(A;;FA;;;SY)(A;;FA;;;BA)(A;;0x1200a9;;;LS)' -File
foreach ($case in @(
    @{ Name='Service-readable file accepts descriptor AI'; Sddl='O:BAD:PAI(A;;FA;;;SY)(A;;FA;;;BA)(A;;0x1200a9;;;LS)'; Accept=$true },
    @{ Name='Service-write rejected on read-only file'; Sddl='O:BAD:P(A;;FA;;;SY)(A;;FA;;;BA)(A;;FA;;;LS)'; Accept=$false }
)) {
    if ((Test-XmqrPrivateAcl -Actual (Security $case.Sddl -File) -Expected $fileExpected) -ne $case.Accept) { throw "FAIL: $($case.Name)" }
    $passed++
    Write-Output "PASS $($case.Name)"
}
Write-Output "$passed ACL checks passed; no filesystem permissions were changed."
