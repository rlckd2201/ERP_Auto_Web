param(
  [string]$HostName = "172.16.19.105",
  [int]$Port = 3012,
  [string]$PublicOrigin = "https://172.16.19.105:3012",
  [string]$DataServerUrl = "",
  [string]$DataServerEndpoint = "/api/excel-voucher/jobs",
  [string]$DataDir = "C:\ERP_DB\finance_3011_data",
  [switch]$ForwardToDataServer,
  [switch]$RequireLogin = $true,
  [switch]$GroupwareSyncOnStart,
  [string]$GroupwareDbUser = "dlpadmin2",
  [string]$GroupwareDbPassword = "rlarlckd12!@",
  [string]$GroupwareMailDomain = "dae-seung.co.kr",
  [string]$SmtpHost = "35.216.76.148",
  [int]$SmtpPort = 25,
  [string]$SmtpUser = "",
  [string]$SmtpPassword = "",
  [string]$SmtpFrom = "admpdm@dae-seung.co.kr",
  [string]$SmtpFromName = "",
  [string]$SslCertFile = "C:\ERP_DB\finance_web105\finance.cert.pem",
  [string]$SslKeyFile = "C:\ERP_DB\finance_web105\finance.key.pem"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

if (Test-Path -LiteralPath 'C:\ERP_DB\finance_web105\environment.json') {
  $Task = Get-ScheduledTask -TaskName 'FinanceVoucher-Web-3012' -ErrorAction Stop
  if ($Task.State -ne 'Running') { Start-ScheduledTask -TaskName $Task.TaskName }
  Write-Host 'FinanceVoucher-Web-3012 manages this installation with its private configuration.'
  return
}

if (-not $SmtpFromName) {
  $SmtpFromName = [Text.Encoding]::UTF8.GetString(
    [Convert]::FromBase64String("7J6s7KCV7KCE7ZGc7J6Q64+Z7ZmUIOyLnOyKpO2FnA==")
  )
}

$UsesHttps = $PublicOrigin -match '^https://'
$HasCert = -not [string]::IsNullOrWhiteSpace($SslCertFile)
$HasKey = -not [string]::IsNullOrWhiteSpace($SslKeyFile)

if ($HasCert -xor $HasKey) {
  throw "HTTPS requires both -SslCertFile and -SslKeyFile."
}
if ($UsesHttps -and (-not $HasCert -or -not $HasKey)) {
  throw "PublicOrigin uses HTTPS, but SSL certificate paths are empty."
}
if ($HasCert -and -not (Test-Path -LiteralPath $SslCertFile -PathType Leaf)) {
  throw "SSL certificate file was not found: $SslCertFile"
}
if ($HasKey -and -not (Test-Path -LiteralPath $SslKeyFile -PathType Leaf)) {
  throw "SSL key file was not found: $SslKeyFile"
}

$Candidates = @(@(
  (Join-Path $Root '.venv\Scripts\python.exe'),
  "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
  "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
  "$env:ProgramFiles\Python312\python.exe",
  "$env:ProgramFiles\Python311\python.exe"
) | Where-Object { $_ -and (Test-Path $_) })

if ($Candidates.Count -gt 0) {
  $Python = $Candidates[0]
} else {
  $PyLine = (& py -0p 2>$null | Select-Object -First 1)
  if ($LASTEXITCODE -eq 0 -and $PyLine -match "([A-Za-z]:\\.*python\.exe)") {
    $Python = $Matches[1]
  } else {
    throw "Python 3.11+ is required. Install Python, then run this script again."
  }
}

$env:EXCEL_VOUCHER_WEB_HOST = $HostName
$env:EXCEL_VOUCHER_WEB_PORT = [string]$Port
$env:EXCEL_VOUCHER_WEB_PUBLIC_ORIGIN = $PublicOrigin
$env:EXCEL_VOUCHER_DATA_DIR = $DataDir
$env:EXCEL_VOUCHER_DATA_SERVER_URL = $DataServerUrl
$env:EXCEL_VOUCHER_DATA_SERVER_ENDPOINT = $DataServerEndpoint
$env:EXCEL_VOUCHER_FORWARD_TO_DATA_SERVER = if ($ForwardToDataServer) { "1" } else { "0" }
$env:EXCEL_VOUCHER_AUTH_REQUIRED = if ($RequireLogin) { "1" } else { "0" }
$env:EXCEL_VOUCHER_GROUPWARE_SYNC_ON_START = if ($GroupwareSyncOnStart) { "1" } else { "0" }
$env:EXCEL_VOUCHER_GROUPWARE_DB_USER = $GroupwareDbUser
$env:EXCEL_VOUCHER_GROUPWARE_DB_PASSWORD = $GroupwareDbPassword
$env:EXCEL_VOUCHER_GROUPWARE_MAIL_DOMAIN = $GroupwareMailDomain
$env:EXCEL_VOUCHER_SMTP_HOST = $SmtpHost
$env:EXCEL_VOUCHER_SMTP_PORT = [string]$SmtpPort
if ($SmtpUser) { $env:EXCEL_VOUCHER_SMTP_USER = $SmtpUser }
if ($SmtpPassword) { $env:EXCEL_VOUCHER_SMTP_PASSWORD = $SmtpPassword }
$env:EXCEL_VOUCHER_SMTP_FROM = $SmtpFrom
$env:EXCEL_VOUCHER_SMTP_FROM_NAME = $SmtpFromName

& $Python -m pip install -r requirements.txt

$UvicornArgs = @("-m", "uvicorn", "app.main:app", "--host", $HostName, "--port", [string]$Port)
if ($SslCertFile -and $SslKeyFile) {
  $UvicornArgs += @("--ssl-certfile", $SslCertFile, "--ssl-keyfile", $SslKeyFile)
}

& $Python @UvicornArgs
