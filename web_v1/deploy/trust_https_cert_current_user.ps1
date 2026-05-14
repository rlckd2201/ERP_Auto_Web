$ErrorActionPreference = "Stop"

$CertPath = if ($env:WEB_V1_CERT_PATH) { $env:WEB_V1_CERT_PATH } else { "C:\ERP_DB\certs\web_v1.cert.pem" }

if (-not (Test-Path $CertPath)) {
    throw "Certificate file not found: $CertPath"
}

Import-Certificate -FilePath $CertPath -CertStoreLocation Cert:\CurrentUser\Root | Out-Null
Write-Host "[WEB v1.0] Trusted certificate for CurrentUser Root: $CertPath"

try {
    Import-Certificate -FilePath $CertPath -CertStoreLocation Cert:\LocalMachine\Root | Out-Null
    Write-Host "[WEB v1.0] Trusted certificate for LocalMachine Root: $CertPath"
} catch {
    Write-Host "[WEB v1.0] LocalMachine Root trust skipped. Run PowerShell as administrator if this PC still shows a certificate warning."
}

Write-Host ""
Write-Host "[WEB v1.0] Next steps:"
Write-Host "1. Close every Chrome/Edge window completely."
Write-Host "2. Open Chrome/Edge again."
Write-Host "3. Open https://172.17.39.121:8080"
Write-Host "4. If the warning remains, run this script from an Administrator PowerShell on the PC that opens the browser."
