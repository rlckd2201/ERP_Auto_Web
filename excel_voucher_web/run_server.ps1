param(
  [string]$HostName = "0.0.0.0",
  [int]$Port = 8081,
  [string]$PublicOrigin = "https://172.17.39.121:8081",
  [string]$DataServerUrl = "http://127.0.0.1:18080",
  [string]$DataServerEndpoint = "/api/excel-voucher/jobs",
  [string]$DataDir = "C:\ERP_DB\excel_voucher_web_data",
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
  [string]$SslCertFile = "",
  [string]$SslKeyFile = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$Candidates = @(@(
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

& $Python -m pip install -r requirements.txt

$UvicornArgs = @("-m", "uvicorn", "app.main:app", "--host", $HostName, "--port", [string]$Port)
if ($SslCertFile -and $SslKeyFile) {
  $UvicornArgs += @("--ssl-certfile", $SslCertFile, "--ssl-keyfile", $SslKeyFile)
}

& $Python @UvicornArgs
