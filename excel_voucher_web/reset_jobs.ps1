param(
  [string]$DataDir = "C:\ERP_DB\excel_voucher_web_data",
  [switch]$ClearUploads,
  [switch]$Force
)

$ErrorActionPreference = "Stop"

if (-not $Force) {
  throw "Use -Force to clear voucher jobs. Accounts and passwords are preserved."
}

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
    throw "Python 3.11+ is required."
  }
}

$DbPath = Join-Path $DataDir "excel_voucher.sqlite3"
if (-not (Test-Path $DbPath)) {
  Write-Host "DB not found: $DbPath"
} else {
  $env:EXCEL_VOUCHER_RESET_DB = $DbPath
  & $Python -c "import os, sqlite3; db=os.environ['EXCEL_VOUCHER_RESET_DB']; conn=sqlite3.connect(db); conn.execute('DELETE FROM job_events'); conn.execute('DELETE FROM jobs'); conn.commit(); conn.close(); print('Cleared jobs and job_events:', db)"
}

if ($ClearUploads) {
  $Uploads = Join-Path $DataDir "uploads"
  if (Test-Path $Uploads) {
    Get-ChildItem -LiteralPath $Uploads -Force | Remove-Item -Recurse -Force
    Write-Host "Cleared uploads: $Uploads"
  }
}
