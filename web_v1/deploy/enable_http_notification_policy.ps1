$ErrorActionPreference = "Stop"

$Origin = if ($env:WEB_NOTIFICATION_ORIGIN) { $env:WEB_NOTIFICATION_ORIGIN } else { "http://172.17.39.121:8080" }

Write-Host "[WEB v1.0] Enabling browser notification workaround for: $Origin"
Write-Host "[WEB v1.0] This must be run on every PC/browser profile that opens the WEB page by HTTP IP."

$policyTargets = @(
    "HKCU:\Software\Policies\Google\Chrome\UnsafelyTreatInsecureOriginAsSecure",
    "HKCU:\Software\Policies\Microsoft\Edge\UnsafelyTreatInsecureOriginAsSecure"
)

foreach ($target in $policyTargets) {
    New-Item -Path $target -Force | Out-Null
    New-ItemProperty -Path $target -Name "1" -Value $Origin -PropertyType String -Force | Out-Null
    Write-Host "[WEB v1.0] Policy written: $target"
}

Write-Host ""
Write-Host "[WEB v1.0] Next steps:"
Write-Host "1. Close every Chrome/Edge window completely."
Write-Host "2. Open Chrome/Edge again."
Write-Host "3. Open $Origin"
Write-Host "4. Click the address-bar '주의 요함' icon > Site settings > reset or allow Notifications."
Write-Host "5. Click '알림 허용' in WEB v1.0 again."
Write-Host ""
Write-Host "[WEB v1.0] To verify Chrome policy, open chrome://policy and reload policies."
Write-Host "[WEB v1.0] To verify Edge policy, open edge://policy and reload policies."
