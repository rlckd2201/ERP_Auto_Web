param(
  [string]$Server = "https://172.17.39.121:8081",
  [string]$AgentId = "finance-agent-172-17-30-243",
  [string]$ClientIp = "172.17.30.243",
  [ValidateSet("default-printer", "off")]
  [string]$PrintMode = "default-printer",
  [string]$PrinterName = "",
  [double]$PrintWaitSeconds = 3,
  [string]$TaskName = "Excel Voucher Agent",
  [switch]$InsecureSkipTlsVerify,
  [switch]$RunNow
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Runner = Join-Path $Root "run_agent.ps1"
if (-not (Test-Path $Runner)) {
  throw "run_agent.ps1 was not found."
}

$PowerShell = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$ActionArgs = @(
  "-NoProfile",
  "-ExecutionPolicy", "Bypass",
  "-File", "`"$Runner`"",
  "-Server", "`"$Server`"",
  "-AgentId", "`"$AgentId`"",
  "-ClientIp", "`"$ClientIp`"",
  "-PrintMode", $PrintMode,
  "-PrinterName", "`"$PrinterName`"",
  "-PrintWaitSeconds", [string]$PrintWaitSeconds
)
if ($InsecureSkipTlsVerify) {
  $ActionArgs += "-InsecureSkipTlsVerify"
}

$UserId = "$env:USERDOMAIN\$env:USERNAME"
$Action = New-ScheduledTaskAction -Execute $PowerShell -Argument ($ActionArgs -join " ") -WorkingDirectory $Root
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $UserId
$Settings = New-ScheduledTaskSettingsSet `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -RestartCount 999 `
  -RestartInterval (New-TimeSpan -Minutes 1) `
  -ExecutionTimeLimit (New-TimeSpan -Days 365)
$Principal = New-ScheduledTaskPrincipal -UserId $UserId -LogonType Interactive -RunLevel Highest
$Task = New-ScheduledTask -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal

Register-ScheduledTask -TaskName $TaskName -InputObject $Task -Force | Out-Null

if ($RunNow) {
  Start-ScheduledTask -TaskName $TaskName
}

Write-Host "Installed scheduled task: $TaskName"
Write-Host "User: $UserId"
Write-Host "Server: $Server"
Write-Host "ClientIp: $ClientIp"
Write-Host "PrinterName: $PrinterName"
