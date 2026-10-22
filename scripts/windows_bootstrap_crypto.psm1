#requires -Version 7.5
# SPDX-License-Identifier: MIT
# Local bootstrap credentials only: no certificate-store or service mutations.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Assert-XmqrPrivateStagingDirectory([string] $Path) {
    if (-not $IsWindows -or -not [Environment]::Is64BitProcess) {
        throw 'Credential preparation requires Windows and PowerShell 64-bit.'
    }
    if (-not [IO.Path]::IsPathFullyQualified($Path) -or $Path -notmatch '^[A-Za-z]:\\' -or $Path.Substring(2).Contains(':')) {
        throw 'StagingDirectory must be an explicit local drive directory.'
    }
    $root = [IO.Path]::GetFullPath($Path)
    $item = Get-Item -LiteralPath $root -Force
    if (-not $item.PSIsContainer) { throw 'StagingDirectory must already exist as a directory.' }
    $cursor = $item
    while ($null -ne $cursor) {
        if (($cursor.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw 'Reparse points are not accepted in the staging directory path.'
        }
        $cursor = $cursor.Parent
    }
    if (@(Get-ChildItem -LiteralPath $root -Force).Count -ne 0) {
        throw 'StagingDirectory must be empty; existing credentials are never overwritten.'
    }
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    try { $currentSid = $identity.User.Value } finally { $identity.Dispose() }
    $allowed = @($currentSid, 'S-1-5-18', 'S-1-5-32-544')
    $acl = Get-Acl -LiteralPath $root
    $descriptor = [Security.AccessControl.RawSecurityDescriptor]::new($acl.GetSecurityDescriptorBinaryForm(), 0)
    if (-not $acl.AreAccessRulesProtected -or $descriptor.Owner.Value -notin $allowed -or
        $null -eq $descriptor.DiscretionaryAcl -or $descriptor.DiscretionaryAcl.Count -eq 0) {
        throw 'StagingDirectory requires a trusted owner and a protected nonempty private DACL.'
    }
    foreach ($ace in $descriptor.DiscretionaryAcl) {
        if ($ace -isnot [Security.AccessControl.CommonAce] -or $ace.IsCallback -or
            $ace.AceQualifier -ne [Security.AccessControl.AceQualifier]::AccessAllowed -or
            $ace.SecurityIdentifier.Value -notin $allowed) {
            throw 'StagingDirectory may grant access only to the operator, SYSTEM and Administrators.'
        }
    }
    return $root
}

function Write-XmqrPrivateNewText([string] $Path, [string] $Text) {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    try { $owner = $identity.User } finally { $identity.Dispose() }
    $security = [Security.AccessControl.FileSecurity]::new()
    $security.SetOwner($owner)
    $security.SetAccessRuleProtection($true, $false)
    foreach ($sid in @($owner.Value, 'S-1-5-18', 'S-1-5-32-544') | Select-Object -Unique) {
        $rule = [Security.AccessControl.FileSystemAccessRule]::new(
            [Security.Principal.SecurityIdentifier]::new($sid),
            [Security.AccessControl.FileSystemRights]::FullControl,
            [Security.AccessControl.AccessControlType]::Allow)
        $security.AddAccessRule($rule)
    }
    # CreateNew plus the creation-time security descriptor protects the first byte.
    $stream = [IO.FileSystemAclExtensions]::Create(
        [IO.FileInfo]::new($Path), [IO.FileMode]::CreateNew,
        [Security.AccessControl.FileSystemRights]::FullControl, [IO.FileShare]::None,
        4096, [IO.FileOptions]::WriteThrough, $security)
    $bytes = $null
    try {
        $bytes = [Text.UTF8Encoding]::new($false).GetBytes($Text)
        $stream.Write($bytes, 0, $bytes.Length)
        $stream.Flush($true)
    } finally {
        if ($null -ne $bytes) { [Array]::Clear($bytes, 0, $bytes.Length) }
        $stream.Dispose()
    }
}

function Get-XmqrPasswordHash([string] $Executable, [string] $Password) {
    if (-not [IO.Path]::IsPathFullyQualified($Executable) -or $Executable -notmatch '^[A-Za-z]:\\' -or
        $Executable.Substring(2).Contains(':')) {
        throw 'HashExecutable must be an explicit local executable path.'
    }
    $file = Get-Item -LiteralPath $Executable -Force
    if ($file.PSIsContainer -or ($file.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw 'HashExecutable must be a regular local executable.'
    }
    $start = [Diagnostics.ProcessStartInfo]::new()
    $start.FileName = $file.FullName
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.RedirectStandardInput = $true
    $start.StandardInputEncoding = [Text.UTF8Encoding]::new($false)
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $start
    try {
        if (-not $process.Start()) { throw 'Unable to launch the password hash helper.' }
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        $process.StandardInput.Write($Password)
        $process.StandardInput.Close()
        if (-not $process.WaitForExit(30000)) {
            try { $process.Kill($true) } catch {}
            throw 'Password hash helper exceeded its 30-second deadline.'
        }
        $hash = $stdout.GetAwaiter().GetResult().Trim()
        # Drain, but never expose helper diagnostics: they might contain secrets.
        $null = $stderr.GetAwaiter().GetResult()
        if ($process.ExitCode -ne 0 -or $hash.Length -gt 256 -or
            $hash -cnotmatch '^\$argon2id\$v=19\$m=19456,t=2,p=1\$[A-Za-z0-9+/]{22}\$[A-Za-z0-9+/]{43}$') {
            throw 'Password hash helper failed or returned an unsupported bounded Argon2id profile.'
        }
        return $hash
    } finally {
        try { if (-not $process.HasExited) { $process.Kill($true) } } catch {}
        $process.Dispose()
    }
}

function New-XmqrLeafCertificate($Authority, [string] $Kind, [Security.Cryptography.RSA] $Key,
    [DateTimeOffset] $Before, [DateTimeOffset] $After) {
    $subject = if ($Kind -eq 'server') { 'CN=localhost' } else { 'CN=xmqr-local' }
    $request = [Security.Cryptography.X509Certificates.CertificateRequest]::new(
        $subject, $Key, [Security.Cryptography.HashAlgorithmName]::SHA256,
        [Security.Cryptography.RSASignaturePadding]::Pkcs1)
    [void] $request.CertificateExtensions.Add([Security.Cryptography.X509Certificates.X509BasicConstraintsExtension]::new($false, $false, 0, $true))
    [void] $request.CertificateExtensions.Add([Security.Cryptography.X509Certificates.X509KeyUsageExtension]::new(
        [Security.Cryptography.X509Certificates.X509KeyUsageFlags]::DigitalSignature -bor
        [Security.Cryptography.X509Certificates.X509KeyUsageFlags]::KeyEncipherment, $true))
    $oids = [Security.Cryptography.OidCollection]::new()
    $oid = if ($Kind -eq 'server') { '1.3.6.1.5.5.7.3.1' } else { '1.3.6.1.5.5.7.3.2' }
    [void] $oids.Add([Security.Cryptography.Oid]::new($oid))
    [void] $request.CertificateExtensions.Add([Security.Cryptography.X509Certificates.X509EnhancedKeyUsageExtension]::new($oids, $true))
    [void] $request.CertificateExtensions.Add([Security.Cryptography.X509Certificates.X509SubjectKeyIdentifierExtension]::new($request.PublicKey, $false))
    [void] $request.CertificateExtensions.Add([Security.Cryptography.X509Certificates.X509AuthorityKeyIdentifierExtension]::CreateFromCertificate($Authority, $true, $false))
    $san = [Security.Cryptography.X509Certificates.SubjectAlternativeNameBuilder]::new()
    if ($Kind -eq 'server') {
        $san.AddDnsName('localhost')
        $san.AddIpAddress([Net.IPAddress]::Loopback)
    } else { $san.AddDnsName('xmqr-local') }
    [void] $request.CertificateExtensions.Add($san.Build())
    $serial = [byte[]]::new(16)
    [Security.Cryptography.RandomNumberGenerator]::Fill($serial)
    $serial[0] = ($serial[0] -band 0x7f) -bor 1
    return $request.Create($Authority, $Before, $After, $serial)
}

function New-XmqrLocalCredentials {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string] $StagingDirectory,
        [Parameter(Mandatory)][string] $HashExecutable
    )
    $root = Assert-XmqrPrivateStagingDirectory $StagingDirectory
    $passwordBytes = [byte[]]::new(32)
    $caKey = $null; $ca = $null; $serverKey = $null; $server = $null; $clientKey = $null; $client = $null
    $password = $null; $hash = $null
    try {
        [Security.Cryptography.RandomNumberGenerator]::Fill($passwordBytes)
        $password = [Convert]::ToHexString($passwordBytes).ToLowerInvariant()
        $hash = Get-XmqrPasswordHash $HashExecutable $password
        $before = [DateTimeOffset]::UtcNow.AddMinutes(-5)
        $caAfter = [DateTimeOffset]::UtcNow.AddYears(2)
        $leafAfter = [DateTimeOffset]::UtcNow.AddYears(1)
        $caKey = [Security.Cryptography.RSA]::Create(3072)
        $request = [Security.Cryptography.X509Certificates.CertificateRequest]::new(
            'CN=XMQR Local Root CA', $caKey, [Security.Cryptography.HashAlgorithmName]::SHA256,
            [Security.Cryptography.RSASignaturePadding]::Pkcs1)
        [void] $request.CertificateExtensions.Add([Security.Cryptography.X509Certificates.X509BasicConstraintsExtension]::new($true, $true, 0, $true))
        [void] $request.CertificateExtensions.Add([Security.Cryptography.X509Certificates.X509KeyUsageExtension]::new(
            [Security.Cryptography.X509Certificates.X509KeyUsageFlags]::KeyCertSign -bor
            [Security.Cryptography.X509Certificates.X509KeyUsageFlags]::CrlSign, $true))
        [void] $request.CertificateExtensions.Add([Security.Cryptography.X509Certificates.X509SubjectKeyIdentifierExtension]::new($request.PublicKey, $false))
        $ca = $request.CreateSelfSigned($before, $caAfter)
        $serverKey = [Security.Cryptography.RSA]::Create(2048)
        $clientKey = [Security.Cryptography.RSA]::Create(2048)
        $server = New-XmqrLeafCertificate $ca 'server' $serverKey $before $leafAfter
        $client = New-XmqrLeafCertificate $ca 'client' $clientKey $before $leafAfter
        $sha = [Security.Cryptography.SHA256]::Create()
        try { $fingerprint = 'sha256:' + [Convert]::ToHexString($sha.ComputeHash($client.RawData)).ToLowerInvariant() }
        finally { $sha.Dispose() }
        $paths = [ordered]@{
            CaCertificate = Join-Path $root 'ca.crt'
            CaPrivateKey = Join-Path $root 'ca.key'
            ServerCertificate = Join-Path $root 'server.crt'
            ServerPrivateKey = Join-Path $root 'server.key'
            ClientCertificate = Join-Path $root 'client.crt'
            ClientPrivateKey = Join-Path $root 'client.key'
            PasswordFile = Join-Path $root 'password'
            UsersFile = Join-Path $root 'users.toml'
            AclFile = Join-Path $root 'acl.toml'
        }
        Write-XmqrPrivateNewText $paths.CaCertificate ($ca.ExportCertificatePem())
        Write-XmqrPrivateNewText $paths.CaPrivateKey ($caKey.ExportPkcs8PrivateKeyPem())
        Write-XmqrPrivateNewText $paths.ServerCertificate ($server.ExportCertificatePem())
        Write-XmqrPrivateNewText $paths.ServerPrivateKey ($serverKey.ExportPkcs8PrivateKeyPem())
        Write-XmqrPrivateNewText $paths.ClientCertificate ($client.ExportCertificatePem())
        Write-XmqrPrivateNewText $paths.ClientPrivateKey ($clientKey.ExportPkcs8PrivateKeyPem())
        Write-XmqrPrivateNewText $paths.PasswordFile $password
        $users = "[[users]]`nusername = 'xmqr-local'`ncert_sha256 = '$fingerprint'`npassword_hash = '$hash'`n"
        $acl = "[[rules]]`nusername = 'xmqr-local'`npublish = ['xmqr/local/test']`nsubscribe = ['xmqr/local/test']`n"
        Write-XmqrPrivateNewText $paths.UsersFile $users
        Write-XmqrPrivateNewText $paths.AclFile $acl
        $paths['ClientFingerprint'] = $fingerprint
        return [pscustomobject] $paths
    } finally {
        [Array]::Clear($passwordBytes, 0, $passwordBytes.Length)
        foreach ($item in @($client, $clientKey, $server, $serverKey, $ca, $caKey)) {
            if ($null -ne $item) { $item.Dispose() }
        }
        $password = $null; $hash = $null
    }
}

Export-ModuleMember -Function New-XmqrLocalCredentials
