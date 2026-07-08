param(
  [string]$Output = "novel2gal-release.tar.gz"
)

$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$staging = Join-Path $env:TEMP ("novel2gal-release-" + [guid]::NewGuid().ToString("N"))

New-Item -ItemType Directory -Path $staging | Out-Null

foreach ($item in @("backend", "frontend", "README.md", ".env.example")) {
  $source = Join-Path $root $item
  if (Test-Path $source) {
    Copy-Item $source -Destination $staging -Recurse -Force
  }
}

foreach ($remove in @("backend\.venv")) {
  $target = Join-Path $staging $remove
  if (Test-Path $target) {
    Remove-Item $target -Recurse -Force
  }
}

Get-ChildItem -Path $staging -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem -Path $staging -Recurse -Directory -Filter ".pytest_cache" | Remove-Item -Recurse -Force

$outputPath = Join-Path $root $Output
if (Test-Path $outputPath) {
  Remove-Item $outputPath -Force
}

Push-Location $staging
try {
  tar -czf $outputPath *
} finally {
  Pop-Location
}

Remove-Item $staging -Recurse -Force
Write-Host "Built $outputPath"
