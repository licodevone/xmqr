# SPDX-License-Identifier: MIT
# VM-only SCM acceptance for one independently packaged client or admin binary.
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet('client', 'admin')]
    [string] $Component,
    [Parameter(Mandatory)]
    [string] $Executable,
    [Parameter(Mandatory)]
    [string] $Config,
    [Parameter(Mandatory)]
    [switch] $DisposableVmAcceptance,
    [string] $AdminTokenFile,
    [string] $AdminStatusUrl = 'http://127.0.0.1:9080/api/status',
    [ValidateRange(10, 180)]
    [int] $TimeoutSeconds = 45
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Assert-Preconditions {
    if (-not $DisposableVmAcceptance) {
        throw 'Pass -DisposableVmAcceptance only from a disposable Windows VM. This script creates and removes one fixed XMQR service.'
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

    $exe = (Resolve-Path -LiteralPath $Executable).Path
    $configPath = (Resolve-Path -LiteralPath $Config).Path
    if (-not (Test-Path -LiteralPath $exe -PathType Leaf) -or
        -not (Test-Path -LiteralPath $configPath -PathType Leaf) -or
        -not [IO.Path]::IsPathFullyQualified($configPath)) {
        throw 'Provide an existing executable and an absolute, provisioned service config file.'
    }
    if ($Component -eq 'admin') {
        if (-not $AdminTokenFile -or -not [IO.Path]::IsPathFullyQualified($AdminTokenFile) -or
            -not (Test-Path -LiteralPath $AdminTokenFile -PathType Leaf)) {
            throw 'Admin acceptance requires the existing absolute private token file used by the config.'
        }
        $uri = [Uri]$AdminStatusUrl
        if ($uri.Scheme -ne 'http' -or $uri.Host -notin @('127.0.0.1', 'localhost') -or
            $uri.AbsolutePath -ne '/api/status' -or $uri.Query -or $uri.UserInfo) {
            throw 'Admin status probe must be an HTTP loopback URL ending in /api/status.'
        }
    }

    $serviceName = if ($Component -eq 'client') { 'xmqr-client-default' } else { 'xmqr-admin' }
    if ($null -ne (Get-Service -Name $serviceName -ErrorAction SilentlyContinue)) {
        throw "Service $serviceName already exists. This runner never stops, changes, or removes an existing service."
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
                    $displayName.Value -ieq "XMQR $Component") {
                    throw "An XMQR $Component MSI is registered. Use a clean VM without this component installed."
                }
            }
        }
    }
    return [pscustomobject]@{ Executable = $exe; Config = $configPath; VmSignature = $vmSignature; ServiceName = $serviceName }
}

function Set-ProtectedDirectoryAcl([string] $Path, [bool] $ServiceModify) {
    $security = [System.Security.AccessControl.DirectorySecurity]::new()
    $security.SetAccessRuleProtection($true, $false)
    $inherit = [System.Security.AccessControl.InheritanceFlags]::ContainerInherit -bor
        [System.Security.AccessControl.InheritanceFlags]::ObjectInherit
    $allow = [System.Security.AccessControl.AccessControlType]::Allow
    foreach ($sid in @('S-1-5-18', 'S-1-5-32-544')) {
        $rule = [System.Security.AccessControl.FileSystemAccessRule]::new(
            [System.Security.Principal.SecurityIdentifier]::new($sid),
            [System.Security.AccessControl.FileSystemRights]::FullControl, $inherit,
            [System.Security.AccessControl.PropagationFlags]::None, $allow)
        $security.AddAccessRule($rule)
    }
    $rights = if ($ServiceModify) {
        [System.Security.AccessControl.FileSystemRights]::Modify
    } else {
        [System.Security.AccessControl.FileSystemRights]::ReadAndExecute
    }
    $rule = [System.Security.AccessControl.FileSystemAccessRule]::new(
        [System.Security.Principal.SecurityIdentifier]::new('S-1-5-19'), $rights, $inherit,
        [System.Security.AccessControl.PropagationFlags]::None, $allow)
    $security.AddAccessRule($rule)
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

function Wait-ServiceState([string] $Expected, [int] $Seconds, [string] $Name) {
    $deadline = [DateTime]::UtcNow.AddSeconds($Seconds)
    do {
        $service = Get-Service -Name $Name -ErrorAction SilentlyContinue
        if ($null -eq $service) { throw "The test service $Name disappeared before reaching state $Expected." }
        if ($service.Status.ToString() -eq $Expected) { return }
        Start-Sleep -Milliseconds 250
    } while ([DateTime]::UtcNow -lt $deadline)
    $current = (Get-Service -Name $Name -ErrorAction SilentlyContinue).Status
    throw "Timed out waiting for $Name state $Expected (last state: $current)."
}

function Wait-ServiceAbsent([int] $Seconds, [string] $Name) {
    $deadline = [DateTime]::UtcNow.AddSeconds($Seconds)
    do {
        if ($null -eq (Get-Service -Name $Name -ErrorAction SilentlyContinue)) { return $true }
        Start-Sleep -Milliseconds 250
    } while ([DateTime]::UtcNow -lt $deadline)
    return $false
}

function Wait-OwnedProcessExit([string] $ImagePath, [int] $Seconds) {
    $deadline = [DateTime]::UtcNow.AddSeconds($Seconds)
    $imageName = [IO.Path]::GetFileName($ImagePath)
    do {
        try {
            $process = Get-CimInstance -ClassName Win32_Process -Filter "Name='$imageName'" -ErrorAction Stop |
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
        $leaf -notmatch '^xmqr-component-scm-[0-9a-f]{32}$') {
        throw "Refusing cleanup outside this run's generated temporary directory: $fullPath"
    }
    return $fullPath
}

function Test-LogLifecycle([string] $Path, [string] $Message) {
    if (-not (Test-Path -LiteralPath $Path)) { throw "Service lifecycle log was not created: $Path" }
    $lines = Get-Content -LiteralPath $Path
    if (-not ($lines | Where-Object { $_ -match "\s$([regex]::Escape($Message))$" })) {
        throw "Service log does not contain lifecycle event '$Message'."
    }
}

function Test-AdminStatus([string] $Url, [string] $TokenPath) {
    $http = [Net.Http.HttpClient]::new()
    $http.Timeout = [TimeSpan]::FromSeconds(5)
    try {
        $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
        do {
            try {
                $unauthenticated = $http.GetAsync($Url).GetAwaiter().GetResult()
                break
            } catch {
                if ([DateTime]::UtcNow -ge $deadline) { throw }
                Start-Sleep -Milliseconds 250
            }
        } while ([DateTime]::UtcNow -lt $deadline)
        if ([int]$unauthenticated.StatusCode -ne 401) {
            throw "Admin status without credentials returned HTTP $([int]$unauthenticated.StatusCode), expected 401."
        }
        $token = [IO.File]::ReadAllText($TokenPath).Trim()
        if (-not $token) { throw 'The configured admin token file is empty.' }
        $http.DefaultRequestHeaders.Authorization = [Net.Http.Headers.AuthenticationHeaderValue]::new('Bearer', $token)
        $authenticated = $http.GetAsync($Url).GetAwaiter().GetResult()
        if ([int]$authenticated.StatusCode -ne 200) {
            throw "Admin status with its configured bearer token returned HTTP $([int]$authenticated.StatusCode), expected 200."
        }
        return [ordered]@{ unauthenticated_status = 401; authenticated_status = 200 }
    } finally {
        $http.Dispose()
    }
}

$preconditions = Assert-Preconditions
$exe = $preconditions.Executable
$configPath = $preconditions.Config
$serviceName = $preconditions.ServiceName
$markerText = & $exe '--windows-service-capabilities'
if ($LASTEXITCODE -ne 0) { throw 'The supplied executable rejected the Windows service capability probe.' }
$marker = ($markerText | Out-String | ConvertFrom-Json)
if ($marker.schema -ne 1 -or $marker.component -ne $Component -or $marker.service_entrypoint -ne $true) {
    throw "The supplied executable does not have the $Component Windows service entrypoint."
}

$runId = [Guid]::NewGuid().ToString('N')
$tempRoot = Join-Path ([IO.Path]::GetTempPath()) "xmqr-component-scm-$runId"
$evidenceRoot = Join-Path ([IO.Path]::GetTempPath()) "xmqr-component-scm-evidence-$runId"
$serviceCreated = $false
$serviceBinaryPath = $null
$cleanupComplete = $true
$failureMessage = $null
$events = [Collections.Generic.List[object]]::new()
$startedAt = [DateTime]::UtcNow
$adminProbe = $null

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

    $testExecutable = Join-Path $bin ([IO.Path]::GetFileName($exe))
    Copy-Item -LiteralPath $exe -Destination $testExecutable
    $sourceHash = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash
    $copyHash = (Get-FileHash -LiteralPath $testExecutable -Algorithm SHA256).Hash
    if ($sourceHash -ne $copyHash) { throw 'The isolated test executable copy failed its SHA-256 check.' }

    $serviceBinaryPath = '"{0}" --windows-service {1} "{2}" --config "{3}"' -f `
        $testExecutable, $serviceName, $logs, $configPath
    $createOutput = Invoke-Sc -Arguments @('create', $serviceName, 'binPath=', $serviceBinaryPath,
        'start=', 'demand', 'obj=', 'NT AUTHORITY\LocalService',
        'DisplayName=', "XMQR Disposable $Component SCM Acceptance")
    $serviceCreated = $true
    $cleanupComplete = $false
    $events.Add([ordered]@{ event = 'created'; utc = [DateTime]::UtcNow.ToString('o'); details = ($createOutput -join ' ') })

    $service = Get-CimInstance -ClassName Win32_Service -Filter "Name='$serviceName'"
    if ($service.StartName -notin @('NT AUTHORITY\LocalService', '.\LocalService')) {
        throw "Service account is not LocalService (reported: $($service.StartName))."
    }
    if (-not (Test-OwnedServicePath -Actual $service.PathName -Expected $serviceBinaryPath)) {
        throw 'SCM registered an unexpected service command line.'
    }
    $scQuery = Invoke-Sc -Arguments @('qc', $serviceName)
    $events.Add([ordered]@{ event = 'registered'; utc = [DateTime]::UtcNow.ToString('o'); details = ($scQuery -join "`n") })

    foreach ($cycle in 1..2) {
        Start-Service -Name $serviceName
        Wait-ServiceState -Expected 'Running' -Seconds $TimeoutSeconds -Name $serviceName
        $events.Add([ordered]@{ event = "running-$cycle"; utc = [DateTime]::UtcNow.ToString('o') })
        if ($Component -eq 'admin') {
            $adminProbe = Test-AdminStatus -Url $AdminStatusUrl -TokenPath $AdminTokenFile
        }
        Stop-Service -Name $serviceName
        Wait-ServiceState -Expected 'Stopped' -Seconds $TimeoutSeconds -Name $serviceName
        $service = Get-CimInstance -ClassName Win32_Service -Filter "Name='$serviceName'" -ErrorAction Stop
        if ($null -eq $service -or $service.State -ne 'Stopped' -or
            $service.ExitCode -ne 0 -or $service.ServiceSpecificExitCode -ne 0) {
            throw "SCM did not report a successful stopped $Component service."
        }
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
        $service = Get-CimInstance -ClassName Win32_Service -Filter "Name='$serviceName'" -ErrorAction Stop
    } catch {
        $service = $null
        $serviceQuerySucceeded = $false
        if ($serviceCreated) { Write-Warning "Could not confirm service identity during cleanup; preserving test files: $_" }
    }
    if ($serviceCreated -and $null -ne $service -and
        (Test-OwnedServicePath -Actual $service.PathName -Expected $serviceBinaryPath)) {
        if ($service.State -ne 'Stopped') {
            try {
                Stop-Service -Name $serviceName -ErrorAction Stop
                Wait-ServiceState -Expected 'Stopped' -Seconds $TimeoutSeconds -Name $serviceName
            } catch {
                Write-Warning "Own test service could not be stopped cooperatively; leaving the test root and service intact: $_"
            }
        }
        try {
            $service = Get-CimInstance -ClassName Win32_Service -Filter "Name='$serviceName'" -ErrorAction Stop
        } catch {
            $service = $null
            $serviceQuerySucceeded = $false
            Write-Warning "Could not confirm service state during cleanup; preserving test files: $_"
        }
        if ($null -ne $service -and
            (Test-OwnedServicePath -Actual $service.PathName -Expected $serviceBinaryPath) -and
            $service.State -eq 'Stopped') {
            try {
                $null = Invoke-Sc -Arguments @('delete', $serviceName)
                $cleanupComplete = (Wait-ServiceAbsent -Seconds 15 -Name $serviceName) -and
                    (Wait-OwnedProcessExit -ImagePath (Join-Path (Join-Path $tempRoot 'bin') ([IO.Path]::GetFileName($exe))) -Seconds 15)
                if (-not $cleanupComplete) { Write-Warning 'SCM still reports the deleted test service; preserving its files.' }
            } catch {
                Write-Warning "Could not delete the owned test service; leaving the test root intact: $_"
            }
        }
    } elseif ($serviceCreated -and $null -ne $service) {
        Write-Warning 'Service identity changed; preserving it and its files without cleanup.'
    } elseif ($serviceCreated -and $serviceQuerySucceeded) {
        $cleanupComplete = Wait-OwnedProcessExit -ImagePath (Join-Path (Join-Path $tempRoot 'bin') ([IO.Path]::GetFileName($exe))) -Seconds 15
    }

    if (Test-Path -LiteralPath $tempRoot) {
        $logsPath = Join-Path $tempRoot 'logs\service.log'
        if (Test-Path -LiteralPath $logsPath) {
            Copy-Item -LiteralPath $logsPath -Destination (Join-Path $evidenceRoot 'service.log') -ErrorAction SilentlyContinue
        }
        $report = [ordered]@{
            schema = 1; result = if ($cleanupComplete -and @($events | Where-Object { $_.event -eq 'passed' }).Count -gt 0) { 'PASS' } else { 'FAIL' }
            component = $Component; started_utc = $startedAt.ToString('o'); finished_utc = [DateTime]::UtcNow.ToString('o')
            executable = $exe; executable_sha256 = if (Test-Path -LiteralPath $exe) { (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant() } else { $null }
            vm = $preconditions.VmSignature; service_name = $serviceName; cleanup_complete = $cleanupComplete
            admin_status = $adminProbe; failure = $failureMessage; temporary_root = $tempRoot; events = @($events)
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
    throw "The test service could not be safely removed; inspect the preserved temporary root: $tempRoot"
}
