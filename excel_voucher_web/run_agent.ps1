param(
  [string]$Server = "https://172.17.39.121:8081",
  [string]$AgentId = "finance-agent-172-17-30-243",
  [string]$ClientIp = "",
  [ValidateSet("default-printer", "off")]
  [string]$PrintMode = "default-printer",
  [string]$PrinterName = "",
  [double]$PrintWaitSeconds = 3,
  [switch]$Once,
  [switch]$InsecureSkipTlsVerify
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
    throw "Python 3.11+ is required."
  }
}

$ArgsList = @(
  ".\agent\agent_worker.py",
  "--server", $Server,
  "--agent-id", $AgentId,
  "--print-mode", $PrintMode,
  "--print-wait-seconds", [string]$PrintWaitSeconds
)
if ($ClientIp) {
  $ArgsList += @("--client-ip", $ClientIp)
}
if ($PrinterName) {
  $ArgsList += @("--printer-name", $PrinterName)
}
if ($Once) {
  $ArgsList += "--once"
}
if ($InsecureSkipTlsVerify) {
  $ArgsList += "--insecure-skip-tls-verify"
}

& $Python @ArgsList
