#requires -Version 7.0
# SPDX-License-Identifier: MIT
# Package the generated transparent X as Windows icon frames and tray RGBA.
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$root = Split-Path $PSScriptRoot -Parent
$assets = Join-Path $root 'tools/windows-manager/assets'
$source = [Drawing.Bitmap]::new((Join-Path $assets 'manager-x.png'))
try {
    $left=$source.Width; $top=$source.Height; $right=-1; $bottom=-1
    for ($y=0; $y -lt $source.Height; $y++) {
        for ($x=0; $x -lt $source.Width; $x++) {
            if ($source.GetPixel($x,$y).A -gt 32) {
                $left=[Math]::Min($left,$x); $right=[Math]::Max($right,$x)
                $top=[Math]::Min($top,$y); $bottom=[Math]::Max($bottom,$y)
            }
        }
    }
    if ($right -lt $left) { throw 'Generated X image is empty.' }
    $bounds=[Drawing.Rectangle]::new($left,$top,$right-$left+1,$bottom-$top+1)
    $frames=@()
    foreach ($size in @(16,20,24,32,40,48,64,128,256)) {
        $bitmap=[Drawing.Bitmap]::new($size,$size,[Drawing.Imaging.PixelFormat]::Format32bppArgb)
        try {
            $graphics=[Drawing.Graphics]::FromImage($bitmap)
            try {
                $graphics.Clear([Drawing.Color]::Transparent)
                $graphics.InterpolationMode=[Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
                $graphics.PixelOffsetMode=[Drawing.Drawing2D.PixelOffsetMode]::HighQuality
                $scale=($size*0.94)/[Math]::Max($bounds.Width,$bounds.Height)
                $width=[single]($bounds.Width*$scale);$height=[single]($bounds.Height*$scale)
                $destination=[Drawing.RectangleF]::new([single](($size-$width)/2),[single](($size-$height)/2),$width,$height)
                $graphics.DrawImage($source,$destination,$bounds,[Drawing.GraphicsUnit]::Pixel)
            } finally { $graphics.Dispose() }
            $stream=[IO.MemoryStream]::new()
            try { $bitmap.Save($stream,[Drawing.Imaging.ImageFormat]::Png);$frames+=@{Size=$size;Data=$stream.ToArray()} }
            finally { $stream.Dispose() }
            if ($size -eq 32) {
                $rgba=[byte[]]::new(32*32*4)
                for($py=0;$py -lt 32;$py++){for($px=0;$px -lt 32;$px++){
                    $color=$bitmap.GetPixel($px,$py);$index=($py*32+$px)*4
                    $rgba[$index]=$color.R;$rgba[$index+1]=$color.G;$rgba[$index+2]=$color.B;$rgba[$index+3]=$color.A
                }}
                [IO.File]::WriteAllBytes((Join-Path $assets 'manager.rgba'),$rgba)
                $bitmap.Save((Join-Path $assets 'manager-x-32.png'),[Drawing.Imaging.ImageFormat]::Png)
            }
        } finally { $bitmap.Dispose() }
    }
    $stream=[IO.MemoryStream]::new()
    $writer=[IO.BinaryWriter]::new($stream)
    try {
        $writer.Write([uint16]0);$writer.Write([uint16]1);$writer.Write([uint16]$frames.Count)
        $offset=6+16*$frames.Count
        foreach($frame in $frames){
            $dimension=if($frame.Size -eq 256){0}else{$frame.Size}
            $writer.Write([byte]$dimension);$writer.Write([byte]$dimension)
            $writer.Write([byte]0);$writer.Write([byte]0);$writer.Write([uint16]1);$writer.Write([uint16]32)
            $writer.Write([uint32]$frame.Data.Length);$writer.Write([uint32]$offset)
            $offset+=$frame.Data.Length
        }
        foreach($frame in $frames){$writer.Write([byte[]]$frame.Data)}
        $writer.Flush();$ico=$stream.ToArray()
        [IO.File]::WriteAllBytes((Join-Path $assets 'manager.ico'),$ico)
        [IO.File]::WriteAllBytes((Join-Path $root 'packaging/windows/icons/manager.ico'),$ico)
    } finally { $writer.Dispose();$stream.Dispose() }
    Write-Output 'Manager X packaged: 9 icon frames, 32x32 tray, 94% useful width.'
} finally { $source.Dispose() }
