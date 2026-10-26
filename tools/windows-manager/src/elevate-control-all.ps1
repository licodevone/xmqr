$ErrorActionPreference = 'Stop'
try {
    if ($env:XMQR_CONTROL_ACTION -notin @('start','stop','restart')) { exit 2 }
    $arguments = @('--control-all', $env:XMQR_CONTROL_ACTION)
    $child = Start-Process -FilePath $env:XMQR_CONTROL_HELPER -ArgumentList $arguments -Verb RunAs -WindowStyle Hidden -PassThru
    # Bound the worst case for up to 64 registered services (stop then start).
    # The UI remains responsive; no service or helper is forcibly terminated.
    if (-not $child.WaitForExit(4500000)) { exit 124 }
    exit $child.ExitCode
} catch {
    exit 1223
}
