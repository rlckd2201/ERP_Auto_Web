param(
  [string]$Server = "http://127.0.0.1:18100",
  [string]$AgentId = "finance-agent-172-17-30-243",
  [string]$ClientIp = "",
  [switch]$Once
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
    throw "Python 3.11+ 설치가 필요합니다."
  }
}

$ArgsList = @(".\agent\agent_worker.py", "--server", $Server, "--agent-id", $AgentId)
if ($ClientIp) {
  $ArgsList += @("--client-ip", $ClientIp)
}
if ($Once) {
  $ArgsList += "--once"
}

& $Python @ArgsList
