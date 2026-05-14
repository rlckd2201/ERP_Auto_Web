$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..\..")
Set-Location $RepoRoot

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

$LegacyConfig = Join-Path $RepoRoot "manager_server\config.ini"
$SupportConfig = Join-Path $RepoRoot "support\config.ini"
if (-not (Test-Path -LiteralPath $LegacyConfig) -and (Test-Path -LiteralPath $SupportConfig)) {
    Copy-Item -LiteralPath $SupportConfig -Destination $LegacyConfig -Force
    Write-Host "[WEB v1.0] ERP config initialized from support\config.ini"
}

Write-Host "[WEB v1.0] Starting backend at https://0.0.0.0:8080"
Write-Host "[WEB v1.0] Browser URL: https://172.17.39.121:8080"
Invoke-Expression "$pythonCmd -m web_v1.backend"
