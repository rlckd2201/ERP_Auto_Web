$ErrorActionPreference = "Stop"

$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptPath "..\..")
$Python = if ($env:PYTHON_EXE) { $env:PYTHON_EXE } else { "python" }
$Agent = Join-Path $RepoRoot "web_v1\agent\erp_agent.py"

Write-Host "[WEB v1.0] Checking user PC ERP Agent environment"
& $Python $Agent --preflight-only --insecure
