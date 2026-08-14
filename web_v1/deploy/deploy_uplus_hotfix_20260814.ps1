$ErrorActionPreference = "Stop"

$resultPath = "C:\Doc_center\uplus_deploy_result.txt"
$expectedVersion = "1.0.228"
$sourceCommit = "e42d7f8"
$sourceBase = "https://raw.githubusercontent.com/rlckd2201/ERP_Auto_Web/$sourceCommit"
$expectedHashes = @{
    "support\uplus_handler.py" = "8efa55a0868c4ed2c86697f024a5eddea3c9f207075ed0794990cf51b753affb"
    "tax_crawler\uplus_handler.py" = "8efa55a0868c4ed2c86697f024a5eddea3c9f207075ed0794990cf51b753affb"
    "tax_crawler\portal_uplus.py" = "3e12e8a17a3dda8aea98dff1799d4362d20ed51cde84cc48bec89e9cf0c2a253"
}

try {
    "RUNNING" | Set-Content -LiteralPath $resultPath -Encoding UTF8
    $versionFile = Get-ChildItem -LiteralPath "C:\Users\Administrator\Desktop" -Filter VERSION -Recurse -ErrorAction SilentlyContinue |
        Where-Object {
            $_.FullName -notmatch "\\_apply_" -and
            (Get-Content -LiteralPath $_.FullName -Raw).Trim() -eq $expectedVersion
        } |
        Select-Object -First 1
    if (-not $versionFile) {
        throw "Active $expectedVersion source root not found"
    }

    $root = $versionFile.Directory.Parent.FullName
    $tempDir = Join-Path $env:TEMP "uplus_hotfix_20260814"
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

    foreach ($relativePath in $expectedHashes.Keys) {
        $leaf = Split-Path -Leaf $relativePath
        $tempPath = Join-Path $tempDir $leaf
        $urlPath = $relativePath.Replace("\", "/")
        Invoke-WebRequest -UseBasicParsing -Uri "$sourceBase/$urlPath" -OutFile $tempPath
        $actualHash = (Get-FileHash -LiteralPath $tempPath -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actualHash -ne $expectedHashes[$relativePath]) {
            throw "Hash mismatch for $relativePath"
        }
        Copy-Item -LiteralPath $tempPath -Destination (Join-Path $root $relativePath) -Force
    }

    Get-CimInstance Win32_Process |
        Where-Object { $_.Name -eq "python.exe" -and $_.CommandLine -match "-m\s+web_v1\.backend" } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 1

    $env:PYTHONUTF8 = "1"
    $env:PYTHONIOENCODING = "utf-8"
    $env:APP_VERSION = $expectedVersion
    $env:APP_ENV = "production"
    $env:WEB_HOST = "0.0.0.0"
    $env:WEB_PORT = "8080"
    $env:WEB_PUBLIC_ORIGIN = "http://172.17.39.121:8080"
    $logDir = "C:\ERP_DB\logs"
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    $python = (Get-Command python -ErrorAction Stop).Source
    $process = Start-Process -FilePath $python -ArgumentList @("-m", "web_v1.backend") `
        -WorkingDirectory $root -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $logDir "web_v1_stdout.log") `
        -RedirectStandardError (Join-Path $logDir "web_v1_stderr.log") -PassThru

    $health = $null
    foreach ($attempt in 1..30) {
        Start-Sleep -Seconds 1
        try {
            $health = Invoke-RestMethod -Uri "http://127.0.0.1:8080/health" -TimeoutSec 2
            break
        } catch {}
    }
    if (-not $health) {
        throw "Backend failed to become healthy; PID=$($process.Id)"
    }

    @(
        "OK"
        "root=$root"
        "pid=$($process.Id)"
        "version=$($health.version)"
        "source_commit=$sourceCommit"
    ) | Set-Content -LiteralPath $resultPath -Encoding UTF8
} catch {
    @(
        "ERROR"
        $_.Exception.Message
    ) | Set-Content -LiteralPath $resultPath -Encoding UTF8
    throw
}
