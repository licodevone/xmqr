$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$registrations = $env:XMQR_SERVICE_NAMES | ConvertFrom-Json
if ($null -eq $registrations -or @($registrations).Count -eq 0) { Write-Output '[]'; exit 0 }
$result = @(
    foreach ($registration in @($registrations)) {
        $name = $registration.Name
        if ($name -notmatch '^xmqr-[a-zA-Z0-9-]{1,75}$') { throw 'Invalid service name' }
        try {
            $service = Get-CimInstance -ClassName Win32_Service -Filter "Name='$name'" -ErrorAction Stop
            if ($null -eq $service) {
                @{ Name=$name; State='Missing'; ExitCode=0; Matches=$false; Error=$null }
            } else {
                $command = $service.PathName.Trim()
                $binary = ''
                if ($command.StartsWith('"')) {
                    $end = $command.IndexOf('"', 1)
                    if ($end -gt 1) { $binary = $command.Substring(1, $end-1) }
                } else { $binary = ($command -split '\s+',2)[0] }
                $matches = [string]::Equals($binary,$registration.Executable,[StringComparison]::OrdinalIgnoreCase)
                @{ Name=$name; State=$service.State; ExitCode=[uint32]$service.ExitCode; Matches=$matches; Error=$null }
            }
        } catch {
            @{ Name=$name; State='Unknown'; ExitCode=0; Matches=$false; Error='Consulta do serviço indisponível' }
        }
    }
)
ConvertTo-Json -InputObject $result -Compress -Depth 3
