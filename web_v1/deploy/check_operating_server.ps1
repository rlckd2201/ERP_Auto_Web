$ErrorActionPreference = "Stop"

Write-Host "[WEB v1.0] Checking backend health"
$health = Invoke-RestMethod -Uri "https://172.17.39.121:8080/health"
$health | Format-List

Write-Host "[WEB v1.0] Checking purchase invoice list API"
$invoices = Invoke-RestMethod -Uri "https://172.17.39.121:8080/api/invoices?mode=purchase"
Write-Host "[WEB v1.0] Purchase invoices: $($invoices.Count)"

Write-Host "[WEB v1.0] Creating demo job"
$job = Invoke-RestMethod -Method Post -Uri "https://172.17.39.121:8080/api/jobs/demo"
Write-Host "[WEB v1.0] Job id: $($job.id)"

Start-Sleep -Seconds 4
$detail = Invoke-RestMethod -Uri ("https://172.17.39.121:8080/api/jobs/" + $job.id)
$detail | Select-Object id,status,progress,message | Format-List
