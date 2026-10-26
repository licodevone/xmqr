$ErrorActionPreference = 'Stop'
try {
    if ($env:XMQR_OPEN_ID -notmatch '^[a-zA-Z0-9-]{1,80}$' -or
        $env:XMQR_OPEN_TARGET -notin @('config','config-dir','certificates','logs')) { exit 2 }
    # No paths from user input cross the boundary. The helper rereads HKLM.
    $arguments = @('--open', $env:XMQR_OPEN_TARGET, $env:XMQR_OPEN_ID)
    $child = Start-Process -FilePath $env:XMQR_OPEN_HELPER -ArgumentList $arguments -Verb RunAs -WindowStyle Hidden -PassThru
    if (-not $child.WaitForExit(45000)) { exit 124 }
    exit $child.ExitCode
} catch {
    exit 1223
}
