$ErrorActionPreference = "Stop"

$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptPath "..\..")
$ServerUrl = if ($env:WEB_SERVER_URL) { $env:WEB_SERVER_URL } else { "https://172.17.39.121:8080" }
$Agent = Join-Path $RepoRoot "web_v1\agent\erp_agent.py"

function Resolve-PythonExe {
    $candidates = @(
        $env:PYTHON_EXE,
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "python",
        "py"
    )
    foreach ($candidate in $candidates) {
        if (-not $candidate) { continue }
        try {
            if ($candidate -like "*\*" -and -not (Test-Path $candidate)) { continue }
            & $candidate --version *> $null
            if ($LASTEXITCODE -eq 0) { return $candidate }
        } catch {}
    }
    throw "Python 3.11 이상을 찾지 못했습니다. Python 설치 후 다시 실행하세요."
}

$Python = Resolve-PythonExe

try {
    $RunScript = Join-Path $RepoRoot "담당자PC_필수프로그램_실행.ps1"
    if (-not (Test-Path $RunScript)) {
@"
`$ErrorActionPreference = "Stop"
`$Root = "$RepoRoot"
`$env:WEB_SERVER_URL = "$ServerUrl"
`$env:PYTHON_EXE = "$Python"
powershell -ExecutionPolicy Bypass -File "`$Root\web_v1\deploy\start_user_erp_agent.ps1"
"@ | Set-Content -Path $RunScript -Encoding UTF8
    }
    $ProtocolKey = "HKCU:\Software\Classes\accountingweb"
    $CommandKey = Join-Path $ProtocolKey "shell\open\command"
    New-Item -Path $CommandKey -Force | Out-Null
    Set-Item -Path $ProtocolKey -Value "URL:Accounting WEB 필수 프로그램"
    New-ItemProperty -Path $ProtocolKey -Name "URL Protocol" -Value "" -PropertyType String -Force | Out-Null
    $PowerShellExe = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
    Set-Item -Path $CommandKey -Value "`"$PowerShellExe`" -NoProfile -ExecutionPolicy Bypass -File `"$RunScript`""
    Write-Host "[WEB v1.0] Login auto-start registered: accountingweb://start"
} catch {
    Write-Host "[WEB v1.0] Login auto-start registration skipped: $($_.Exception.Message)"
}

Write-Host "[WEB v1.0] Starting user PC ERP Agent"
Write-Host "[WEB v1.0] Server: $ServerUrl"
Write-Host "[WEB v1.0] Agent: $Agent"
Write-Host "[WEB v1.0] Python: $Python"

& $Python -m pip install -r (Join-Path $RepoRoot "web_v1\backend\requirements.txt")

$AgentArgs = "`"$Agent`" --server `"$ServerUrl`" --insecure"
Start-Process -FilePath $Python -ArgumentList $AgentArgs -WindowStyle Hidden
Write-Host "[WEB v1.0] User PC ERP Agent started in background tray mode"
