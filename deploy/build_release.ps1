param(
  [string]$Output = "novel2gal-release.zip"
)

$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$staging = Join-Path $env:TEMP ("novel2gal-release-" + [guid]::NewGuid().ToString("N"))

New-Item -ItemType Directory -Path $staging | Out-Null

$items = @("backend", "frontend", "README.md", ".env.example")
foreach ($item in $items) {
  $source = Join-Path $root $item
  if (Test-Path $source) {
    Copy-Item $source -Destination $staging -Recurse -Force
  }
}

$venv = Join-Path $staging "backend\.venv"
if (Test-Path $venv) {
  Remove-Item $venv -Recurse -Force
}

Get-ChildItem -Path $staging -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem -Path $staging -Recurse -Directory -Filter ".pytest_cache" | Remove-Item -Recurse -Force

$outputPath = Join-Path $root $Output
if (Test-Path $outputPath) {
  Remove-Item $outputPath -Force
}

Compress-Archive -Path (Join-Path $staging "*") -DestinationPath $outputPath -Force
Remove-Item $staging -Recurse -Force

Write-Host "Built $outputPath"
