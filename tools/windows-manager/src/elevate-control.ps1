$ErrorActionPreference = 'Stop'
try {
    if ($env:XMQR_CONTROL_ID -notmatch '^[a-zA-Z0-9-]{1,80}$' -or
        $env:XMQR_CONTROL_ACTION -notin @('start','stop','restart')) { exit 2 }
    # All arguments are restricted identifiers, not shell fragments. FilePath
    # is passed as data, even when the installation directory contains spaces.
    $arguments = @('--control', $env:XMQR_CONTROL_ACTION, $env:XMQR_CONTROL_ID)
    $child = Start-Process -FilePath $env:XMQR_CONTROL_HELPER -ArgumentList $arguments -Verb RunAs -WindowStyle Hidden -PassThru
    if (-not $child.WaitForExit(45000)) { exit 124 }
    exit $child.ExitCode
} catch {
    exit 1223
}
