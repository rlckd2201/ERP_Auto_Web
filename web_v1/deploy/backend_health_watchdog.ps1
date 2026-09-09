param(
    [string]$BackendTaskName = "AccountingWeb-Backend",
    [int]$FailureThreshold = 2
)

$ErrorActionPreference = "Stop"
$StatePath = "C:\ERP_DB\backend_health_watchdog.failures"
$LogPath = "C:\ERP_DB\backend_logs\backend_health_watchdog.log"
$HealthUrl = "https://127.0.0.1:8080/health"

function Write-WatchdogLog([string]$Message) {
    $directory = Split-Path -Parent $LogPath
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
    "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message" |
        Add-Content -LiteralPath $LogPath -Encoding UTF8
}

function Test-BackendHealth {
    try {
        $status = & curl.exe -k -sS --max-time 8 -o NUL -w "%{http_code}" $HealthUrl 2>$null
        return ($LASTEXITCODE -eq 0 -and "$status".Trim() -eq "200")
    } catch {
        return $false
    }
}

if (Test-BackendHealth) {
    if (Test-Path -LiteralPath $StatePath) {
        Remove-Item -LiteralPath $StatePath -Force -ErrorAction SilentlyContinue
        Write-WatchdogLog "health restored without restart"
    }
    exit 0
}

$failures = 0
if (Test-Path -LiteralPath $StatePath) {
    try { $failures = [int](Get-Content -LiteralPath $StatePath -Raw) } catch { $failures = 0 }
}
$failures++
Set-Content -LiteralPath $StatePath -Value $failures -Encoding ASCII
Write-WatchdogLog "health check failed ($failures/$FailureThreshold)"
if ($failures -lt [Math]::Max(1, $FailureThreshold)) { exit 1 }

& schtasks.exe /End /TN $BackendTaskName *> $null
$backendProcesses = @(
    Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" |
        Where-Object { $_.CommandLine -match '(^|\s)-m\s+web_v1\.backend(\s|$)' }
)
foreach ($process in $backendProcesses) {
    Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
    Write-WatchdogLog "terminated stale backend pid=$($process.ProcessId)"
}
Start-Sleep -Seconds 2
Remove-Item -LiteralPath $StatePath -Force -ErrorAction SilentlyContinue
& schtasks.exe /Run /TN $BackendTaskName *> $null
Write-WatchdogLog "restart requested"

for ($attempt = 1; $attempt -le 15; $attempt++) {
    Start-Sleep -Seconds 2
    if (Test-BackendHealth) {
        Write-WatchdogLog "restart verified: HTTP 200"
        exit 0
    }
}
Write-WatchdogLog "restart verification failed"
exit 2
