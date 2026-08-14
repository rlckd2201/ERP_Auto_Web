$ErrorActionPreference = "Stop"

$resultPath = "C:\Doc_center\wehago_deploy_result.txt"
$expectedVersion = "1.0.228"
$sourceCommit = "4d87a08"
$sourceBase = "https://raw.githubusercontent.com/rlckd2201/ERP_Auto_Web/$sourceCommit"
$expectedHashes = @{
    "tax_crawler\base_handler.py" = "22b195b2ba9edbba058a37834d179987f18c92dd636e7267ab97ad9bc85fe660"
    "tax_crawler\portal_wehago.py" = "c58da3c4c993b4eaf07ca0a649fbe609a240aff3c9789d5dea893122dd01b59c"
}

function Stop-WebBackend {
    $processes = @(Get-CimInstance Win32_Process)
    $targets = @(
        $processes |
            Where-Object {
                $_.Name -eq "python.exe" -and
                $_.CommandLine -match "-m\s+web_v1\.backend"
            } |
            ForEach-Object { [int]$_.ProcessId }
    )

    $changed = $true
    while ($changed) {
        $changed = $false
        foreach ($process in $processes) {
            if (
                $targets -contains [int]$process.ParentProcessId -and
                $targets -notcontains [int]$process.ProcessId
            ) {
                $targets += [int]$process.ProcessId
                $changed = $true
            }
        }
    }

    try {
        $targets += @(
            Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue |
                ForEach-Object { [int]$_.OwningProcess }
        )
    } catch {}

    $targets = @($targets | Where-Object { $_ -gt 0 } | Sort-Object -Unique -Descending)
    foreach ($processId in $targets) {
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
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

    $tempDir = Join-Path $env:TEMP "wehago_hotfix_20260814"
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
    foreach ($relativePath in $expectedHashes.Keys) {
        $leaf = Split-Path -Leaf $relativePath
        $tempPath = Join-Path $tempDir $leaf
        $urlPath = $relativePath.Replace("\", "/")
        Invoke-WebRequest -UseBasicParsing -Uri "$sourceBase/$urlPath" -OutFile $tempPath
        $downloadHash = (Get-FileHash -LiteralPath $tempPath -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($downloadHash -ne $expectedHashes[$relativePath]) {
            throw "Downloaded hash mismatch for $relativePath"
        }
        $destination = Join-Path $root $relativePath
        Copy-Item -LiteralPath $tempPath -Destination $destination -Force
        $deployedHash = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($deployedHash -ne $expectedHashes[$relativePath]) {
            throw "Deployed hash mismatch for $relativePath"
        }
    }

    Stop-WebBackend
    $env:PYTHONUTF8 = "1"
    $env:PYTHONIOENCODING = "utf-8"
    $env:APP_VERSION = $expectedVersion
    $env:APP_ENV = "production"
    $env:WEB_HOST = "0.0.0.0"
    $env:WEB_PORT = "8080"

    $logDir = "C:\ERP_DB\logs"
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    $python = (Get-Command python -ErrorAction Stop).Source
    $process = Start-Process -FilePath $python -ArgumentList @("-m", "web_v1.backend") `
        -WorkingDirectory $root -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $logDir "web_v1_stdout.log") `
        -RedirectStandardError (Join-Path $logDir "web_v1_stderr.log") -PassThru

    $listening = $false
    foreach ($attempt in 1..30) {
        Start-Sleep -Seconds 1
        if ($process.HasExited) {
            throw "Backend exited during startup with code $($process.ExitCode)"
        }
        try {
            $listener = Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction Stop |
                Select-Object -First 1
            if ($listener) {
                $listening = $true
                break
            }
        } catch {}
    }
    if (-not $listening) {
        throw "Backend did not listen on port 8080; PID=$($process.Id)"
    }

    @(
        "OK"
        "root=$root"
        "pid=$($process.Id)"
        "version=$expectedVersion"
        "source_commit=$sourceCommit"
        "base_handler_sha256=$($expectedHashes['tax_crawler\base_handler.py'])"
        "portal_wehago_sha256=$($expectedHashes['tax_crawler\portal_wehago.py'])"
    ) | Set-Content -LiteralPath $resultPath -Encoding UTF8
} catch {
    @(
        "ERROR"
        $_.Exception.Message
    ) | Set-Content -LiteralPath $resultPath -Encoding UTF8
    throw
}
