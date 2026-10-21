$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$name = $env:XMQR_SERVICE_NAME
$action = $env:XMQR_SERVICE_ACTION
if ($name -notmatch '^xmqr-[a-zA-Z0-9-]{1,75}$' -or $action -notin @('start','stop','restart')) { exit 2 }
try {
    # Confirm that the registered product and SCM refer to the same executable.
    $record = Get-CimInstance -ClassName Win32_Service -Filter "Name='$name'" -ErrorAction Stop
    if ($null -eq $record) { exit 3 }
    $command = $record.PathName.Trim()
    if ($command.StartsWith('"')) {
        $end = $command.IndexOf('"', 1)
        if ($end -lt 2) { exit 3 }
        $binary = $command.Substring(1, $end-1)
    } else {
        $binary = ($command -split '\s+',2)[0]
    }
    if (-not [string]::Equals($binary,$env:XMQR_SERVICE_EXECUTABLE,[StringComparison]::OrdinalIgnoreCase)) { exit 3 }
    $service = Get-Service -Name $name -ErrorAction Stop
    $deadline = [DateTime]::UtcNow.AddSeconds(30)
    function Wait-State([string] $wanted) {
        do {
            $service.Refresh()
            if ($service.Status.ToString() -eq $wanted) { return }
            if ([DateTime]::UtcNow -ge $deadline) { throw [TimeoutException]::new() }
            Start-Sleep -Milliseconds 150
        } while ($true)
    }
    if ($action -in @('stop','restart')) {
        # Do not stop unrelated dependent services or force termination.
        if (@($service.DependentServices | Where-Object { $_.Status -ne 'Stopped' }).Count -gt 0) { exit 6 }
        $service.Refresh()
        if ($service.Status -eq 'Running') { $service.Stop() }
        elseif ($service.Status -ne 'Stopped') { exit 7 }
        Wait-State 'Stopped'
    }
    if ($action -in @('start','restart')) {
        $service.Refresh()
        if ($service.Status -eq 'Stopped') { $service.Start() }
        elseif ($service.Status -ne 'Running') { exit 7 }
        Wait-State 'Running'
    }
    exit 0
} catch {
    $errorObject = $_.Exception
    while ($null -ne $errorObject) {
        if ($errorObject -is [ComponentModel.Win32Exception] -and $errorObject.NativeErrorCode -eq 5) { exit 5 }
        if ($errorObject -is [UnauthorizedAccessException]) { exit 5 }
        if ($errorObject -is [TimeoutException]) { exit 124 }
        $errorObject = $errorObject.InnerException
    }
    exit 1
}
