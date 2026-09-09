$ErrorActionPreference = "Stop"
$ProjectRoot = "C:\Users\Administrator\Desktop\전표 자동화 프로그램_WEB_Version"
$Python = "C:\Users\Administrator\AppData\Local\Programs\Python\Python311\python.exe"
if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot "web_v1\backend\app.py"))) { throw "Production project root is invalid: $ProjectRoot" }
if (-not (Test-Path -LiteralPath $Python)) { throw "Python not found: $Python" }
$LogDirectory = "C:\ERP_DB\backend_logs"
New-Item -ItemType Directory -Path $LogDirectory -Force | Out-Null
$StdoutPath = Join-Path $LogDirectory "backend_task_stdout.log"
$StderrPath = Join-Path $LogDirectory "backend_task_stderr.log"
$process = Start-Process `
    -FilePath $Python `
    -ArgumentList @("-u", "-m", "web_v1.backend") `
    -WorkingDirectory $ProjectRoot `
    -WindowStyle Hidden `
    -RedirectStandardOutput $StdoutPath `
    -RedirectStandardError $StderrPath `
    -Wait `
    -PassThru
$exitCode = $process.ExitCode
"[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] backend exited: $exitCode" | Out-File -LiteralPath $StderrPath -Encoding utf8 -Append
exit $exitCode
