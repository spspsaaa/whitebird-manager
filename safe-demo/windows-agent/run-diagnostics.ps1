# WhiteBird Manager local diagnostic collector. No network uploads or secrets.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$folder = Join-Path $env:LOCALAPPDATA 'WhiteBirdManager'
New-Item -ItemType Directory -Path $folder -Force | Out-Null
$script = Join-Path $root 'check-octo-local.ps1'
if (-not (Test-Path -LiteralPath $script)) { throw 'Missing local diagnostic script' }
# Child script returns a fixed set of non-sensitive fields.
$json = & $script | Out-String
$data = $json | ConvertFrom-Json
$allowed = [ordered]@{
  tool = [string]$data.tool
  timestamp_utc = [string]$data.timestamp_utc
  os = [string]$data.os
  port = [int]$data.port
  local_tcp = [string]$data.local_tcp
  local_http = [string]$data.local_http
  error_type = [string]$data.error_type
}
$target = Join-Path $folder 'octo-status.json'
$tmp = Join-Path $folder ('octo-status-' + [guid]::NewGuid().ToString('N') + '.tmp')
try {
  $allowed | ConvertTo-Json -Depth 2 | Set-Content -LiteralPath $tmp -Encoding UTF8
  Move-Item -LiteralPath $tmp -Destination $target -Force
} finally {
  if (Test-Path -LiteralPath $tmp) { Remove-Item -LiteralPath $tmp -Force }
}
Write-Host 'Diagnostic saved locally (no upload).'
Write-Host ('Status: ' + $allowed.local_tcp + ' / HTTP: ' + $allowed.local_http)
