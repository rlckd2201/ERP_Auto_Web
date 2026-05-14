$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..\..")
$BackendDir = Join-Path $RepoRoot "web_v1\backend"
$EnvPath = Join-Path $BackendDir ".env"

$DefaultEmailId = "mailsendds@gmail.com"
$DefaultEmailPw = "ttsjfjkqhfwemcfq"
$DefaultGeminiApiKey = "AIzaSyAKPjmvjgP4BzvEzrBJqer9F2DM7onhrcU"
$DefaultServerIp = if ($env:WEB_SERVER_IP) { $env:WEB_SERVER_IP } else { "172.17.39.121" }
$CertDir = "C:\ERP_DB\certs"
$SslCertFile = Join-Path $CertDir "web_v1.cert.pem"
$SslKeyFile = Join-Path $CertDir "web_v1.key.pem"

Set-Location $RepoRoot

Write-Host "[WEB v1.0] Operating server install started"
Write-Host "[WEB v1.0] RepoRoot: $RepoRoot"

$pythonCandidates = @("python", "py -3.11", "py -3")
$pythonCmd = $null
foreach ($candidate in $pythonCandidates) {
    try {
        $cmd = $candidate.Split(" ")[0]
        $args = $candidate.Split(" ")[1..10] | Where-Object { $_ }
        & $cmd @args --version | Out-Null
        if ($LASTEXITCODE -eq 0) {
            $pythonCmd = $candidate
            break
        }
    } catch {}
}

if (-not $pythonCmd) {
    throw "Python command not found. Install Python 3.11 first."
}

Write-Host "[WEB v1.0] Python: $pythonCmd"

New-Item -ItemType Directory -Force -Path "C:\ERP_DB", "C:\ERP_DB\downloads", "C:\ERP_DB\chrome_profile", "C:\ERP_DB\erp_outputs", $CertDir | Out-Null

Write-Host "[WEB v1.0] Installing Python packages"
Invoke-Expression "$pythonCmd -m pip install --upgrade pip"
Invoke-Expression "$pythonCmd -m pip install -r `"$BackendDir\requirements.txt`""
Invoke-Expression "$pythonCmd -m pip install --force-reinstall --no-cache-dir greenlet playwright"
Invoke-Expression "$pythonCmd -m playwright install chromium"

$ForceRenewCert = $env:FORCE_RENEW_HTTPS_CERT -eq "1"
if ($ForceRenewCert -or -not (Test-Path -LiteralPath $SslCertFile) -or -not (Test-Path -LiteralPath $SslKeyFile)) {
    Write-Host "[WEB v1.0] Creating HTTPS certificate for $DefaultServerIp"
    Invoke-Expression "$pythonCmd -m web_v1.backend.tools.create_https_cert `"$CertDir`" $DefaultServerIp 127.0.0.1 localhost"
} else {
    Write-Host "[WEB v1.0] Reusing existing HTTPS certificate: $SslCertFile"
}
Import-Certificate -FilePath $SslCertFile -CertStoreLocation Cert:\CurrentUser\Root | Out-Null
Write-Host "[WEB v1.0] HTTPS certificate trusted for current Windows user"

$emailId = if ($env:EMAIL_ID) { $env:EMAIL_ID } else { $DefaultEmailId }
$emailPw = if ($env:EMAIL_PW) { $env:EMAIL_PW } else { $DefaultEmailPw }
$geminiKey = if ($env:GEMINI_API_KEY) { $env:GEMINI_API_KEY } else { $DefaultGeminiApiKey }

$printers = @()
try {
    $printers = Get-Printer | Select-Object -ExpandProperty Name
} catch {
    Write-Host "[WEB v1.0] Get-Printer failed. Printer names will be requested manually."
}

$ptAuto = $printers | Where-Object { $_ -like "*172.16.10.172*" -or $_ -like "*평택*" } | Select-Object -First 1
$gjAuto = $printers | Where-Object { $_ -like "*172.17.30.162*" -or $_ -like "*김제*" } | Select-Object -First 1

$ptPrinter = if ($env:PRINT_TARGET_PYEONGTAEK) { $env:PRINT_TARGET_PYEONGTAEK } elseif ($ptAuto) { $ptAuto } else { Read-Host "평택 프린터 이름 입력(Get-Printer 결과와 동일)" }
$gjPrinter = if ($env:PRINT_TARGET_GIMJE) { $env:PRINT_TARGET_GIMJE } elseif ($gjAuto) { $gjAuto } else { Read-Host "김제 프린터 이름 입력(Get-Printer 결과와 동일)" }

@"
APP_VERSION=1.0.96
APP_ENV=production

WEB_HOST=0.0.0.0
WEB_PORT=8080
WEB_PUBLIC_ORIGIN=https://$DefaultServerIp:8080
SSL_CERT_FILE=$SslCertFile
SSL_KEY_FILE=$SslKeyFile

ERP_DB_DIR=C:\ERP_DB
DOWNLOAD_DIR=C:\ERP_DB\downloads
CHROME_PROFILE_DIR=C:\ERP_DB\chrome_profile
SQLITE_DB_PATH=C:\ERP_DB\learned_data.db

IMAP_SERVER=imap.gmail.com
EMAIL_ID=$emailId
EMAIL_PW=$emailPw

GEMINI_API_KEY=$geminiKey

PRINT_TARGET_PYEONGTAEK=$ptPrinter
PRINT_TARGET_GIMJE=$gjPrinter
PRINT_TARGET_PDF=Microsoft Print to PDF
ERP_PRINT_TARGET=Microsoft Print to PDF
ERP_OUTPUT_DIR=C:\ERP_DB\erp_outputs
ERP_EXECUTE_ENABLED=1
LEGACY_MANAGER_PATH=$RepoRoot\manager_server\전표 자동화 프로그램(담당자용)_v6.2.py

WORKER_GUI_CONCURRENCY=1
"@ | Set-Content -Path $EnvPath -Encoding UTF8

Write-Host "[WEB v1.0] .env written: $EnvPath"
Write-Host "[WEB v1.0] Install completed"
Write-Host "[WEB v1.0] Start command:"
Write-Host "powershell -ExecutionPolicy Bypass -File `"$RepoRoot\web_v1\deploy\start_operating_server.ps1`""
Write-Host "[WEB v1.0] Browser URL:"
Write-Host "https://$DefaultServerIp:8080"
