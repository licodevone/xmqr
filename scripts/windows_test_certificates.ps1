#requires -Version 7.0
# SPDX-License-Identifier: MIT
# Test-only, ephemeral CA and TLS identities. Never installs a certificate/store entry.
[CmdletBinding()]
param([Parameter(Mandatory)][string] $OutputDirectory)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if (-not $IsWindows) { throw 'Native Windows fixture only.' }
$root = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $root) { throw 'Choose a new fixture directory.' }
$null = New-Item -ItemType Directory -Path $root
$sid = [Security.Principal.WindowsIdentity]::GetCurrent().User
$acl = [Security.AccessControl.DirectorySecurity]::new()
$acl.SetOwner($sid)
$acl.SetAccessRuleProtection($true, $false)
$inherit = [Security.AccessControl.InheritanceFlags]::ContainerInherit -bor [Security.AccessControl.InheritanceFlags]::ObjectInherit
foreach ($principal in @($sid, [Security.Principal.SecurityIdentifier]::new('S-1-5-18'), [Security.Principal.SecurityIdentifier]::new('S-1-5-32-544'))) {
    $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($principal, [Security.AccessControl.FileSystemRights]::FullControl, $inherit, [Security.AccessControl.PropagationFlags]::None, [Security.AccessControl.AccessControlType]::Allow))
}
Set-Acl -LiteralPath $root -AclObject $acl
$before = [DateTimeOffset]::UtcNow.AddMinutes(-5)
$after = [DateTimeOffset]::UtcNow.AddDays(2)
$caKey = [Security.Cryptography.RSA]::Create(2048)
$caRequest = [Security.Cryptography.X509Certificates.CertificateRequest]::new('CN=XMQR P242 TEST ONLY CA', $caKey, [Security.Cryptography.HashAlgorithmName]::SHA256, [Security.Cryptography.RSASignaturePadding]::Pkcs1)
$caRequest.CertificateExtensions.Add([Security.Cryptography.X509Certificates.X509BasicConstraintsExtension]::new($true, $false, 0, $true))
$caRequest.CertificateExtensions.Add([Security.Cryptography.X509Certificates.X509KeyUsageExtension]::new([Security.Cryptography.X509Certificates.X509KeyUsageFlags]::KeyCertSign -bor [Security.Cryptography.X509Certificates.X509KeyUsageFlags]::CrlSign, $true))
$caRequest.CertificateExtensions.Add([Security.Cryptography.X509Certificates.X509SubjectKeyIdentifierExtension]::new($caRequest.PublicKey, $false))
$ca = $caRequest.CreateSelfSigned($before, $after)
try {
    [IO.File]::WriteAllText((Join-Path $root 'ca.crt'), $ca.ExportCertificatePem(), [Text.UTF8Encoding]::new($false))
    foreach ($name in @('server', 'client', 'wrong-server')) {
        $key = [Security.Cryptography.RSA]::Create(2048)
        try {
            $request = [Security.Cryptography.X509Certificates.CertificateRequest]::new("CN=XMQR P242 TEST ONLY $name", $key, [Security.Cryptography.HashAlgorithmName]::SHA256, [Security.Cryptography.RSASignaturePadding]::Pkcs1)
            $request.CertificateExtensions.Add([Security.Cryptography.X509Certificates.X509BasicConstraintsExtension]::new($false, $false, 0, $true))
            $request.CertificateExtensions.Add([Security.Cryptography.X509Certificates.X509KeyUsageExtension]::new([Security.Cryptography.X509Certificates.X509KeyUsageFlags]::DigitalSignature -bor [Security.Cryptography.X509Certificates.X509KeyUsageFlags]::KeyEncipherment, $true))
            $oids = [Security.Cryptography.OidCollection]::new()
            $oid = if ($name -eq 'client') { '1.3.6.1.5.5.7.3.2' } else { '1.3.6.1.5.5.7.3.1' }
            $null = $oids.Add([Security.Cryptography.Oid]::new($oid))
            $request.CertificateExtensions.Add([Security.Cryptography.X509Certificates.X509EnhancedKeyUsageExtension]::new($oids, $true))
            $request.CertificateExtensions.Add([Security.Cryptography.X509Certificates.X509SubjectKeyIdentifierExtension]::new($request.PublicKey, $false))
            $request.CertificateExtensions.Add([Security.Cryptography.X509Certificates.X509AuthorityKeyIdentifierExtension]::CreateFromCertificate($ca, $true, $false))
            $sans = [Security.Cryptography.X509Certificates.SubjectAlternativeNameBuilder]::new()
            if ($name -eq 'server') { $sans.AddDnsName('localhost'); $sans.AddIpAddress([Net.IPAddress]::Loopback) }
            elseif ($name -eq 'wrong-server') { $sans.AddDnsName('wrong.invalid') }
            else { $sans.AddDnsName('fixture-device') }
            $request.CertificateExtensions.Add($sans.Build())
            $serial = [byte[]]::new(16)
            [Security.Cryptography.RandomNumberGenerator]::Fill($serial)
            $serial[0] = $serial[0] -band 0x7f
            $certificate = $request.Create($ca, $before, $after.AddMinutes(-1), $serial)
            try {
                [IO.File]::WriteAllText((Join-Path $root "$name.crt"), $certificate.ExportCertificatePem(), [Text.UTF8Encoding]::new($false))
                [IO.File]::WriteAllText((Join-Path $root "$name.key"), $key.ExportPkcs8PrivateKeyPem(), [Text.UTF8Encoding]::new($false))
            } finally { $certificate.Dispose() }
        } finally { $key.Dispose() }
    }
} finally { $ca.Dispose(); $caKey.Dispose() }
Write-Output 'Created private test-only certificates; no certificate store was changed.'
