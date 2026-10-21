# SPDX-License-Identifier: MIT
# VM-only destructive acceptance: creates/removes the fixed xmqr-broker service.
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string] $BrokerExecutable,
    [Parameter(Mandatory)]
    [switch] $DisposableVmAcceptance,
    [ValidateRange(10, 180)]
    [int] $TimeoutSeconds = 45
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Assert-Preconditions {
    if (-not $DisposableVmAcceptance) {
        throw 'Pass -DisposableVmAcceptance only from a disposable Windows VM. This script creates and removes the fixed xmqr-broker service.'
    }
    if (-not $IsWindows -or -not [Environment]::Is64BitOperatingSystem -or -not [Environment]::Is64BitProcess) {
        throw 'This acceptance runner requires 64-bit Windows and 64-bit PowerShell 7.'
    }
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Run this script from an elevated PowerShell session inside the disposable VM.'
    }
    $computer = Get-CimInstance -ClassName Win32_ComputerSystem
    $vmSignature = "$($computer.Manufacturer) $($computer.Model)"
    if ($vmSignature -notmatch '(?i)virtual|vmware|virtualbox|qemu|kvm|xen|parallels|amazon ec2|google') {
        throw "The host does not identify as a VM ($vmSignature). Refusing to create a service."
    }

    $exe = (Resolve-Path -LiteralPath $BrokerExecutable).Path
    if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) { throw "Broker executable not found: $BrokerExecutable" }

    $existingService = Get-Service -Name 'xmqr-broker' -ErrorAction SilentlyContinue
    if ($null -ne $existingService) {
        throw 'Service xmqr-broker already exists. This runner never stops, changes, or removes an existing service.'
    }
    foreach ($subkey in @(
        'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall',
        'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall'
    )) {
        $keyPath = "Registry::HKEY_LOCAL_MACHINE\$subkey"
        if (Test-Path -LiteralPath $keyPath) {
            foreach ($entry in Get-ChildItem -LiteralPath $keyPath -ErrorAction SilentlyContinue) {
                $product = Get-ItemProperty -LiteralPath $entry.PSPath -ErrorAction SilentlyContinue
                $displayName = $product.PSObject.Properties['DisplayName']
                if ($null -ne $displayName -and $displayName.Value -is [string] -and
                    $displayName.Value -ieq 'XMQR Broker') {
                    throw 'An XMQR Broker MSI is registered. Use a clean VM without the broker component installed.'
                }
            }
        }
    }
    return [pscustomobject]@{ Executable = $exe; VmSignature = $vmSignature }
}

function Set-ProtectedDirectoryAcl([string] $Path, [bool] $ServiceModify) {
    $security = [System.Security.AccessControl.DirectorySecurity]::new()
    $security.SetAccessRuleProtection($true, $false)
    $inherit = [System.Security.AccessControl.InheritanceFlags]::ContainerInherit -bor
        [System.Security.AccessControl.InheritanceFlags]::ObjectInherit
    $propagation = [System.Security.AccessControl.PropagationFlags]::None
    $allow = [System.Security.AccessControl.AccessControlType]::Allow
    foreach ($sid in @('S-1-5-18', 'S-1-5-32-544')) {
        $rule = [System.Security.AccessControl.FileSystemAccessRule]::new(
            [System.Security.Principal.SecurityIdentifier]::new($sid),
            [System.Security.AccessControl.FileSystemRights]::FullControl,
            $inherit, $propagation, $allow)
        $security.AddAccessRule($rule)
    }
    $serviceRights = if ($ServiceModify) {
        [System.Security.AccessControl.FileSystemRights]::Modify
    } else {
        [System.Security.AccessControl.FileSystemRights]::ReadAndExecute
    }
    $serviceRule = [System.Security.AccessControl.FileSystemAccessRule]::new(
        [System.Security.Principal.SecurityIdentifier]::new('S-1-5-19'),
        $serviceRights, $inherit, $propagation, $allow)
    $security.AddAccessRule($serviceRule)
    Set-Acl -LiteralPath $Path -AclObject $security
}

function Invoke-Sc([string[]] $Arguments) {
    $result = & sc.exe @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) { throw "sc.exe $($Arguments -join ' ') failed ($LASTEXITCODE): $result" }
    return $result
}

function Test-OwnedServicePath([string] $Actual, [string] $Expected) {
    return [string]::Equals($Actual.Trim(), $Expected, [StringComparison]::OrdinalIgnoreCase)
}

function Wait-ServiceState([string] $Expected, [int] $Seconds) {
    $deadline = [DateTime]::UtcNow.AddSeconds($Seconds)
    do {
        $service = Get-Service -Name 'xmqr-broker' -ErrorAction SilentlyContinue
        if ($null -eq $service) { throw 'The test service disappeared before reaching the expected state.' }
        if ($service.Status.ToString() -eq $Expected) { return }
        Start-Sleep -Milliseconds 250
    } while ([DateTime]::UtcNow -lt $deadline)
    $current = (Get-Service -Name 'xmqr-broker' -ErrorAction SilentlyContinue).Status
    throw "Timed out waiting for xmqr-broker state $Expected (last state: $current)."
}

function Wait-ServiceAbsent([int] $Seconds) {
    $deadline = [DateTime]::UtcNow.AddSeconds($Seconds)
    do {
        if ($null -eq (Get-Service -Name 'xmqr-broker' -ErrorAction SilentlyContinue)) { return $true }
        Start-Sleep -Milliseconds 250
    } while ([DateTime]::UtcNow -lt $deadline)
    return $false
}

function Wait-OwnedProcessExit([string] $ImagePath, [int] $Seconds) {
    $deadline = [DateTime]::UtcNow.AddSeconds($Seconds)
    do {
        try {
            $process = Get-CimInstance -ClassName Win32_Process -Filter "Name='mqtt-broker.exe'" -ErrorAction Stop |
                Where-Object { $_.ExecutablePath -ieq $ImagePath }
        } catch {
            Write-Warning "Could not confirm the test process exited: $_"
            return $false
        }
        if ($null -eq $process) { return $true }
        Start-Sleep -Milliseconds 250
    } while ([DateTime]::UtcNow -lt $deadline)
    return $false
}

function Assert-OwnedTempRoot([string] $Path) {
    $tempBase = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\', '/')
    $fullPath = [IO.Path]::GetFullPath($Path)
    $parent = [IO.Path]::GetDirectoryName($fullPath).TrimEnd('\', '/')
    $leaf = [IO.Path]::GetFileName($fullPath)
    if (-not [string]::Equals($parent, $tempBase, [StringComparison]::OrdinalIgnoreCase) -or
        $leaf -notmatch '^xmqr-broker-scm-[0-9a-f]{32}$') {
        throw "Refusing cleanup outside this run's generated temporary directory: $fullPath"
    }
    return $fullPath
}

function Wait-LoopbackListener([int] $Port, [int] $Seconds) {
    $deadline = [DateTime]::UtcNow.AddSeconds($Seconds)
    do {
        $client = [Net.Sockets.TcpClient]::new()
        try {
            $connect = $client.ConnectAsync([Net.IPAddress]::Loopback, $Port)
            if ($connect.Wait([TimeSpan]::FromMilliseconds(750)) -and $client.Connected) { return }
        } catch {
            # The broker may still be opening its listener. Retry until the bound expires.
        } finally {
            $client.Dispose()
        }
        Start-Sleep -Milliseconds 250
    } while ([DateTime]::UtcNow -lt $deadline)
    throw "Broker did not accept a loopback TCP connection on 127.0.0.1:$Port."
}

function Test-LogLifecycle([string] $Path, [string] $Message) {
    if (-not (Test-Path -LiteralPath $Path)) { throw "Service lifecycle log was not created: $Path" }
    $lines = Get-Content -LiteralPath $Path
    if (-not ($lines | Where-Object { $_ -match "\s$([regex]::Escape($Message))$" })) {
        throw "Service log does not contain lifecycle event '$Message'."
    }
}

function Assert-ServiceSuccessfulExit {
    $service = Get-CimInstance -ClassName Win32_Service -Filter "Name='xmqr-broker'" -ErrorAction Stop
    if ($null -eq $service -or $service.State -ne 'Stopped' -or
        $service.ExitCode -ne 0 -or $service.ServiceSpecificExitCode -ne 0) {
        throw "SCM did not report a successful stopped service (state=$($service.State), exit=$($service.ExitCode), specific=$($service.ServiceSpecificExitCode))."
    }
}

$preconditions = Assert-Preconditions
$executable = $preconditions.Executable
$vmSignature = $preconditions.VmSignature
$markerText = & $executable '--windows-service-capabilities'
if ($LASTEXITCODE -ne 0) { throw 'The supplied executable rejected the Windows service capability probe.' }
$marker = ($markerText | Out-String | ConvertFrom-Json)
if ($marker.schema -ne 1 -or $marker.component -ne 'broker' -or $marker.service_entrypoint -ne $true) {
    throw 'The supplied executable does not have the broker Windows service entrypoint.'
}

$runId = [Guid]::NewGuid().ToString('N')
$tempRoot = Join-Path ([IO.Path]::GetTempPath()) "xmqr-broker-scm-$runId"
$evidenceRoot = Join-Path ([IO.Path]::GetTempPath()) "xmqr-broker-scm-evidence-$runId"
$serviceCreated = $false
$serviceBinaryPath = $null
$cleanupComplete = $true
$failureMessage = $null
$port = $null
$events = [Collections.Generic.List[object]]::new()
$startedAt = [DateTime]::UtcNow

try {
    $null = New-Item -ItemType Directory -Path $tempRoot
    $null = New-Item -ItemType Directory -Path $evidenceRoot
    $bin = Join-Path $tempRoot 'bin'
    $logs = Join-Path $tempRoot 'logs'
    $state = Join-Path $tempRoot 'state'
    foreach ($directory in @($bin, $logs, $state)) { $null = New-Item -ItemType Directory -Path $directory }
    Set-ProtectedDirectoryAcl -Path $tempRoot -ServiceModify $false
    Set-ProtectedDirectoryAcl -Path $bin -ServiceModify $false
    Set-ProtectedDirectoryAcl -Path $logs -ServiceModify $true
    Set-ProtectedDirectoryAcl -Path $state -ServiceModify $true

    $testExecutable = Join-Path $bin 'mqtt-broker.exe'
    Copy-Item -LiteralPath $executable -Destination $testExecutable
    $sourceHash = (Get-FileHash -LiteralPath $executable -Algorithm SHA256).Hash
    $copyHash = (Get-FileHash -LiteralPath $testExecutable -Algorithm SHA256).Hash
    if ($sourceHash -ne $copyHash) { throw 'The isolated test executable copy failed its SHA-256 check.' }

    $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, 0)
    $listener.Start()
    $port = ([Net.IPEndPoint]$listener.LocalEndpoint).Port
    $listener.Stop()
    $config = Join-Path $tempRoot 'broker.toml'
    @"
version = 1

[broker]
mode = "open-lab"
bind = "127.0.0.1:$port"
state_dir = "state"

[monitor]
enabled = false
"@ | Set-Content -LiteralPath $config -Encoding utf8NoBOM

    $serviceBinaryPath = '"{0}" --windows-service xmqr-broker "{1}" --config "{2}"' -f `
        $testExecutable, $logs, $config
    $createOutput = Invoke-Sc -Arguments @('create', 'xmqr-broker', 'binPath=', $serviceBinaryPath,
        'start=', 'demand', 'obj=', 'NT AUTHORITY\LocalService',
        'DisplayName=', 'XMQR Disposable SCM Acceptance')
    $serviceCreated = $true
    $cleanupComplete = $false
    $events.Add([ordered]@{ event = 'created'; utc = [DateTime]::UtcNow.ToString('o'); details = ($createOutput -join ' ') })

    $service = Get-CimInstance -ClassName Win32_Service -Filter "Name='xmqr-broker'"
    if ($service.StartName -notin @('NT AUTHORITY\LocalService', '.\LocalService')) {
        throw "Service account is not LocalService (reported: $($service.StartName))."
    }
    if (-not (Test-OwnedServicePath -Actual $service.PathName -Expected $serviceBinaryPath)) {
        throw 'SCM registered an unexpected service command line.'
    }
    $scQuery = Invoke-Sc -Arguments @('qc', 'xmqr-broker')
    $events.Add([ordered]@{ event = 'registered'; utc = [DateTime]::UtcNow.ToString('o'); details = ($scQuery -join "`n") })

    foreach ($cycle in 1..2) {
        Start-Service -Name 'xmqr-broker'
        Wait-ServiceState -Expected 'Running' -Seconds $TimeoutSeconds
        Wait-LoopbackListener -Port $port -Seconds $TimeoutSeconds
        $events.Add([ordered]@{ event = "running-$cycle"; utc = [DateTime]::UtcNow.ToString('o'); port = $port })
        Stop-Service -Name 'xmqr-broker'
        Wait-ServiceState -Expected 'Stopped' -Seconds $TimeoutSeconds
        Assert-ServiceSuccessfulExit
        Test-LogLifecycle -Path (Join-Path $logs 'service.log') -Message 'running'
        Test-LogLifecycle -Path (Join-Path $logs 'service.log') -Message 'stopped'
        if (Select-String -LiteralPath (Join-Path $logs 'service.log') -Pattern '\sfailure:|\sfailed:' -Quiet) {
            throw 'The service log contains an application failure event.'
        }
        $events.Add([ordered]@{ event = "stopped-$cycle"; utc = [DateTime]::UtcNow.ToString('o') })
    }
    $events.Add([ordered]@{ event = 'passed'; utc = [DateTime]::UtcNow.ToString('o') })
} catch {
    $failureMessage = $_.Exception.Message
    throw
} finally {
    $serviceQuerySucceeded = $true
    try {
        $service = Get-CimInstance -ClassName Win32_Service -Filter "Name='xmqr-broker'" -ErrorAction Stop
    } catch {
        $service = $null
        $serviceQuerySucceeded = $false
        if ($serviceCreated) { Write-Warning "Could not confirm service identity during cleanup; preserving test files: $_" }
    }
    if ($serviceCreated -and $null -ne $service -and
        (Test-OwnedServicePath -Actual $service.PathName -Expected $serviceBinaryPath)) {
        if ($service.State -ne 'Stopped') {
            try {
                Stop-Service -Name 'xmqr-broker' -ErrorAction Stop
                Wait-ServiceState -Expected 'Stopped' -Seconds $TimeoutSeconds
            } catch {
                Write-Warning "Own test service could not be stopped cooperatively; leaving the test root and service intact: $_"
            }
        }
        try {
            $service = Get-CimInstance -ClassName Win32_Service -Filter "Name='xmqr-broker'" -ErrorAction Stop
        } catch {
            $service = $null
            $serviceQuerySucceeded = $false
            Write-Warning "Could not confirm service state during cleanup; preserving test files: $_"
        }
        if ($null -ne $service -and
            (Test-OwnedServicePath -Actual $service.PathName -Expected $serviceBinaryPath) -and
            $service.State -eq 'Stopped') {
            try {
                $null = Invoke-Sc -Arguments @('delete', 'xmqr-broker')
                $cleanupComplete = (Wait-ServiceAbsent -Seconds 15) -and
                    (Wait-OwnedProcessExit -ImagePath (Join-Path $tempRoot 'bin\mqtt-broker.exe') -Seconds 15)
                if (-not $cleanupComplete) {
                    Write-Warning 'SCM still reports the deleted test service; preserving its files.'
                }
            } catch {
                Write-Warning "Could not delete the owned test service; leaving the test root intact: $_"
            }
        }
    } elseif ($serviceCreated -and $null -ne $service) {
        Write-Warning 'Service identity changed; preserving it and its files without cleanup.'
    } elseif ($serviceCreated -and $serviceQuerySucceeded) {
        $cleanupComplete = Wait-OwnedProcessExit -ImagePath (Join-Path $tempRoot 'bin\mqtt-broker.exe') -Seconds 15
    }

    if (Test-Path -LiteralPath $tempRoot) {
        $logsPath = Join-Path $tempRoot 'logs\service.log'
        if (Test-Path -LiteralPath $logsPath) {
            Copy-Item -LiteralPath $logsPath -Destination (Join-Path $evidenceRoot 'service.log') -ErrorAction SilentlyContinue
        }
        $report = [ordered]@{
            schema = 1; result = if ($cleanupComplete -and @($events | Where-Object { $_.event -eq 'passed' }).Count -gt 0) { 'PASS' } else { 'FAIL' }
            started_utc = $startedAt.ToString('o'); finished_utc = [DateTime]::UtcNow.ToString('o')
            executable = $executable; executable_sha256 = if (Test-Path -LiteralPath $executable) { (Get-FileHash -LiteralPath $executable -Algorithm SHA256).Hash.ToLowerInvariant() } else { $null }
            vm = $vmSignature
            service_name = 'xmqr-broker'; listener = if ($port) { "127.0.0.1:$port" } else { $null }
            cleanup_complete = $cleanupComplete; failure = $failureMessage; temporary_root = $tempRoot; events = @($events)
        }
        $report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $evidenceRoot 'report.json') -Encoding utf8NoBOM
        if ($cleanupComplete) {
            $safeTempRoot = Assert-OwnedTempRoot -Path $tempRoot
            Remove-Item -LiteralPath $safeTempRoot -Recurse -Force
        } else {
            Write-Warning "Acceptance temp root retained for safe manual recovery: $tempRoot"
        }
    }
    Write-Output "Acceptance evidence: $evidenceRoot"
}
if (-not $cleanupComplete) {
    throw "The test service or its process could not be safely removed; inspect the preserved temporary root: $tempRoot"
}
