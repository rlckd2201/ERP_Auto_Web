param([switch]$LibraryOnly)
$ErrorActionPreference = 'Stop'

function Quote-NativeArgument([string]$Value) {
    '"' + [regex]::Replace([regex]::Replace($Value, '(\\*)"', '$1$1\"'), '(\\+)$', '$1$1') + '"'
}
function Protect-Output([string]$Value) {
    $Value = [regex]::Replace($Value, '(https?://)[^\s/@]+:[^\s/@]+@', '$1[redacted]@')
    $Value = [regex]::Replace($Value, '(https?://[^\s?]+)\?[^\s]+', '$1?[redacted]')
    [regex]::Replace($Value, '(?im)((?:password|token|secret|authorization)\s*[:=]\s*)\S+', '$1[redacted]')
}
function Invoke-Native([string]$Exe, [string[]]$Arguments, [int]$Seconds = 90) {
    $info = New-Object Diagnostics.ProcessStartInfo
    $info.FileName = $Exe
    $info.Arguments = ($Arguments | ForEach-Object { Quote-NativeArgument $_ }) -join ' '
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $true
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    $info.EnvironmentVariables['PYTHONIOENCODING'] = 'utf-8'
    $info.StandardOutputEncoding = [Text.Encoding]::UTF8
    $info.StandardErrorEncoding = [Text.Encoding]::UTF8
    $process = [Diagnostics.Process]::Start($info)
    $stdout = $process.StandardOutput.ReadToEndAsync()
    $stderr = $process.StandardError.ReadToEndAsync()
    if (-not $process.WaitForExit($Seconds * 1000)) {
        try { $process.Kill() } catch {}
        throw "Command timed out after $Seconds seconds; stop here and report the result."
    }
    $process.WaitForExit()
    $result = [pscustomobject]@{ exit_code = $process.ExitCode; stdout = $stdout.Result; stderr = $stderr.Result }
    $process.Dispose()
    $result
}
function Invoke-Python([string]$Exe, [string]$Code, [string[]]$Extra = @()) {
    $encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($Code))
    Invoke-Native $Exe (@('-c', "exec(__import__('base64').b64decode('$encoded'))") + $Extra)
}
function Read-LauncherPython([string]$Text) {
    $match = [regex]::Match($Text, '(?im)^\s*\$env:PYTHON_EXE\s*=\s*["'']([^"''\r\n]+)["'']\s*$')
    if ($match.Success) { return [Environment]::ExpandEnvironmentVariables($match.Groups[1].Value) }
    return ''
}
function Get-PythonProbe([string]$Exe) {
    $code = @'
import contextlib,importlib,io,json,site,struct,sys
modules=['requests','fastapi','uvicorn','pydantic','httpx','pyautogui','pyperclip','pywinauto','psutil','win32gui','win32con','win32print','fitz','PIL','openpyxl','cryptography','truststore','selenium','bs4','pdfplumber','pypdfium2','google.genai','playwright']
checks={}
for name in modules:
    try:
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()): importlib.import_module(name)
        checks[name]='ok'
    except Exception as exc: checks[name]=type(exc).__name__
print(json.dumps(dict(executable=sys.executable,version=list(sys.version_info[:3]),bits=struct.calcsize('P')*8,user_site=site.getusersitepackages(),modules=checks,all_ok=all(v=='ok' for v in checks.values()))))
'@
    try {
        $run = Invoke-Python $Exe $code
        if ($run.exit_code -ne 0) { return $null }
        return ($run.stdout.Trim() | ConvertFrom-Json)
    } catch { return $null }
}
function Get-Candidates([string]$Configured) {
    $items = New-Object 'Collections.Generic.List[string]'
    foreach ($value in @($Configured, $env:PYTHON_EXE,
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe")) {
        if ($value -and (Test-Path -LiteralPath $value -PathType Leaf)) { $items.Add($value) }
    }
    foreach ($hive in @([Microsoft.Win32.RegistryHive]::CurrentUser, [Microsoft.Win32.RegistryHive]::LocalMachine)) {
        foreach ($view in @([Microsoft.Win32.RegistryView]::Registry64, [Microsoft.Win32.RegistryView]::Registry32)) {
            $base = [Microsoft.Win32.RegistryKey]::OpenBaseKey($hive, $view)
            $core = $base.OpenSubKey('Software\Python\PythonCore')
            if ($core) {
                foreach ($version in $core.GetSubKeyNames()) {
                    $key = $core.OpenSubKey("$version\InstallPath")
                    if ($key) {
                        $value = [string]$key.GetValue('ExecutablePath')
                        if (-not $value -and $key.GetValue('')) { $value = Join-Path ([string]$key.GetValue('')) 'python.exe' }
                        if ($value -and (Test-Path -LiteralPath $value -PathType Leaf)) { $items.Add($value) }
                        $key.Dispose()
                    }
                }
                $core.Dispose()
            }
            $base.Dispose()
        }
    }
    foreach ($name in @('python.exe','py.exe')) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command -and $command.Source -notmatch 'WindowsApps\\python') { $items.Add($command.Source) }
    }
    @($items | Select-Object -Unique)
}
function Add-Step([string]$Name, $Result) {
    $script:Report.steps.Add([pscustomobject]@{name=$Name;result=$Result;time=(Get-Date -Format o)})
}
function Require-Success([string]$Name, $Run) {
    $tail = (($Run.stdout + "`n" + $Run.stderr) -split '\r?\n' | Select-Object -Last 18) -join "`n"
    Add-Step $Name @{exit_code=$Run.exit_code;output=(Protect-Output $tail)}
    if ($Run.exit_code -ne 0) { throw "$Name failed (exit $($Run.exit_code)). See the Desktop result file." }
}
function Get-AgentProcesses {
    @(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" | Where-Object { $_.CommandLine -match 'erp_agent\.py' })
}
function New-Launcher([string]$Root, [string]$Python, [string]$Server) {
    $r = $Root.Replace("'", "''"); $p = $Python.Replace("'", "''"); $s = $Server.Replace("'", "''")
    @"
`$ErrorActionPreference = 'Stop'
`$Root = '$r'
`$env:WEB_SERVER_URL = '$s'
`$env:PYTHON_EXE = '$p'
`$env:REQUESTS_CA_BUNDLE = 'C:\ERP_DB\certs\web_v1.cert.pem'
powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "`$Root\web_v1\deploy\start_user_erp_agent.ps1"
"@
}
if ($LibraryOnly) { return }

$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$resultPath = Join-Path ([Environment]::GetFolderPath('Desktop')) "AccountingWeb_Repair_$stamp.json"
$script:Report = [ordered]@{created_at=(Get-Date -Format o);computer=$env:COMPUTERNAME;user=$env:USERNAME;status='started';steps=(New-Object 'Collections.Generic.List[object]')}
$exitCode = 1
try {
    Write-Host '현시훈 PC 회계 프로그램 복구를 시작합니다. 완료될 때까지 창을 닫지 마세요.'
    if ($env:COMPUTERNAME -ne '현시훈PC' -or $env:USERNAME -ne '현시훈') { throw 'This repair is for 현시훈PC / 현시훈 only. No repair was applied.' }
    $existing = Get-AgentProcesses
    if ($existing.Count -gt 0) {
        Add-Step 'existing_agent' @($existing | ForEach-Object { [int]$_.ProcessId })
        $script:Report.status = 'already_running_server_check_needed'
        Write-Host 'Agent가 이미 실행 중입니다. 중복 실행하지 않았습니다. 결과 파일을 전달해 주세요.'
        $exitCode = 0
    } else {
        $key = Get-Item -LiteralPath 'HKCU:\Software\Classes\accountingweb\shell\open\command'
        $command = [string]$key.GetValue('')
        $match = [regex]::Match($command, '(?i)-File\s+"([^"\r\n]+\.ps1)"')
        if (-not $match.Success) { throw 'Registered launcher path could not be verified.' }
        $launcher = [IO.Path]::GetFullPath([Environment]::ExpandEnvironmentVariables($match.Groups[1].Value))
        $root = Split-Path -Parent $launcher
        $userRoot = [IO.Path]::GetFullPath($env:USERPROFILE).TrimEnd('\') + '\'
        if (-not $launcher.StartsWith($userRoot, [StringComparison]::OrdinalIgnoreCase)) { throw 'Launcher is outside this Windows user profile.' }
        $agent = Join-Path $root 'web_v1\agent\erp_agent.py'
        $requirements = Join-Path $root 'web_v1\backend\requirements.txt'
        foreach ($path in @($launcher,$agent,$requirements)) { if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing file: $path" } }
        $text = [IO.File]::ReadAllText($launcher)
        $configured = Read-LauncherPython $text
        Add-Step 'launcher' @{path=$launcher;configured_python=$configured;version=([IO.File]::ReadAllText((Join-Path $root 'web_v1\VERSION')).Trim())}
        Write-Host '1/4 실제 Python과 필수 패키지를 검사합니다.'
        $probes = @()
        foreach ($candidate in (Get-Candidates $configured)) {
            $probe = Get-PythonProbe $candidate
            if ($probe -and $probe.executable -notin @($probes | ForEach-Object {$_.executable})) { $probes += $probe }
        }
        Add-Step 'python_before' $probes
        $good = @($probes | Where-Object { $_.all_ok -and $_.version[0] -eq 3 -and $_.version[1] -ge 11 } | Select-Object -First 1)
        if ($good.Count -gt 0) { $python = $good[0].executable }
        else {
            Write-Host '2/4 회계 프로그램용 Python 3.11 실행환경을 준비합니다.'
            $base311 = @($probes | Where-Object { $_.version[0] -eq 3 -and $_.version[1] -eq 11 -and $_.bits -eq 64 } | Select-Object -First 1)
            if ($base311.Count -eq 0) {
                $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
                if (-not $winget) { throw 'WinGet is unavailable; Python 3.11 installation needs support. Result saved.' }
                $run = Invoke-Native $winget.Source @('install','--id','Python.Python.3.11','--exact','--scope','user','--silent','--accept-package-agreements','--accept-source-agreements','--disable-interactivity','--source','winget') 900
                Require-Success 'install_python311' $run
                $probes311 = @(Get-Candidates '' | ForEach-Object { Get-PythonProbe $_ } | Where-Object { $_ })
                $base311 = @($probes311 | Where-Object { $_.version[0] -eq 3 -and $_.version[1] -eq 11 -and $_.bits -eq 64 } | Select-Object -First 1)
                if ($base311.Count -eq 0) { throw 'Python 3.11 x64 was not found after installation.' }
            }
            $runtime = Join-Path $env:LOCALAPPDATA "AccountingWeb\RecoveryRuntime_$stamp"
            Require-Success 'create_isolated_runtime' (Invoke-Native $base311[0].executable @('-m','venv',$runtime) 180)
            $python = Join-Path $runtime 'Scripts\python.exe'
            Write-Host '필수 패키지를 설치하고 있습니다. 인터넷 속도에 따라 몇 분 걸릴 수 있습니다.'
            Require-Success 'install_packages' (Invoke-Native $python @('-m','pip','install','--disable-pip-version-check','--retries','1','--timeout','20','-r',$requirements) 900)
        }
        $after = Get-PythonProbe $python
        Add-Step 'python_after' $after
        if (-not $after -or -not $after.all_ok) { throw 'Required package imports still fail; launcher was not changed.' }
        Write-Host '3/4 Python에서 서버 HTTPS 연결을 확인합니다.'
        $server = 'https://172.16.19.105:3010'
        $cert = 'C:\ERP_DB\certs\web_v1.cert.pem'
        if (-not (Test-Path -LiteralPath $cert -PathType Leaf)) { throw 'The installed server certificate is missing.' }
        $networkCode = "import requests,sys,json; r=requests.get(sys.argv[1]+'/api/version',verify=sys.argv[2],timeout=10); r.raise_for_status(); print(json.dumps({'status':r.status_code,'version':r.json().get('version')}))"
        Require-Success 'python_https' (Invoke-Python $python $networkCode @($server,$cert))
        if ((Get-AgentProcesses).Count -gt 0) { throw 'An Agent started during repair. It was left untouched; report this result.' }
        $backup = $launcher + '.before_repair_' + $stamp
        Copy-Item -LiteralPath $launcher -Destination $backup -ErrorAction Stop
        [IO.File]::WriteAllText($launcher, (New-Launcher $root $python $server), (New-Object Text.UTF8Encoding($true)))
        Add-Step 'launcher_backup' $backup
        Write-Host '4/4 Agent를 시작합니다.'
        $env:REQUESTS_CA_BUNDLE = $cert
        $env:WEB_SERVER_URL = $server
        $env:PYTHON_EXE = $python
        $pythonw = Join-Path (Split-Path -Parent $python) 'pythonw.exe'
        if (-not (Test-Path -LiteralPath $pythonw)) { $pythonw = $python }
        $argsText = (@($agent,'--server',$server) | ForEach-Object { Quote-NativeArgument $_ }) -join ' '
        $process = Start-Process -FilePath $pythonw -ArgumentList $argsText -WorkingDirectory $root -WindowStyle Hidden -PassThru
        Start-Sleep -Seconds 15
        $running = Get-AgentProcesses
        Add-Step 'agent_after' @($running | ForEach-Object { [int]$_.ProcessId })
        if ($running.Count -eq 0) { throw 'Agent exited after launch; send the result for startup-log inspection.' }
        $script:Report.status = 'agent_started_server_heartbeat_pending'
        Write-Host 'Agent 실행을 확인했습니다. 포털에서 다시 점검을 누르고 결과 파일을 전달해 주세요.' -ForegroundColor Green
        $exitCode = 0
    }
} catch {
    $script:Report.status = 'needs_support'
    $script:Report.error = Protect-Output $_.Exception.Message
    Write-Host $script:Report.error -ForegroundColor Red
} finally {
    $script:Report.completed_at = Get-Date -Format o
    $script:Report | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $resultPath -Encoding UTF8
    Write-Host "결과 파일: $resultPath"
}
exit $exitCode
