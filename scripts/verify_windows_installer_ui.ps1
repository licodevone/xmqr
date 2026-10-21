#requires -Version 7.0
# SPDX-License-Identifier: MIT
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string] $Msi,
    [Parameter(Mandatory)]
    [ValidateSet('manager', 'component')]
    [string] $Kind
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Get-MsiTableRows {
    param(
        [Parameter(Mandatory)] $Database,
        [Parameter(Mandatory)] [string] $Table,
        [Parameter(Mandatory)] [string[]] $Columns
    )

    $quotedColumns = ($Columns | ForEach-Object { "``$_``" }) -join ','
    $view = $Database.OpenView("SELECT $quotedColumns FROM ``$Table``")
    try {
        [void] $view.Execute()
        while ($record = $view.Fetch()) {
            $row = [ordered]@{}
            for ($index = 0; $index -lt $Columns.Count; $index++) {
                $row[$Columns[$index]] = $record.StringData($index + 1)
            }
            [pscustomobject] $row
            [void] [Runtime.InteropServices.Marshal]::FinalReleaseComObject($record)
        }
    }
    finally {
        [void] $view.Close()
        [void] [Runtime.InteropServices.Marshal]::FinalReleaseComObject($view)
    }
}

function Assert-Check([bool] $Condition, [string] $Message) {
    if (-not $Condition) { throw $Message }
    Write-Output "PASS $Message"
}

$fullMsi = [IO.Path]::GetFullPath($Msi)
if (-not (Test-Path -LiteralPath $fullMsi -PathType Leaf)) {
    throw "MSI not found: $fullMsi"
}

$installer = $null
$database = $null
try {
    $installer = New-Object -ComObject WindowsInstaller.Installer
    # OpenDatabase mode 0 is read-only. This script never installs or modifies the MSI.
    $database = $installer.OpenDatabase($fullMsi, 0)

    $dialogs = @(Get-MsiTableRows $database 'Dialog' @('Dialog', 'Control_First'))
    $controls = @(Get-MsiTableRows $database 'Control' @('Dialog_', 'Control', 'Type', 'Property', 'Text', 'X', 'Y', 'Width', 'Height', 'Attributes'))
    $events = @(Get-MsiTableRows $database 'ControlEvent' @('Dialog_', 'Control_', 'Event', 'Argument', 'Condition'))
    $sequence = @(Get-MsiTableRows $database 'InstallUISequence' @('Action', 'Condition', 'Sequence'))
    $properties = @(Get-MsiTableRows $database 'Property' @('Property', 'Value'))
    $checkboxes = @(Get-MsiTableRows $database 'CheckBox' @('Property', 'Value'))
    $controlConditions = @(Get-MsiTableRows $database 'ControlCondition' @('Dialog_', 'Control_', 'Action', 'Condition'))
    $launchConditions = @(Get-MsiTableRows $database 'LaunchCondition' @('Condition', 'Description'))
    $components = @(Get-MsiTableRows $database 'Component' @('Component', 'Condition', 'Directory_'))

    $expectedDialogs = @(
        'XmqrWelcomeDlg', 'XmqrTermsDlg', 'XmqrProgressDlg', 'XmqrExitDlg', 'XmqrErrorDlg',
        'XmqrCancelDlg', 'XmqrCancelledDlg', 'XmqrFatalDlg'
    )
    foreach ($dialog in $expectedDialogs) {
        Assert-Check ($dialogs.Dialog -contains $dialog) "dialog table contains $dialog"
    }

    $welcome = $sequence | Where-Object Action -EQ 'XmqrWelcomeDlg' | Select-Object -First 1
    $progress = $sequence | Where-Object Action -EQ 'XmqrProgressDlg' | Select-Object -First 1
    $execute = $sequence | Where-Object Action -EQ 'ExecuteAction' | Select-Object -First 1
    Assert-Check ($null -ne $welcome -and [int]$welcome.Sequence -lt [int]$progress.Sequence) 'welcome precedes progress'
    Assert-Check ($null -ne $progress -and [int]$progress.Sequence -lt [int]$execute.Sequence) 'progress precedes ExecuteAction'
    Assert-Check (($sequence | Where-Object Action -EQ 'XmqrExitDlg').Sequence -contains '-1') 'successful operations show finish dialog'
    Assert-Check (($sequence | Where-Object Action -EQ 'XmqrCancelledDlg').Sequence -contains '-2') 'cancelled operations show cancellation dialog'
    Assert-Check (($sequence | Where-Object Action -EQ 'XmqrFatalDlg').Sequence -contains '-3') 'failed operations show fatal-error dialog'

    $requiredEvents = @(
        @{ Dialog = 'XmqrWelcomeDlg'; Control = 'Next'; Event = 'EndDialog'; Argument = 'Return' },
        @{ Dialog = 'XmqrWelcomeDlg'; Control = 'ReadTerms'; Event = 'SpawnDialog'; Argument = 'XmqrTermsDlg' },
        @{ Dialog = 'XmqrTermsDlg'; Control = 'Close'; Event = 'EndDialog'; Argument = 'Return' },
        @{ Dialog = 'XmqrWelcomeDlg'; Control = 'Cancel'; Event = 'SpawnDialog'; Argument = 'XmqrCancelDlg' },
        @{ Dialog = 'XmqrProgressDlg'; Control = 'Cancel'; Event = 'SpawnDialog'; Argument = 'XmqrCancelDlg' },
        @{ Dialog = 'XmqrExitDlg'; Control = 'Finish'; Event = 'EndDialog'; Argument = 'Return' },
        @{ Dialog = 'XmqrCancelDlg'; Control = 'Yes'; Event = 'EndDialog'; Argument = 'Exit' },
        @{ Dialog = 'XmqrCancelDlg'; Control = 'No'; Event = 'EndDialog'; Argument = 'Return' }
    )
    foreach ($expected in $requiredEvents) {
        $found = $events | Where-Object {
            $_.Dialog_ -eq $expected.Dialog -and $_.Control_ -eq $expected.Control -and
            $_.Event -eq $expected.Event -and $_.Argument -eq $expected.Argument
        } | Select-Object -First 1
        Assert-Check ($null -ne $found) "$($expected.Dialog)/$($expected.Control) routes $($expected.Event) $($expected.Argument)"
    }

    $licenseControl = $controls | Where-Object {
        $_.Dialog_ -eq 'XmqrWelcomeDlg' -and $_.Control -eq 'AcceptLicense' -and
        $_.Type -eq 'CheckBox' -and $_.Property -eq 'XMQR_ACCEPT_LICENSE'
    } | Select-Object -First 1
    $licenseCheckbox = $checkboxes | Where-Object Property -EQ 'XMQR_ACCEPT_LICENSE' | Select-Object -First 1
    $licenseProperty = $properties | Where-Object Property -EQ 'XMQR_ACCEPT_LICENSE' | Select-Object -First 1
    Assert-Check ($null -ne $licenseControl -and $null -ne $licenseCheckbox -and $licenseCheckbox.Value -eq '1') 'license checkbox is present and unchecked by default'
    Assert-Check ($null -eq $licenseProperty -or [string]::IsNullOrEmpty($licenseProperty.Value)) 'license acceptance has no initial MSI property value'
    Assert-Check ($licenseControl.Text -match 'Li e aceito os termos de licen' -and $licenseControl.X -eq '25' -and
        $licenseControl.Y -eq '205' -and $licenseControl.Width -eq '240') 'license checkbox uses the requested explicit wording and placement'
    $readTerms = $controls | Where-Object {
        $_.Dialog_ -eq 'XmqrWelcomeDlg' -and $_.Control -eq 'ReadTerms' -and $_.Type -eq 'PushButton'
    } | Select-Object -First 1
    Assert-Check ($null -ne $readTerms -and $readTerms.Text -match 'Ler termos') 'terms reader is visible on the welcome dialog'

    $termsControl = $controls | Where-Object {
        $_.Dialog_ -eq 'XmqrTermsDlg' -and $_.Control -eq 'TermsText' -and $_.Type -eq 'ScrollableText'
    } | Select-Object -First 1
    Assert-Check ($null -ne $termsControl -and $termsControl.Text -match 'Permission is hereby granted, free of charge') 'terms dialog embeds the actual MIT grant text'
    $nextEnable = $controlConditions | Where-Object {
        $_.Dialog_ -eq 'XmqrWelcomeDlg' -and $_.Control_ -eq 'Next' -and $_.Action -eq 'enable'
    } | Select-Object -First 1
    $nextDisable = $controlConditions | Where-Object {
        $_.Dialog_ -eq 'XmqrWelcomeDlg' -and $_.Control_ -eq 'Next' -and $_.Action -eq 'disable'
    } | Select-Object -First 1
    Assert-Check (($null -ne $nextEnable -and $nextEnable.Condition -match 'XMQR_ACCEPT_LICENSE') -and
        ($null -ne $nextDisable -and $nextDisable.Condition -match 'NOT.*XMQR_ACCEPT_LICENSE')) 'Install button enables after acceptance and disables again when unchecked'
    $nextControl = $controls | Where-Object { $_.Dialog_ -eq 'XmqrWelcomeDlg' -and $_.Control -eq 'Next' } | Select-Object -First 1
    Assert-Check (([int]$nextControl.Attributes -band 2) -eq 0) 'Install button starts disabled before fresh acceptance'
    $nextPublish = $events | Where-Object {
        $_.Dialog_ -eq 'XmqrWelcomeDlg' -and $_.Control_ -eq 'Next' -and $_.Event -eq 'EndDialog' -and $_.Argument -eq 'Return'
    } | Select-Object -First 1
    Assert-Check ($null -ne $nextPublish -and $nextPublish.Condition -match 'XMQR_ACCEPT_LICENSE' -and
        $nextPublish.Condition -match 'Installed' -and $nextPublish.Condition -match 'REMOVE') 'Install button requires acceptance except for maintenance and uninstall'
    $quietGuard = $launchConditions | Where-Object {
        $_.Condition -match 'UILevel\s*>=\s*5' -and $_.Condition -match 'XMQR_ACCEPT_LICENSE' -and
        $_.Condition -match 'Installed' -and $_.Condition -match 'REMOVE'
    } | Select-Object -First 1
    Assert-Check ($null -ne $quietGuard -and $quietGuard.Condition -match 'UILevel\s*>=\s*5\s+OR\s+XMQR_ACCEPT_LICENSE\s*=\s*"1"\s+OR\s+Installed\s+OR\s+REMOVE\s*=\s*"ALL"') 'quiet and passive fresh installs require explicit license acceptance while maintenance is allowed'

    $progressControls = @($controls | Where-Object Dialog_ -EQ 'XmqrProgressDlg' | Select-Object -ExpandProperty Control)
    foreach ($control in @('ProgressBar', 'ActionText', 'ActionData')) {
        Assert-Check ($progressControls -contains $control) "progress dialog contains $control"
    }
    $errorDialogRow = $dialogs | Where-Object Dialog -EQ 'XmqrErrorDlg' | Select-Object -First 1
    Assert-Check ($errorDialogRow.Control_First -eq 'ErrorText') 'Windows Installer error dialog starts with ErrorText'
    $errorControls = @($controls | Where-Object Dialog_ -EQ 'XmqrErrorDlg' | Select-Object -ExpandProperty Control)
    foreach ($control in @('ErrorText', 'A', 'C', 'I', 'N', 'O', 'R', 'Y')) {
        Assert-Check ($errorControls -contains $control) "error dialog contains standard $control control"
    }
    $errorProperty = $properties | Where-Object Property -EQ 'ErrorDialog' | Select-Object -First 1
    Assert-Check ($errorProperty.Value -eq 'XmqrErrorDlg') 'ErrorDialog property points to detailed MSI error dialog'
    $logging = $properties | Where-Object Property -EQ 'MsiLogging' | Select-Object -First 1
    Assert-Check ($logging.Value -eq 'voicewarmup') 'MSI enables verbose installer logging'
    $startMenuProperty = $properties | Where-Object Property -EQ 'XMQR_START_MENU' | Select-Object -First 1
    $desktopProperty = $properties | Where-Object Property -EQ 'XMQR_DESKTOP' | Select-Object -First 1
    Assert-Check ($null -ne $startMenuProperty -and $startMenuProperty.Value -eq '1') 'Start Menu shortcut is checked by default'
    Assert-Check ($null -ne $desktopProperty -and $desktopProperty.Value -eq '0') 'Desktop shortcut is optional and unchecked by default'
    foreach ($choice in @(
        @{ Control = 'StartMenuChoice'; Property = 'XMQR_START_MENU' },
        @{ Control = 'DesktopChoice'; Property = 'XMQR_DESKTOP' }
    )) {
        $control = $controls | Where-Object {
            $_.Dialog_ -eq 'XmqrWelcomeDlg' -and $_.Control -eq $choice.Control -and
            $_.Type -eq 'CheckBox' -and $_.Property -eq $choice.Property
        } | Select-Object -First 1
        $checkbox = $checkboxes | Where-Object Property -EQ $choice.Property | Select-Object -First 1
        Assert-Check ($null -ne $control -and $null -ne $checkbox -and $checkbox.Value -eq '1') "$($choice.Control) is bound to $($choice.Property)"
    }
    $startMenuLabel = $controls | Where-Object { $_.Dialog_ -eq 'XmqrWelcomeDlg' -and $_.Control -eq 'StartMenuChoice' } | Select-Object -First 1
    $desktopLabel = $controls | Where-Object { $_.Dialog_ -eq 'XmqrWelcomeDlg' -and $_.Control -eq 'DesktopChoice' } | Select-Object -First 1
    Assert-Check ($startMenuLabel.Text -match 'menu Iniciar' -and $desktopLabel.Text -match 'trabalho') 'shortcut choices have clear Start Menu and Desktop labels'
    $secureProperties = ($properties | Where-Object Property -EQ 'SecureCustomProperties' | Select-Object -First 1).Value
    foreach ($secureProperty in @('XMQR_ACCEPT_LICENSE', 'XMQR_START_MENU', 'XMQR_DESKTOP')) {
        Assert-Check ($secureProperties -split ';' -contains $secureProperty) "$secureProperty survives the per-machine UI-to-service handoff"
    }

    if ($Kind -eq 'manager') {
        $shortcuts = @(Get-MsiTableRows $database 'Shortcut' @('Directory_', 'Name', 'Component_', 'Target', 'Arguments', 'WkDir'))
        $managerShortcut = $shortcuts | Where-Object {
            $_.Directory_ -eq 'XMQRStartMenuFolder' -and $_.Target -eq '[#ManagerExecutableFile]' -and
            $_.WkDir -eq 'INSTALLFOLDER' -and $_.Name -match '(?:\||^)XMQR Manager$' -and
            $_.Component_ -eq 'ManagerStartMenuShortcut'
        } | Select-Object -First 1
        Assert-Check ($null -ne $managerShortcut) 'Manager Start Menu shortcut targets the packaged executable'
        $desktopShortcut = $shortcuts | Where-Object {
            $_.Directory_ -eq 'DesktopFolder' -and $_.Target -eq '[#ManagerExecutableFile]' -and
            $_.Component_ -eq 'ManagerDesktopShortcut'
        } | Select-Object -First 1
        Assert-Check ($null -ne $desktopShortcut) 'Manager Desktop shortcut targets the packaged executable'
        Assert-Check ($managerShortcut.Name -match '(?:\||^)XMQR Manager$' -and $desktopShortcut.Name -match '(?:\||^)XMQR Manager$') 'Manager shortcut names are XMQR Manager'
        foreach ($condition in @(
            @{ Component = 'ManagerStartMenuShortcut'; Property = 'XMQR_START_MENU' },
            @{ Component = 'ManagerDesktopShortcut'; Property = 'XMQR_DESKTOP' }
        )) {
            $component = $components | Where-Object Component -EQ $condition.Component | Select-Object -First 1
            Assert-Check ($null -ne $component -and $component.Condition -eq ($condition.Property + ' = "1"')) "$($condition.Component) requires an explicitly checked choice"
        }
    }
    else {
        $shortcuts = @(Get-MsiTableRows $database 'Shortcut' @('Directory_', 'Name', 'Component_', 'Target', 'Arguments', 'WkDir'))
        $appSearch = @(Get-MsiTableRows $database 'AppSearch' @('Property', 'Signature_'))
        $registrySearch = @(Get-MsiTableRows $database 'RegLocator' @('Signature_', 'Root', 'Key', 'Name', 'Type'))
        $startAlias = $shortcuts | Where-Object {
            $_.Directory_ -eq 'XMQRStartMenuFolder' -and $_.Target -eq '[XMQR_MANAGER_EXE]' -and
            $_.Component_ -eq 'ManagerStartMenuAlias' -and -not $_.Arguments
        } | Select-Object -First 1
        $desktopAlias = $shortcuts | Where-Object {
            $_.Directory_ -eq 'DesktopFolder' -and $_.Target -eq '[XMQR_MANAGER_EXE]' -and
            $_.Component_ -eq 'ManagerDesktopAlias' -and -not $_.Arguments
        } | Select-Object -First 1
        Assert-Check ($null -ne $startAlias) 'component Start Menu alias launches the installed Manager without service arguments'
        Assert-Check ($null -ne $desktopAlias) 'component Desktop alias launches the installed Manager without service arguments'
        $productName = ($properties | Where-Object Property -EQ 'ProductName' | Select-Object -First 1).Value
        $startDisplayName = ($startAlias.Name -split '\|')[-1]
        $desktopDisplayName = ($desktopAlias.Name -split '\|')[-1]
        Assert-Check ($startDisplayName -eq $productName -and $desktopDisplayName -eq $productName) 'component aliases use a product-specific shortcut name'
        foreach ($condition in @(
            @{ Component = 'ManagerStartMenuAlias'; Choice = 'XMQR_START_MENU' },
            @{ Component = 'ManagerDesktopAlias'; Choice = 'XMQR_DESKTOP' }
        )) {
            $component = $components | Where-Object Component -EQ $condition.Component | Select-Object -First 1
            Assert-Check ($null -ne $component -and $component.Condition -match "XMQR_MANAGER_EXE.*$($condition.Choice)" -and
                $component.Condition.Contains($condition.Choice + ' = "1"')) "$($condition.Component) requires the Manager and its explicitly checked choice"
        }
        $search = $appSearch | Where-Object Property -EQ 'XMQR_MANAGER_EXE' | Select-Object -First 1
        $locator = if ($null -ne $search) { $registrySearch | Where-Object Signature_ -EQ $search.Signature_ | Select-Object -First 1 }
        Assert-Check ($null -ne $search -and $null -ne $locator -and $locator.Root -eq '2' -and
            $locator.Key -eq 'SOFTWARE\XMQR\Manager' -and $locator.Name -eq 'Executable') 'component aliases resolve the registered HKLM Manager executable'
        $secureProperties = ($properties | Where-Object Property -EQ 'SecureCustomProperties' | Select-Object -First 1).Value
        Assert-Check ($secureProperties -split ';' -contains 'XMQR_MANAGER_EXE') 'Manager path search survives the per-machine UI-to-service handoff'
        $serviceInfo = $controls | Where-Object { $_.Dialog_ -eq 'XmqrWelcomeDlg' -and $_.Control -eq 'PackageInfo' } | Select-Object -First 1
        Assert-Check ($null -ne $serviceInfo -and $serviceInfo.Text -match 'servi' -and $serviceInfo.Text -match 'privados') 'component wizard explains Windows services and private-file provisioning'
    }

    Write-Output "Verified read-only MSI UI tables: $fullMsi ($Kind)"
}
finally {
    if ($null -ne $database) { [void] [Runtime.InteropServices.Marshal]::FinalReleaseComObject($database) }
    if ($null -ne $installer) { [void] [Runtime.InteropServices.Marshal]::FinalReleaseComObject($installer) }
}
