$ErrorActionPreference = 'Stop'
$taskName = 'WhiteBirdManager-LocalDiagnostics'
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($null -ne $task) {
  Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}
Write-Host 'Local diagnostic task removed. Existing status file remains on this PC.'
