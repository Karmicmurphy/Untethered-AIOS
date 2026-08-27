param(
    [string]$OutputDirectory = $PSScriptRoot
)

$ErrorActionPreference = 'Stop'
$source = Join-Path $PSScriptRoot 'TwisDesktopLauncher.cs'
$manifest = Join-Path $PSScriptRoot 'launcher.manifest'
$icon = Join-Path $OutputDirectory 'twis-holo-workshop.ico'
$executable = Join-Path $OutputDirectory 'TWIS Holo Workshop.exe'
$compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'

if (-not (Test-Path -LiteralPath $compiler)) {
    throw "The Windows .NET Framework C# compiler was not found at $compiler"
}

New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null

Add-Type -AssemblyName System.Drawing
$sizes = @(16, 24, 32, 48, 64, 128, 256)
$images = New-Object System.Collections.Generic.List[byte[]]

foreach ($size in $sizes) {
    $bitmap = New-Object System.Drawing.Bitmap $size, $size, ([System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    try {
        $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
        $graphics.Clear([System.Drawing.Color]::Transparent)

        $inset = [Math]::Max(1.0, $size * 0.035)
        $bounds = New-Object System.Drawing.RectangleF $inset, $inset, ($size - 2 * $inset), ($size - 2 * $inset)
        $background = New-Object System.Drawing.Drawing2D.LinearGradientBrush $bounds, ([System.Drawing.Color]::FromArgb(255, 4, 13, 21)), ([System.Drawing.Color]::FromArgb(255, 8, 29, 36)), 135
        $graphics.FillEllipse($background, $bounds)
        $background.Dispose()

        $brassWidth = [Math]::Max(1.0, $size * 0.045)
        $cyanWidth = [Math]::Max(1.0, $size * 0.035)
        $brass = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(255, 201, 151, 73)), $brassWidth
        $cyan = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(255, 51, 229, 244)), $cyanWidth
        $white = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 225, 251, 252))
        $center = $size / 2.0
        $ringInset = $size * 0.13
        $graphics.DrawEllipse($brass, $ringInset, $ringInset, $size - 2 * $ringInset, $size - 2 * $ringInset)

        for ($tick = 0; $tick -lt 12; $tick++) {
            $angle = ($tick * 30 - 90) * [Math]::PI / 180
            $outer = $size * 0.415
            $inner = if (($tick % 3) -eq 0) { $size * 0.345 } else { $size * 0.375 }
            $graphics.DrawLine($brass,
                [single]($center + [Math]::Cos($angle) * $inner),
                [single]($center + [Math]::Sin($angle) * $inner),
                [single]($center + [Math]::Cos($angle) * $outer),
                [single]($center + [Math]::Sin($angle) * $outer))
        }

        $needle = @(
            (New-Object System.Drawing.PointF ($center), ($size * 0.16)),
            (New-Object System.Drawing.PointF ($center + $size * 0.105), ($center + $size * 0.05)),
            (New-Object System.Drawing.PointF ($center), ($center + $size * 0.34)),
            (New-Object System.Drawing.PointF ($center - $size * 0.105), ($center + $size * 0.05))
        )
        $graphics.FillPolygon((New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 39, 224, 241))), $needle)
        $graphics.DrawLine($cyan, $size * 0.25, $center, $size * 0.75, $center)
        $hub = $size * 0.105
        $graphics.FillEllipse($white, $center - $hub, $center - $hub, 2 * $hub, 2 * $hub)
        $graphics.DrawEllipse($brass, $center - $hub, $center - $hub, 2 * $hub, 2 * $hub)

        $stream = New-Object System.IO.MemoryStream
        $bitmap.Save($stream, [System.Drawing.Imaging.ImageFormat]::Png)
        $images.Add($stream.ToArray())
        $stream.Dispose()
        $brass.Dispose()
        $cyan.Dispose()
        $white.Dispose()
    }
    finally {
        $graphics.Dispose()
        $bitmap.Dispose()
    }
}

$file = [System.IO.File]::Create($icon)
$writer = New-Object System.IO.BinaryWriter $file
try {
    $writer.Write([UInt16]0)
    $writer.Write([UInt16]1)
    $writer.Write([UInt16]$sizes.Count)
    $offset = 6 + (16 * $sizes.Count)
    for ($index = 0; $index -lt $sizes.Count; $index++) {
        $dimension = if ($sizes[$index] -eq 256) { [byte]0 } else { [byte]$sizes[$index] }
        $writer.Write($dimension)
        $writer.Write($dimension)
        $writer.Write([byte]0)
        $writer.Write([byte]0)
        $writer.Write([UInt16]1)
        $writer.Write([UInt16]32)
        $writer.Write([UInt32]$images[$index].Length)
        $writer.Write([UInt32]$offset)
        $offset += $images[$index].Length
    }
    foreach ($image in $images) {
        $writer.Write($image)
    }
}
finally {
    $writer.Dispose()
    $file.Dispose()
}

& $compiler /nologo /target:winexe /platform:anycpu /optimize+ /win32icon:"$icon" /win32manifest:"$manifest" /reference:System.dll /reference:System.Drawing.dll /reference:System.Windows.Forms.dll /out:"$executable" "$source"
if ($LASTEXITCODE -ne 0) {
    throw "Launcher compilation failed with exit code $LASTEXITCODE"
}

Get-Item -LiteralPath $executable, $icon | Select-Object FullName, Length, LastWriteTime
