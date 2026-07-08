param(
    [string]$ManifestPath = "frontend/assets/asset_manifest.json",
    [string]$OutputDir = "frontend/assets/vendor"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path $ManifestPath)) {
    throw "Manifest not found: $ManifestPath"
}

New-Item -ItemType Directory -Force $OutputDir | Out-Null
$manifest = Get-Content -Encoding UTF8 $ManifestPath | ConvertFrom-Json
$items = @()
$items += @($manifest.backgrounds)
$items += @($manifest.portraits)
$items += @($manifest.bgm)

foreach ($item in $items) {
    if (-not $item.url) { continue }
    $extension = [System.IO.Path]::GetExtension(([uri]$item.url).AbsolutePath)
    if (-not $extension) { $extension = ".bin" }
    $target = Join-Path $OutputDir "$($item.id)$extension"
    if (Test-Path $target) {
        Write-Host "skip $target"
        continue
    }
    Write-Host "download $($item.id) <- $($item.url)"
    Invoke-WebRequest -UseBasicParsing -Uri $item.url -OutFile $target
}

Write-Host "done: $OutputDir"
