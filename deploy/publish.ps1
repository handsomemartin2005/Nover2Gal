param(
  [string]$Server = "47.94.183.24",
  [string]$User = "root",
  [string]$Domain = "dianlijiliang.cn",
  [string]$KeyPath = ".deploy_keys\novel2gal_aliyun_ed25519",
  [switch]$KeepPackage
)

$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$key = Resolve-Path (Join-Path $root $KeyPath) -ErrorAction Stop
$packageName = "novel2gal-release.tar.gz"
$package = Join-Path $root $packageName
$remotePackage = "/tmp/$packageName"
$remoteInstaller = "/tmp/novel2gal-server_install.sh"
$remoteWeed = "/tmp/novel2gal-weed"
$cacheDir = Join-Path $root "tmp\deploy-cache"
$weedArchive = Join-Path $cacheDir "seaweedfs-linux-amd64.tar.gz"
$weedBinary = Join-Path $cacheDir "weed"

function Invoke-Checked([string]$File, [string[]]$Arguments) {
  & $File @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "$File failed with exit code $LASTEXITCODE"
  }
}

Write-Host "[1/5] Building release package..."
& (Join-Path $PSScriptRoot "build_release_tar.ps1") -Output $packageName
if ($LASTEXITCODE -ne 0) {
  throw "Release package build failed with exit code $LASTEXITCODE"
}

$sshBase = @(
  "-i", $key.Path,
  "-o", "StrictHostKeyChecking=no",
  "$User@$Server"
)

Write-Host "[2/5] Uploading release package..."
Invoke-Checked "scp" @(
  "-i", $key.Path,
  "-o", "StrictHostKeyChecking=no",
  $package,
  "$User@$Server`:$remotePackage"
)

Write-Host "[3/5] Uploading server installer..."
Invoke-Checked "scp" @(
  "-i", $key.Path,
  "-o", "StrictHostKeyChecking=no",
  (Join-Path $PSScriptRoot "server_install.sh"),
  "$User@$Server`:$remoteInstaller"
)

if (Test-Path $weedBinary) {
  Write-Host "[3/5] Uploading object-store binary..."
  Invoke-Checked "scp" @(
    "-i", $key.Path,
    "-o", "StrictHostKeyChecking=no",
    $weedBinary,
    "$User@$Server`:$remoteWeed"
  )
} else {
  Write-Host "[3/5] SeaweedFS cache not present; using filesystem object-store backend."
}

Write-Host "[4/5] Installing and restarting on $Server..."
$remoteCommand = "chmod +x $remoteInstaller && NOVEL2GAL_DOMAIN=$Domain $remoteInstaller $remotePackage"
Invoke-Checked "ssh" ($sshBase + @($remoteCommand))

Write-Host "[5/5] Checking public health endpoint..."
$healthUrl = "https://$Domain/health"
$health = Invoke-RestMethod -Uri $healthUrl -Method Get -TimeoutSec 30
if ($health.status -ne "ok") {
  throw "Health check returned an unexpected response: $($health | ConvertTo-Json -Compress)"
}
$ready = Invoke-RestMethod -Uri "https://$Domain/health/ready" -Method Get -TimeoutSec 30
if ($ready.status -ne "ready") {
  throw "Readiness check returned an unexpected response: $($ready | ConvertTo-Json -Compress)"
}

if (-not $KeepPackage -and (Test-Path $package)) {
  Remove-Item $package -Force
}

Write-Host "Published successfully: https://$Domain"
