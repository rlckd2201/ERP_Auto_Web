param(
  [string]$HostName = "0.0.0.0",
  [int]$Port = 8081,
  [string]$PublicOrigin = "https://172.17.39.121:8081",
  [string]$DataServerUrl = "http://127.0.0.1:18080",
  [string]$DataServerEndpoint = "/api/excel-voucher/jobs",
  [switch]$ForwardToDataServer,
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
$env:EXCEL_VOUCHER_DATA_SERVER_URL = $DataServerUrl
$env:EXCEL_VOUCHER_DATA_SERVER_ENDPOINT = $DataServerEndpoint
$env:EXCEL_VOUCHER_FORWARD_TO_DATA_SERVER = if ($ForwardToDataServer) { "1" } else { "0" }

& $Python -m pip install -r requirements.txt

$UvicornArgs = @("-m", "uvicorn", "app.main:app", "--host", $HostName, "--port", [string]$Port)
if ($SslCertFile -and $SslKeyFile) {
  $UvicornArgs += @("--ssl-certfile", $SslCertFile, "--ssl-keyfile", $SslKeyFile)
}

& $Python @UvicornArgs
