#requires -Version 7.5
# SPDX-License-Identifier: MIT
Set-StrictMode -Version Latest

function Test-XmqrPrivateAcl {
    [CmdletBinding()]
    [OutputType([bool])]
    param(
        [Parameter(Mandatory)][Security.AccessControl.FileSystemSecurity] $Actual,
        [Parameter(Mandatory)][Security.AccessControl.FileSystemSecurity] $Expected
    )
    # Descriptor AI/group metadata can change on persistence. Compare the exact
    # access policy instead; ACE inheritance/propagation flags remain significant.
    try {
        if (-not $Actual.AreAccessRulesProtected -or -not $Expected.AreAccessRulesProtected -or
            $Actual.GetOwner([Security.Principal.SecurityIdentifier]).Value -ne
            $Expected.GetOwner([Security.Principal.SecurityIdentifier]).Value) { return $false }
        $keys = @()
        foreach ($security in @($Actual, $Expected)) {
            $raw = [Security.AccessControl.RawSecurityDescriptor]::new($security.GetSecurityDescriptorBinaryForm(), 0)
            if ($null -eq $raw.DiscretionaryAcl -or $raw.DiscretionaryAcl.Count -eq 0) { return $false }
            $entries = [Collections.Generic.List[string]]::new()
            foreach ($ace in $raw.DiscretionaryAcl) {
                if ($ace -isnot [Security.AccessControl.CommonAce] -or $ace.IsCallback -or $ace.OpaqueLength -ne 0 -or
                    $ace.AceQualifier -ne [Security.AccessControl.AceQualifier]::AccessAllowed) { return $false }
                $entries.Add(('{0}:{1}:{2}' -f $ace.SecurityIdentifier.Value, $ace.AccessMask, [int]$ace.AceFlags))
            }
            # Only allow ACEs are admitted, so ordering has no effect. Duplicates
            # remain in this multiset and cannot hide an extra access rule.
            $keys += (($entries | Sort-Object -CaseSensitive) -join '|')
        }
        return $keys[0] -ceq $keys[1]
    } catch { return $false }
}

Export-ModuleMember -Function Test-XmqrPrivateAcl
