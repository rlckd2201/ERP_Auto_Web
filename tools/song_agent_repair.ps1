param([switch]$LibraryOnly, [string]$ResultPath)
$ErrorActionPreference = 'Stop'
# The dot-sourced library assigns its own LibraryOnly parameter in this scope.
# Keep the requested entry mode separate so a normal run reaches the repair.
$songLibraryOnly = [bool]$LibraryOnly
. (Join-Path $PSScriptRoot 'repair-common.ps1') -LibraryOnly

function Assert-SongIdentity([string]$Computer, [string]$User) {
    if ($Computer -cne '송명학' -or $User -cne '전산 송명학') {
        throw 'This recovery is only for 송명학 / 전산 송명학. No settings were changed.'
    }
}
function Get-SongRoot([string]$Profile) {
    $profilePath = [IO.Path]::GetFullPath($Profile).TrimEnd('\')
    $installPath = [IO.Path]::GetFullPath((Join-Path $profilePath 'Desktop\개발파일\회계업무 자동화_WEB_Version'))
    if (-not $installPath.StartsWith($profilePath + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Installation path is outside the current user profile.'
    }
    $installPath
}
function Get-PinnedCertificate([string]$Path) {
    $expected = '2978977502684f6822d9d046f194f7f9e978357457d3a87385d33cc66e1fb8fd'
    if ((Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash -ine $expected) {
        throw 'The bundled server certificate does not match the verified certificate.'
    }
    $cert = New-Object Security.Cryptography.X509Certificates.X509Certificate2($Path)
    if ($cert.NotAfter.ToUniversalTime() -le [DateTime]::UtcNow -or $cert.NotBefore.ToUniversalTime() -gt [DateTime]::UtcNow) {
        throw 'The verified server certificate is outside its validity period.'
    }
    $cert
}
function Get-RunningSetup {
    @(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object {
        $_.CommandLine -match 'accounting_web_required_setup_[^\r\n]*[\\/]setup\.ps1'
    })
}
function New-SongLauncher([string]$Root, [string]$Python, [string]$CertPath) {
    $pythonw = Join-Path (Split-Path -Parent $Python) 'pythonw.exe'
    if (-not (Test-Path -LiteralPath $pythonw)) { $pythonw = $Python }
    $agent = Join-Path $Root 'web_v1\agent\erp_agent.py'
    $arguments = (@($agent, '--server', 'https://172.16.19.105:3010') | ForEach-Object { Quote-NativeArgument $_ }) -join ' '
    $r = $Root.Replace("'", "''"); $p = $pythonw.Replace("'", "''")
    $a = $arguments.Replace("'", "''"); $c = $CertPath.Replace("'", "''")
    $runtime = $Python.Replace("'", "''")
    @"
`$ErrorActionPreference = 'Stop'
`$env:WEB_SERVER_URL = 'https://172.16.19.105:3010'
`$env:PYTHON_EXE = '$runtime'
`$env:REQUESTS_CA_BUNDLE = '$c'
Start-Process -FilePath '$p' -ArgumentList '$a' -WorkingDirectory '$r' -WindowStyle Hidden
"@
}
function Read-RegistrationBackup {
    $command = ''; $startup = ''
    $key = Get-Item -LiteralPath 'HKCU:\Software\Classes\accountingweb\shell\open\command' -ErrorAction SilentlyContinue
    if ($key) { $command = [string]$key.GetValue('') }
    $key = Get-Item -LiteralPath 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -ErrorAction SilentlyContinue
    if ($key) { $startup = [string]$key.GetValue('AccountingWebAgent') }
    @{protocol_command=$command;startup_command=$startup}
}
function Register-SongLauncher([string]$Launcher, [string]$Root, [string]$Shortcut) {
    $shellExe = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    $runCommand = (@($shellExe,'-NoProfile','-ExecutionPolicy','Bypass','-WindowStyle','Hidden','-File',$Launcher) | ForEach-Object { Quote-NativeArgument $_ }) -join ' '
    $key = 'HKCU:\Software\Classes\accountingweb'
    $commandKey = Join-Path $key 'shell\open\command'
    New-Item -Path $commandKey -Force | Out-Null
    Set-Item -LiteralPath $key -Value 'URL:Accounting WEB 필수 프로그램'
    New-ItemProperty -LiteralPath $key -Name 'URL Protocol' -Value '' -PropertyType String -Force | Out-Null
    Set-Item -LiteralPath $commandKey -Value $runCommand
    $runKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
    New-Item -Path $runKey -Force | Out-Null
    Set-ItemProperty -LiteralPath $runKey -Name 'AccountingWebAgent' -Value $runCommand -Force
    $wsh = New-Object -ComObject WScript.Shell
    $link = $wsh.CreateShortcut($Shortcut)
    $link.TargetPath = $shellExe
    $link.Arguments = (@('-NoProfile','-ExecutionPolicy','Bypass','-WindowStyle','Hidden','-File',$Launcher) | ForEach-Object { Quote-NativeArgument $_ }) -join ' '
    $link.WorkingDirectory = $Root
    $link.WindowStyle = 7
    $link.Save()
    $readback = Read-RegistrationBackup
    if ($readback.protocol_command -cne $runCommand -or $readback.startup_command -cne $runCommand -or -not (Test-Path -LiteralPath $Shortcut)) {
        throw 'Launcher registration verification failed. See the backup and result file.'
    }
}
if ($songLibraryOnly) { return }

$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
if (-not $ResultPath) { $ResultPath = Join-Path ([Environment]::GetFolderPath('Desktop')) "AccountingWeb_SongRepair_$stamp.json" }
[Console]::OutputEncoding = New-Object Text.UTF8Encoding($false)
$script:Report = [ordered]@{repair_version=2;created_at=(Get-Date -Format o);computer=$env:COMPUTERNAME;user=$env:USERNAME;status='started';steps=(New-Object 'Collections.Generic.List[object]')}
$exitCode = 1
try {
    $script:Report | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $ResultPath -Encoding UTF8
    Assert-SongIdentity $env:COMPUTERNAME $env:USERNAME
    if ((Get-AgentProcesses).Count -gt 0) { throw 'An Agent is already running. Do not start another one; send this result for server verification.' }
    if ((Get-RunningSetup).Count -gt 0) { throw 'An installation is still running. Wait for it to finish, then run this recovery once.' }
    $root = Get-SongRoot $env:USERPROFILE
    $agent = Join-Path $root 'web_v1\agent\erp_agent.py'
    $requirements = Join-Path $root 'web_v1\backend\requirements.txt'
    foreach ($path in @($agent,$requirements,(Join-Path $root 'web_v1\VERSION'))) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing installed file: $path" }
    }
    $bundledCert = Join-Path $PSScriptRoot 'server105-trust.pem'
    $certificate = Get-PinnedCertificate $bundledCert
    $basePython = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'
    if (-not (Test-Path -LiteralPath $basePython)) { throw 'The diagnosed Python 3.11 interpreter is missing. No fallback to Python 3.15 was attempted.' }
    Write-Host '1/4 Python 3.11과 필수 패키지를 검사합니다.'
    $probe = Get-PythonProbe $basePython
    Add-Step 'python_before' $probe
    if (-not $probe -or $probe.version[0] -ne 3 -or $probe.version[1] -ne 11 -or $probe.bits -ne 64) { throw 'The diagnosed interpreter is not a working Python 3.11 x64 runtime.' }
    $python = $basePython
    if (-not $probe.all_ok) {
        $runtime = Join-Path $env:LOCALAPPDATA "AccountingWeb\RecoveryRuntime_$stamp"
        Require-Success 'create_isolated_runtime' (Invoke-Native $basePython @('-m','venv',$runtime) 180)
        $python = Join-Path $runtime 'Scripts\python.exe'
        Write-Host '별도 회계 실행환경에 필수 패키지를 설치합니다. 창을 닫지 마세요.'
        Require-Success 'install_packages' (Invoke-Native $python @('-m','pip','install','--disable-pip-version-check','--retries','1','--timeout','20','-r',$requirements) 900)
    }
    $after = Get-PythonProbe $python
    Add-Step 'python_after' $after
    if (-not $after -or -not $after.all_ok) { throw 'Required package imports still fail. Startup settings were not changed.' }
    Write-Host '2/4 인증서와 서버 HTTPS 연결을 검증합니다.'
    $networkCode = "import requests,sys,json; r=requests.get('https://172.16.19.105:3010/api/version',verify=sys.argv[1],timeout=10); r.raise_for_status(); print(json.dumps({'status':r.status_code,'version':r.json().get('version')}))"
    Require-Success 'verified_python_https' (Invoke-Python $python $networkCode @($bundledCert))
    if ((Get-AgentProcesses).Count -gt 0 -or (Get-RunningSetup).Count -gt 0) { throw 'Agent or setup started during the checks. It was left untouched.' }
    $backupDir = Join-Path $env:LOCALAPPDATA "AccountingWeb\RepairBackups\$stamp"
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
    $launcher = Join-Path $root '담당자PC_필수프로그램_실행.ps1'
    $shortcut = Join-Path ([Environment]::GetFolderPath('Desktop')) '회계업무 WEB 필수프로그램 실행.lnk'
    $certPath = Join-Path $env:LOCALAPPDATA 'AccountingWeb\certs\server105-trust.pem'
    $before = Read-RegistrationBackup
    foreach ($path in @($launcher,$shortcut,$certPath)) {
        if (Test-Path -LiteralPath $path -PathType Leaf) { Copy-Item -LiteralPath $path -Destination (Join-Path $backupDir ([IO.Path]::GetFileName($path))) }
    }
    $store = New-Object Security.Cryptography.X509Certificates.X509Store('Root','CurrentUser')
    $store.Open([Security.Cryptography.X509Certificates.OpenFlags]::ReadOnly)
    try { $alreadyTrusted = @($store.Certificates | Where-Object { $_.Thumbprint -eq $certificate.Thumbprint }).Count -gt 0 } finally { $store.Close() }
    $before.certificate_thumbprint = $certificate.Thumbprint
    $before.certificate_already_trusted = $alreadyTrusted
    $before | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $backupDir 'registration_before.json') -Encoding UTF8
    Add-Step 'backup' @{path=$backupDir;registration=$before;launcher_existed=(Test-Path -LiteralPath $launcher)}
    New-Item -ItemType Directory -Path (Split-Path -Parent $certPath) -Force | Out-Null
    Copy-Item -LiteralPath $bundledCert -Destination $certPath -Force
    if (-not $alreadyTrusted) {
        $store.Open([Security.Cryptography.X509Certificates.OpenFlags]::ReadWrite)
        try { $store.Add($certificate) } finally { $store.Close() }
    }
    $store.Open([Security.Cryptography.X509Certificates.OpenFlags]::ReadOnly)
    try { $trusted = @($store.Certificates | Where-Object { $_.Thumbprint -eq $certificate.Thumbprint }).Count -gt 0 } finally { $store.Close() }
    if (-not $trusted) { throw 'Current-user certificate trust verification failed.' }
    Add-Step 'certificate_trust' @{trusted_current_user=$trusted;thumbprint=$certificate.Thumbprint}
    Write-Host '3/4 현재 Windows 사용자의 바로가기와 자동시작을 등록합니다.'
    [IO.File]::WriteAllText($launcher,(New-SongLauncher $root $python $certPath),(New-Object Text.UTF8Encoding($true)))
    Register-SongLauncher $launcher $root $shortcut
    Add-Step 'registration' @{launcher=$launcher;shortcut=$shortcut;expected_agent_id=($env:COMPUTERNAME + '-' + $env:USERNAME)}
    Write-Host '4/4 Agent를 실행합니다.'
    $shellExe = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    $arguments = (@('-NoProfile','-ExecutionPolicy','Bypass','-File',$launcher) | ForEach-Object { Quote-NativeArgument $_ }) -join ' '
    Start-Process -FilePath $shellExe -ArgumentList $arguments -WorkingDirectory $root -WindowStyle Hidden | Out-Null
    Start-Sleep -Seconds 15
    $running = @(Get-AgentProcesses | Where-Object { $_.CommandLine.IndexOf($agent,[StringComparison]::OrdinalIgnoreCase) -ge 0 })
    Add-Step 'agent_processes' @($running | ForEach-Object { [int]$_.ProcessId })
    if ($running.Count -eq 0) { throw 'Agent exited after launch. Send this result for startup-log inspection.' }
    $script:Report.status = 'agent_started_server_heartbeat_pending'
    Write-Host 'Agent 실행 확인. 포털에서 다시 점검을 누르세요. 서버 연결·계정 연결은 별도 확인이 필요합니다.' -ForegroundColor Green
    $exitCode = 0
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
