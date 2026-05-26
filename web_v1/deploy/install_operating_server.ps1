$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..\..")
$BackendDir = Join-Path $RepoRoot "web_v1\backend"
$EnvPath = Join-Path $BackendDir ".env"

$DefaultEmailId = "mailsendds@gmail.com"
$DefaultEmailPw = "ttsjfjkqhfwemcfq"
$DefaultPasswordResetDomain = "dae-seung.co.kr"
$DefaultPasswordResetSmtpServer = "35.216.76.148"
$DefaultPasswordResetSmtpPort = "25"
$DefaultPasswordResetUser = "admpdm"
$DefaultPasswordResetPw = "eotmd12#$"
$DefaultPasswordResetFrom = "admpdm@dae-seung.co.kr"
$DefaultRegularAutoResultFromName = "회계처리프로그램"
$DefaultGeminiApiKey = ""
$DefaultServerIp = if ($env:WEB_SERVER_IP) { $env:WEB_SERVER_IP } else { "172.17.39.121" }
$DefaultPyeongtaekPrinter = "평택 프린터 (172.16.10.172)"
$DefaultRegularAutoAgentIp = if ($env:REGULAR_AUTO_AGENT_IP) { $env:REGULAR_AUTO_AGENT_IP } else { "172.17.30.243" }
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

$existingEnv = @{}
if (Test-Path -LiteralPath $EnvPath) {
    Get-Content -LiteralPath $EnvPath | ForEach-Object {
        if ($_ -match "^\s*([^#=]+)=(.*)$") {
            $existingEnv[$matches[1].Trim()] = $matches[2].Trim()
        }
    }
}

function Resolve-EnvValue([string]$Key, [string]$DefaultValue = "") {
    $value = [Environment]::GetEnvironmentVariable($Key)
    if ($null -ne $value -and $value -ne "") {
        return $value
    }
    if ($script:existingEnv.ContainsKey($Key) -and $script:existingEnv[$Key]) {
        return $script:existingEnv[$Key]
    }
    return $DefaultValue
}

$emailId = Resolve-EnvValue "EMAIL_ID" $DefaultEmailId
$emailPw = Resolve-EnvValue "EMAIL_PW" $DefaultEmailPw
$existingGeminiKey = Resolve-EnvValue "GEMINI_API_KEY" ""
$geminiKey = if ($env:GEMINI_API_KEY) { $env:GEMINI_API_KEY } elseif ($existingGeminiKey) { $existingGeminiKey } else { $DefaultGeminiApiKey }
$passwordResetDomain = if ($env:PASSWORD_RESET_MAIL_DOMAIN) { $env:PASSWORD_RESET_MAIL_DOMAIN } else { $DefaultPasswordResetDomain }
$passwordResetSmtpServer = if ($env:PASSWORD_RESET_SMTP_SERVER) { $env:PASSWORD_RESET_SMTP_SERVER } else { $DefaultPasswordResetSmtpServer }
$passwordResetSmtpPort = if ($env:PASSWORD_RESET_SMTP_PORT) { $env:PASSWORD_RESET_SMTP_PORT } else { $DefaultPasswordResetSmtpPort }
$passwordResetUser = if ($env:PASSWORD_RESET_SMTP_USER) { $env:PASSWORD_RESET_SMTP_USER } else { $DefaultPasswordResetUser }
$passwordResetPw = if ($env:PASSWORD_RESET_SMTP_PW) { $env:PASSWORD_RESET_SMTP_PW } else { $DefaultPasswordResetPw }
$passwordResetFrom = if ($env:PASSWORD_RESET_FROM) { $env:PASSWORD_RESET_FROM } else { $DefaultPasswordResetFrom }

$printers = @()
try {
    $printers = Get-Printer | Select-Object -ExpandProperty Name
} catch {
    Write-Host "[WEB v1.0] Get-Printer failed. Printer names will be requested manually."
}

$ptAuto = $printers | Where-Object { $_ -like "*172.16.10.172*" -or $_ -like "*평택*" } | Select-Object -First 1
$gjAuto = $printers | Where-Object { $_ -like "*172.17.30.162*" -or $_ -like "*김제*" } | Select-Object -First 1

$ptPrinter = if ($env:PRINT_TARGET_PYEONGTAEK) { $env:PRINT_TARGET_PYEONGTAEK } elseif ($ptAuto) { $ptAuto } else { $DefaultPyeongtaekPrinter }
$gjPrinter = if ($env:PRINT_TARGET_GIMJE) { $env:PRINT_TARGET_GIMJE } elseif ($gjAuto) { $gjAuto } else { Read-Host "김제 프린터 이름 입력(Get-Printer 결과와 동일)" }
$regularAutoPrinterKey = if ($env:REGULAR_AUTO_PRINTER_KEY) { $env:REGULAR_AUTO_PRINTER_KEY } else { "pyeongtaek" }
$regularAutoResultFromName = if ($env:REGULAR_AUTO_RESULT_FROM_NAME) { $env:REGULAR_AUTO_RESULT_FROM_NAME } else { $DefaultRegularAutoResultFromName }
$regularAutoResultFrom = if ($env:REGULAR_AUTO_RESULT_FROM) { $env:REGULAR_AUTO_RESULT_FROM } else { $passwordResetFrom }
$regularAutoResultSmtpServer = if ($env:REGULAR_AUTO_RESULT_SMTP_SERVER) { $env:REGULAR_AUTO_RESULT_SMTP_SERVER } else { $passwordResetSmtpServer }
$regularAutoResultSmtpPort = if ($env:REGULAR_AUTO_RESULT_SMTP_PORT) { $env:REGULAR_AUTO_RESULT_SMTP_PORT } else { $passwordResetSmtpPort }
$regularAutoResultSmtpUser = if ($env:REGULAR_AUTO_RESULT_SMTP_USER) { $env:REGULAR_AUTO_RESULT_SMTP_USER } else { $passwordResetUser }
$regularAutoResultSmtpPw = if ($env:REGULAR_AUTO_RESULT_SMTP_PW) { $env:REGULAR_AUTO_RESULT_SMTP_PW } else { $passwordResetPw }

@"
APP_VERSION=1.0.146
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

PASSWORD_RESET_MAIL_DOMAIN=$passwordResetDomain
PASSWORD_RESET_SMTP_SERVER=$passwordResetSmtpServer
PASSWORD_RESET_SMTP_PORT=$passwordResetSmtpPort
PASSWORD_RESET_SMTP_USER=$passwordResetUser
PASSWORD_RESET_SMTP_PW=$passwordResetPw
PASSWORD_RESET_FROM=$passwordResetFrom

GEMINI_API_KEY=$geminiKey

PRINT_TARGET_PYEONGTAEK=$ptPrinter
PRINT_TARGET_GIMJE=$gjPrinter
PRINT_TARGET_PDF=Microsoft Print to PDF
ERP_PRINT_TARGET=Microsoft Print to PDF
ERP_OUTPUT_DIR=C:\ERP_DB\erp_outputs
ERP_EXECUTE_ENABLED=1
LEGACY_MANAGER_PATH=$RepoRoot\manager_server\전표 자동화 프로그램(담당자용)_v6.2.py

REGULAR_AUTO_ENABLED=1
REGULAR_AUTO_AGENT_IP=$DefaultRegularAutoAgentIp
REGULAR_AUTO_PRINTER_KEY=$regularAutoPrinterKey
REGULAR_AUTO_INTERVAL_SECONDS=60
REGULAR_AUTO_SCAN_LIMIT=200
REGULAR_AUTO_MAX_BATCH=20
REGULAR_AUTO_RESULT_EMAIL=ds1501@dae-seung.co.kr
REGULAR_AUTO_RESULT_EMAIL_ENABLED=1
REGULAR_AUTO_RESULT_FROM_NAME=$regularAutoResultFromName
REGULAR_AUTO_RESULT_FROM=$regularAutoResultFrom
REGULAR_AUTO_RESULT_SMTP_SERVER=$regularAutoResultSmtpServer
REGULAR_AUTO_RESULT_SMTP_PORT=$regularAutoResultSmtpPort
REGULAR_AUTO_RESULT_SMTP_USER=$regularAutoResultSmtpUser
REGULAR_AUTO_RESULT_SMTP_PW=$regularAutoResultSmtpPw

WORKER_GUI_CONCURRENCY=1
"@ | Set-Content -Path $EnvPath -Encoding UTF8

Write-Host "[WEB v1.0] .env written: $EnvPath"
Write-Host "[WEB v1.0] Install completed"
Write-Host "[WEB v1.0] Start command:"
Write-Host "powershell -ExecutionPolicy Bypass -File `"$RepoRoot\web_v1\deploy\start_operating_server.ps1`""
Write-Host "[WEB v1.0] Browser URL:"
Write-Host "https://$DefaultServerIp:8080"


