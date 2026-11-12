# Opt-in local monitoring: runs a read-only check every 15 minutes.
# Uses the current Windows user; does not require admin privileges.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$script = Join-Path $root 'run-diagnostics.ps1'
if (-not (Test-Path -LiteralPath $script)) { throw 'Missing diagnostic collector' }
$taskName = 'WhiteBirdManager-LocalDiagnostics'
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoProfile -NonInteractive -File "' + $script + '"')
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 15)
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 2) -StartWhenAvailable
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description 'Read-only Octo local health checks; no data upload' -Force | Out-Null
Write-Host 'Installed local-only diagnostic task.'
Write-Host 'To uninstall, run uninstall-local-monitor.ps1.'
