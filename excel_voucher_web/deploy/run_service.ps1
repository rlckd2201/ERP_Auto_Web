param(
  [Parameter(Mandatory=$true)][string]$AppRoot,
  [Parameter(Mandatory=$true)][string]$ConfigFile,
  [Parameter(Mandatory=$true)][string]$CertFile,
  [Parameter(Mandatory=$true)][string]$KeyFile
)
$ErrorActionPreference = 'Stop'
$Config = Get-Content -LiteralPath $ConfigFile -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($Property in $Config.PSObject.Properties) {
  if ($Property.Name -notmatch '^EXCEL_VOUCHER_[A-Z0-9_]+$') { throw 'Invalid environment key' }
  [Environment]::SetEnvironmentVariable($Property.Name, [string]$Property.Value, 'Process')
}
$Python = Join-Path $AppRoot '.venv\Scripts\python.exe'
foreach ($Path in @($Python, $CertFile, $KeyFile)) {
  if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Required file not found: $Path" }
}
Set-Location -LiteralPath $AppRoot
$Logs = Join-Path $env:EXCEL_VOUCHER_DATA_DIR 'service_logs'
New-Item -ItemType Directory -Path $Logs -Force | Out-Null
$env:PYTHONIOENCODING = 'utf-8'
$LogFile = Join-Path $Logs ('web-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
$Arguments = @('-m', 'uvicorn', 'app.main:app', '--host', $env:EXCEL_VOUCHER_WEB_HOST,
  '--port', $env:EXCEL_VOUCHER_WEB_PORT, '--ssl-certfile', ('"' + $CertFile + '"'),
  '--ssl-keyfile', ('"' + $KeyFile + '"'))
$Process = Start-Process -FilePath $Python -ArgumentList $Arguments -WorkingDirectory $AppRoot `
  -WindowStyle Hidden -RedirectStandardOutput ($LogFile + '.out.log') `
  -RedirectStandardError ($LogFile + '.err.log') -Wait -PassThru
exit $Process.ExitCode
