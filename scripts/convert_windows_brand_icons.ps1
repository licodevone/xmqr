#requires -Version 7.0
# SPDX-License-Identifier: MIT
# Deterministic format conversion only; the PNG artwork is preserved separately.
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$root = Split-Path $PSScriptRoot -Parent
$icons = Join-Path $root 'packaging/windows/icons'
$null = New-Item -ItemType Directory -Path $icons -Force
foreach ($kind in @('broker', 'admin', 'client', 'manager')) {
    if ($kind -eq 'manager' -and (Test-Path -LiteralPath (Join-Path $root 'tools/windows-manager/assets/manager-x.png'))) {
        & (Join-Path $PSScriptRoot 'convert_windows_manager_x.ps1')
        continue
    }
    $source = [Drawing.Bitmap]::new((Join-Path $icons ($kind + '.png')))
    try {
        # Ignore fully transparent outer padding when fitting standard icon frames.
        $left = $source.Width; $top = $source.Height; $right = -1; $bottom = -1
        for ($y = 0; $y -lt $source.Height; $y++) {
            for ($x = 0; $x -lt $source.Width; $x++) {
                if ($source.GetPixel($x, $y).A -gt 8) {
                    $left = [Math]::Min($left, $x); $right = [Math]::Max($right, $x)
                    $top = [Math]::Min($top, $y); $bottom = [Math]::Max($bottom, $y)
                }
            }
        }
        if ($right -lt $left) { throw "Empty image: $kind" }
        $bounds = [Drawing.Rectangle]::new($left, $top, $right - $left + 1, $bottom - $top + 1)
        $frames = @()
        foreach ($size in @(16, 20, 24, 32, 40, 48, 64, 128, 256)) {
            $bitmap = [Drawing.Bitmap]::new($size, $size, [Drawing.Imaging.PixelFormat]::Format32bppArgb)
            try {
                $graphics = [Drawing.Graphics]::FromImage($bitmap)
                try {
                    $graphics.Clear([Drawing.Color]::Transparent)
                    $graphics.InterpolationMode = [Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
                    $graphics.PixelOffsetMode = [Drawing.Drawing2D.PixelOffsetMode]::HighQuality
                    $scale = ($size * 0.92) / [Math]::Max($bounds.Width, $bounds.Height)
                    $width = [single]($bounds.Width * $scale); $height = [single]($bounds.Height * $scale)
                    $destination = [Drawing.RectangleF]::new([single](($size - $width) / 2), [single](($size - $height) / 2), $width, $height)
                    $graphics.DrawImage($source, $destination, $bounds, [Drawing.GraphicsUnit]::Pixel)
                } finally { $graphics.Dispose() }
                $stream = [IO.MemoryStream]::new()
                try { $bitmap.Save($stream, [Drawing.Imaging.ImageFormat]::Png); $frames += @{ Size=$size; Data=$stream.ToArray() } }
                finally { $stream.Dispose() }
                if ($kind -eq 'manager' -and $size -eq 32) {
                    $rgba = [byte[]]::new(32 * 32 * 4)
                    for ($py = 0; $py -lt 32; $py++) { for ($px = 0; $px -lt 32; $px++) {
                        $pixel = $bitmap.GetPixel($px, $py); $i = ($py * 32 + $px) * 4
                        $rgba[$i]=$pixel.R; $rgba[$i+1]=$pixel.G; $rgba[$i+2]=$pixel.B; $rgba[$i+3]=$pixel.A
                    } }
                    $assets = Join-Path $root 'tools/windows-manager/assets'
                    $null = New-Item -ItemType Directory -Path $assets -Force
                    [IO.File]::WriteAllBytes((Join-Path $assets 'manager.rgba'), $rgba)
                }
            } finally { $bitmap.Dispose() }
        }
        $file = [IO.File]::Create((Join-Path $icons ($kind + '.ico')))
        $writer = [IO.BinaryWriter]::new($file)
        try {
            $writer.Write([uint16]0); $writer.Write([uint16]1); $writer.Write([uint16]$frames.Count)
            $offset = 6 + 16 * $frames.Count
            foreach ($frame in $frames) {
                $dimension = if ($frame.Size -eq 256) { 0 } else { $frame.Size }
                $writer.Write([byte]$dimension); $writer.Write([byte]$dimension)
                $writer.Write([byte]0); $writer.Write([byte]0); $writer.Write([uint16]1); $writer.Write([uint16]32)
                $writer.Write([uint32]$frame.Data.Length); $writer.Write([uint32]$offset)
                $offset += $frame.Data.Length
            }
            foreach ($frame in $frames) { $writer.Write([byte[]]$frame.Data) }
        } finally { $writer.Dispose(); $file.Dispose() }
        Write-Output "$kind.ico: $($frames.Count) PNG frames, 16-256px"
    } finally { $source.Dispose() }
}
