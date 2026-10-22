#requires -Version 7.5
# SPDX-License-Identifier: MIT
# Tests the actual initializer function with nonsecret files under target only.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$sourceScript = Join-Path $PSScriptRoot 'initialize_windows_local.ps1'
$tokensFound = $null; $errorsFound = $null
$ast = [Management.Automation.Language.Parser]::ParseFile($sourceScript, [ref]$tokensFound, [ref]$errorsFound)
if ($errorsFound.Count) { throw 'Initializer parser errors.' }
$functionAst = $ast.Find({ param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Replace-XmqrClientConfig' }, $false)
if ($null -eq $functionAst) { throw 'Production replacement function missing.' }
# Load only this function, never the initializer's top-level provisioning/SCM.
. ([scriptblock]::Create($functionAst.Extent.Text))
$root = Join-Path (Split-Path $PSScriptRoot -Parent) ('target/p247-replace-' + [Guid]::NewGuid().ToString('N'))
$null = New-Item -ItemType Directory -Path $root
$passed = 0
function Check([string] $Name, [bool] $Condition) {
    if (-not $Condition) { throw "FAIL $Name" }
    $script:passed++
    Write-Output "PASS $Name"
}
function Fixture([string] $Name) {
    $directory = Join-Path $root $Name
    $null = New-Item -ItemType Directory -Path $directory
    $paths = @{ Source=(Join-Path $directory 'prepared.toml'); Destination=(Join-Path $directory 'client.toml'); BackupPath=(Join-Path $directory 'before.toml') }
    [IO.File]::WriteAllText($paths.Source, "version=1`narguments=['sub']`n")
    [IO.File]::WriteAllText($paths.Destination, "version=1`narguments=[]`n")
    $paths.ExpectedHash = (Get-FileHash -LiteralPath $paths.Destination -Algorithm SHA256).Hash
    return $paths
}
$f = Fixture 'old-call'
$rejected = $false
try { [IO.File]::Replace($f.Source, $f.Destination, $null) }
catch { $rejected = $_.Exception.InnerException -is [ArgumentException] }
Check 'Previous null backup call reproduced' $rejected
Check 'Rejected old call preserves destination' ((Get-FileHash -LiteralPath $f.Destination).Hash -eq $f.ExpectedHash)
Check 'Rejected old call preserves source' ([IO.File]::Exists($f.Source))

$f = Fixture 'replacement'
$newHash = (Get-FileHash -LiteralPath $f.Source).Hash
Replace-XmqrClientConfig @f
Check 'New configuration installed' ((Get-FileHash -LiteralPath $f.Destination).Hash -eq $newHash)
Check 'Original configuration retained in explicit backup' ((Get-FileHash -LiteralPath $f.BackupPath).Hash -eq $f.ExpectedHash)
Check 'Replacement consumes source atomically' (-not [IO.File]::Exists($f.Source))
# Same recovery operation used by the surrounding initializer catch block.
[IO.File]::Copy($f.BackupPath, $f.Destination, $true)
Check 'Original configuration recoverable after later failure' ((Get-FileHash -LiteralPath $f.Destination).Hash -eq $f.ExpectedHash)

$f = Fixture 'backup-exists'
[IO.File]::WriteAllText($f.BackupPath, 'operator-backup')
$backupHash = (Get-FileHash -LiteralPath $f.BackupPath).Hash
$rejected = $false
try { Replace-XmqrClientConfig @f } catch { $rejected = $true }
Check 'Existing backup refused' $rejected
Check 'Existing backup preserved' ((Get-FileHash -LiteralPath $f.BackupPath).Hash -eq $backupHash)
Check 'Existing-backup refusal preserves destination' ((Get-FileHash -LiteralPath $f.Destination).Hash -eq $f.ExpectedHash)
Check 'Existing-backup refusal preserves prepared source' ([IO.File]::Exists($f.Source))

$f = Fixture 'config-changed'
[IO.File]::WriteAllText($f.Destination, "version=1`narguments=['operator-customization']`n")
$customHash = (Get-FileHash -LiteralPath $f.Destination).Hash
$rejected = $false
try { Replace-XmqrClientConfig @f } catch { $rejected = $true }
Check 'Changed configuration refused' $rejected
Check 'Operator customization preserved' ((Get-FileHash -LiteralPath $f.Destination).Hash -eq $customHash)
Check 'Changed-config refusal preserves source' ([IO.File]::Exists($f.Source))
Check 'Changed-config refusal creates no backup' (-not [IO.File]::Exists($f.BackupPath))

$f = Fixture 'empty-backup'
$f.BackupPath = ''
$rejected = $false
try { Replace-XmqrClientConfig @f } catch { $rejected = $true }
Check 'Empty backup path rejected by parameter guard' $rejected
Check 'Empty-backup refusal preserves destination' ((Get-FileHash -LiteralPath $f.Destination).Hash -eq $f.ExpectedHash)

$f = Fixture 'changed-before-backup'
[IO.File]::WriteAllText($f.Destination, "version=1`narguments=['changed-during-setup']`n")
$lateBackup = Join-Path ([IO.Path]::GetDirectoryName($f.Destination)) 'late-copy.toml'
[IO.File]::Copy($f.Destination, $lateBackup, $false)
$customHash = (Get-FileHash -LiteralPath $lateBackup).Hash
$rejected = $false
try { Replace-XmqrClientConfig @f } catch { $rejected = $true }
Check 'Pinned preflight hash rejects change captured by later backup' $rejected
Check 'Change made during preparation remains intact' ((Get-FileHash -LiteralPath $f.Destination).Hash -eq $customHash)
Check 'Late backup cannot redefine approved hash' ($f.ExpectedHash -ne $customHash)
Write-Output "$passed replacement checks passed; no installed files, credentials, ACLs or services were changed."
