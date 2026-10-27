param(
  [int]$Port = 3011,
  [string]$PublicOrigin = "https://172.16.19.105:3011",
  [string]$DataServerUrl = "",
  [switch]$ForwardToDataServer,
  [string]$SslCertFile = "C:\ERP_DB\finance_web105\finance.cert.pem",
  [string]$SslKeyFile = "C:\ERP_DB\finance_web105\finance.key.pem",
  [string]$TaskName = "Excel Voucher Web Server",
  # 기본은 예약 작업(로그인 없이도 부팅 시 시작, 죽으면 자동 재시작).
  # -UseStartupShortcut 를 주면 시작프로그램 폴더에 바로가기만 만든다.
  [switch]$UseStartupShortcut,
  [switch]$Hidden = $true,
  [switch]$RunNow
)

$ErrorActionPreference = "Stop"
if (Test-Path -LiteralPath 'C:\ERP_DB\finance_web105\environment.json') {
  $Task = Get-ScheduledTask -TaskName 'FinanceVoucher-Web-3011' -ErrorAction Stop
  if ($RunNow -and $Task.State -ne 'Running') { Start-ScheduledTask -TaskName $Task.TaskName }
  Write-Host 'Existing FinanceVoucher-Web-3011 task retained; no duplicate task or startup shortcut created.'
  return
}
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Runner = Join-Path $Root "run_server.ps1"
if (-not (Test-Path $Runner)) {
  throw "run_server.ps1 was not found next to this script."
}

$PowerShell = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"

$ServerArgs = @(
  "-Port", [string]$Port,
  "-PublicOrigin", "`"$PublicOrigin`"",
  "-DataServerUrl", "`"$DataServerUrl`"",
  "-RequireLogin",
  "-GroupwareSyncOnStart"
)
if ($ForwardToDataServer) { $ServerArgs += "-ForwardToDataServer" }
if ($SslCertFile -and $SslKeyFile) {
  $ServerArgs += @("-SslCertFile", "`"$SslCertFile`"", "-SslKeyFile", "`"$SslKeyFile`"")
}

$LaunchArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass")
if ($Hidden) { $LaunchArgs += @("-WindowStyle", "Hidden") }
$LaunchArgs += @("-File", "`"$Runner`"") + $ServerArgs
$Argument = $LaunchArgs -join " "

if ($UseStartupShortcut) {
  # 시작프로그램 폴더 바로가기: 이 계정으로 로그인해야 실행된다.
  $StartupDir = [Environment]::GetFolderPath("Startup")
  $LinkPath = Join-Path $StartupDir "$TaskName.lnk"
  $Shell = New-Object -ComObject WScript.Shell
  $Shortcut = $Shell.CreateShortcut($LinkPath)
  $Shortcut.TargetPath = $PowerShell
  $Shortcut.Arguments = $Argument
  $Shortcut.WorkingDirectory = $Root
  $Shortcut.WindowStyle = if ($Hidden) { 7 } else { 1 }
  $Shortcut.Description = "Excel Voucher Web Server ($PublicOrigin)"
  $Shortcut.Save()

  Write-Host "Created startup shortcut: $LinkPath"
  Write-Host "Target : $PowerShell"
  Write-Host "Args   : $Argument"
  if ($RunNow) { Start-Process -FilePath $PowerShell -ArgumentList $Argument -WorkingDirectory $Root -WindowStyle Hidden }
  return
}

# 예약 작업(권장): 로그인 없이 부팅 시 시작하고, 꺼지면 1분 뒤 자동 재시작.
$UserId = "$env:USERDOMAIN\$env:USERNAME"
$Action = New-ScheduledTaskAction -Execute $PowerShell -Argument $Argument -WorkingDirectory $Root
$Trigger = New-ScheduledTaskTrigger -AtStartup
$Settings = New-ScheduledTaskSettingsSet `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -RestartCount 999 `
  -RestartInterval (New-TimeSpan -Minutes 1) `
  -ExecutionTimeLimit (New-TimeSpan -Days 365) `
  -StartWhenAvailable
$Principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$Task = New-ScheduledTask -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal

Register-ScheduledTask -TaskName $TaskName -InputObject $Task -Force | Out-Null

Write-Host "Installed scheduled task: $TaskName"
Write-Host "Trigger: at system startup (no login required)"
Write-Host "Runner : $Runner"
Write-Host "Args   : $Argument"

if ($RunNow) {
  Start-ScheduledTask -TaskName $TaskName
  Write-Host "Started now."
}
