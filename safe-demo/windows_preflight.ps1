# Read-only Windows host suitability report. Does not access browser profiles or secrets.
$ErrorActionPreference = 'Stop'
$os = Get-CimInstance Win32_OperatingSystem
$cs = Get-CimInstance Win32_ComputerSystem
$disk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'"
$ramGiB = [math]::Round($cs.TotalPhysicalMemory / 1GB, 2)
$freeGiB = if ($null -ne $disk) { [math]::Round($disk.FreeSpace / 1GB, 2) } else { 0 }
$checks = [ordered]@{
    windows_x64 = ($env:PROCESSOR_ARCHITECTURE -eq 'AMD64' -or [Environment]::Is64BitOperatingSystem) -and ($os.Caption -match 'Windows')
    memory_recommended_8_gib = $ramGiB -ge 8
    disk_at_least_40_gib = $freeGiB -ge 40
    cpu_at_least_2 = $cs.NumberOfLogicalProcessors -ge 2
    interactive_session = [Environment]::UserInteractive
}
$ready = -not ($checks.Values -contains $false)
[ordered]@{
    checks = $checks
    ready_for_manual_browser_trial = $ready
    resources = [ordered]@{
        os = $os.Caption
        memory_gib = $ramGiB
        free_disk_gib = $freeGiB
        logical_processors = $cs.NumberOfLogicalProcessors
        interactive_session = [Environment]::UserInteractive
    }
    note = 'Preflight only. Does not guarantee browser support, fingerprint identity, or 24/7 uptime.'
} | ConvertTo-Json -Depth 5
