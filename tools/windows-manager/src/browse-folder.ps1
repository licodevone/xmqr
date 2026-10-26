# SPDX-License-Identifier: MIT
# Read-only directory browser; never changes ACLs or launches file associations.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
try {
    $root = [IO.Path]::GetFullPath($env:XMQR_BROWSE_ROOT)
    if ($root.Length -gt 3) { $root = $root.TrimEnd('\') }
    if (-not [IO.Directory]::Exists($root)) { throw 'Pasta não encontrada.' }
    $script:location = $root
    $form = New-Object System.Windows.Forms.Form
    $form.Text = 'XMQR — consulta administrativa de pasta'
    $form.Size = New-Object System.Drawing.Size(850, 560)
    $form.StartPosition = 'CenterScreen'
    $bar = New-Object System.Windows.Forms.FlowLayoutPanel
    $bar.Dock = 'Top'
    $bar.Height = 42
    $up = New-Object System.Windows.Forms.Button
    $up.Text = 'Voltar'
    $refresh = New-Object System.Windows.Forms.Button
    $refresh.Text = 'Atualizar'
    $bar.Controls.Add($up)
    $bar.Controls.Add($refresh)
    $address = New-Object System.Windows.Forms.Label
    $address.AutoSize = $true
    $bar.Controls.Add($address)
    $list = New-Object System.Windows.Forms.ListView
    $list.Dock = 'Fill'
    $list.View = 'Details'
    $list.FullRowSelect = $true
    $list.MultiSelect = $false
    [void]$list.Columns.Add('Nome', 490)
    [void]$list.Columns.Add('Tipo', 130)
    [void]$list.Columns.Add('Bytes', 130)
    $status = New-Object System.Windows.Forms.Label
    $status.Dock = 'Bottom'
    $status.Height = 42
    $status.Text = 'Duplo clique abre subpastas. Arquivos são somente listados; use Abrir configuração para editar.'
    $form.Controls.Add($list)
    $form.Controls.Add($bar)
    $form.Controls.Add($status)
    function Show-Directory([string] $path) {
        try {
            $full = [IO.Path]::GetFullPath($path)
            if ($full.Length -gt 3) { $full = $full.TrimEnd('\') }
            if ($full -ne $root -and -not $full.StartsWith($root.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) {
                throw 'Navegação fora da pasta registrada recusada.'
            }
            # Do not follow junctions/symlinks outside the registered tree.
            $probe = $full
            while ($probe.Length -ge $root.Length) {
                if (([IO.File]::GetAttributes($probe) -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                    throw 'Links e junções não são abertos pelo navegador administrativo.'
                }
                $probe = [IO.Path]::GetDirectoryName($probe)
                if (-not $probe) { break }
            }
            $items = @(Get-ChildItem -LiteralPath $full -Force -ErrorAction Stop | Select-Object -First 2001)
            $list.Items.Clear()
            foreach ($item in ($items | Select-Object -First 2000 | Sort-Object -Property @{Expression='PSIsContainer';Descending=$true},Name)) {
                $row = New-Object System.Windows.Forms.ListViewItem($item.Name)
                $link = ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0
                $type = if ($link) { 'Link (bloqueado)' } elseif ($item.PSIsContainer) { 'Pasta' } else { 'Arquivo' }
                [void]$row.SubItems.Add($type)
                [void]$row.SubItems.Add($(if ($item.PSIsContainer) { '' } else { [string]$item.Length }))
                $row.Tag = if ($item.PSIsContainer -and -not $link) { $item.FullName } else { $null }
                [void]$list.Items.Add($row)
            }
            $script:location = $full
            $address.Text = $full
            $up.Enabled = $full -ne $root
            if ($items.Count -gt 2000) { $status.Text = 'Exibindo os primeiros 2000 itens. Nenhuma permissão foi alterada.' }
        } catch {
            [void][System.Windows.Forms.MessageBox]::Show($form, $_.Exception.Message, 'XMQR — não foi possível listar a pasta')
        }
    }
    $up.Add_Click({ Show-Directory ([IO.Path]::GetDirectoryName($script:location)) })
    $refresh.Add_Click({ Show-Directory $script:location })
    $list.Add_DoubleClick({
        if ($list.SelectedItems.Count -eq 1 -and $list.SelectedItems[0].Tag) {
            Show-Directory ([string]$list.SelectedItems[0].Tag)
        }
    })
    Show-Directory $root
    [void]$form.ShowDialog()
    $form.Dispose()
} catch {
    [void][System.Windows.Forms.MessageBox]::Show($_.Exception.Message, 'XMQR — falha ao abrir pasta')
    exit 1
}
