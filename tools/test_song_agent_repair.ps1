param([Parameter(Mandatory=$true)][string]$PackageDirectory)
$ErrorActionPreference = 'Stop'
function Assert($Condition,[string]$Message) { if (-not $Condition) { throw $Message } }
$resources = Join-Path ([IO.Path]::GetFullPath($PackageDirectory)) 'resources'
. (Join-Path $resources 'repair.ps1') -LibraryOnly
$passed = 0
Assert-SongIdentity '송명학' '전산 송명학'
foreach ($pair in @(@('김기창','전산 송명학'),@('송명학','송명학'),@('송명학','Administrator'))) {
    $rejected = $false
    try { Assert-SongIdentity $pair[0] $pair[1] } catch { $rejected = $true }
    Assert $rejected 'Wrong PC or Windows user was accepted'
}
$passed++;Write-Host 'PASS exact affected PC/user guard'
$root = Get-SongRoot "C:\Users\전산 송명학"
Assert ($root -ceq 'C:\Users\전산 송명학\Desktop\개발파일\회계업무 자동화_WEB_Version') 'Wrong installation path'
$passed++;Write-Host 'PASS missing launcher recovery uses the diagnosed user installation'
$cert = Get-PinnedCertificate (Join-Path $resources 'server105-trust.pem')
Assert ($cert.Thumbprint -eq '4FDA8BA45533953FDC16CF5018AB9164F3DB53D1') 'Certificate fingerprint differs from operating server'
$passed++;Write-Host 'PASS actual public certificate identity and validity'
$temporary = Join-Path $env:TEMP ('song_repair_test_' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $temporary | Out-Null
$changedCert = Join-Path $temporary 'changed.pem'
[IO.File]::WriteAllText($changedCert,[IO.File]::ReadAllText((Join-Path $resources 'server105-trust.pem')) + "`n")
$rejected = $false
try { Get-PinnedCertificate $changedCert | Out-Null } catch { $rejected = $true }
Assert $rejected 'Modified certificate was accepted'
$passed++;Write-Host 'PASS modified certificate rejected before trust changes'
$py = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'
Assert (Test-Path -LiteralPath $py) 'Local test Python missing'
$argsToCheck = @('space value','quote"value','C:\trailing\',"전산 송명학's path")
$run = Invoke-Python $py 'import json,sys; print(json.dumps(sys.argv[1:],ensure_ascii=False))' $argsToCheck
Assert ($run.exit_code -eq 0) 'Native invocation failed'
$received = ConvertFrom-Json -InputObject $run.stdout.Trim()
for ($i=0;$i -lt $argsToCheck.Count;$i++) { Assert ($received[$i] -ceq $argsToCheck[$i]) "Argument corrupted: $i" }
$passed++;Write-Host 'PASS Windows argument round trip with spaces, quotes and Korean'
$failed = Invoke-Python $py 'import sys; print("intentional failure"); sys.exit(17)'
$script:Report = @{steps=(New-Object 'Collections.Generic.List[object]')}
$rejected = $false
try { Require-Success 'fixture_failure' $failed } catch { $rejected = $true }
Assert ($rejected -and $script:Report.steps[0].result.exit_code -eq 17) 'Failed child did not stop or record its exit code'
$passed++;Write-Host 'PASS failed subprocess records reason and stops recovery'
$rendered = New-SongLauncher "C:\Users\O'Brien\전산 송명학" $py "C:\Users\O'Brien\cert.pem"
$tokens=$null;$errors=$null
$tree = [Management.Automation.Language.Parser]::ParseInput($rendered,[ref]$tokens,[ref]$errors)
Assert ($errors.Count -eq 0) 'Generated launcher is invalid PowerShell'
$startCommands = @($tree.FindAll({param($node) $node -is [Management.Automation.Language.CommandAst] -and $node.GetCommandName() -eq 'Start-Process'},$true))
Assert ($startCommands.Count -eq 1) 'Launcher must start one Agent'
Assert ($rendered.Contains('-WindowStyle Hidden') -and $rendered.Contains('REQUESTS_CA_BUNDLE') -and -not $rendered.Contains('--insecure') -and -not $rendered.Contains('--agent-id') -and -not $rendered.Contains('pip install')) 'Launcher unexpectedly changes TLS, identity, or packages'
$passed++;Write-Host 'PASS persistent launcher syntax, TLS verification and natural Agent identity'
$originalCa = $env:REQUESTS_CA_BUNDLE;$originalServer = $env:WEB_SERVER_URL;$originalPython = $env:PYTHON_EXE
function Start-Process { param($FilePath,$ArgumentList,$WorkingDirectory,$WindowStyle) $script:CapturedStart=@{path=$FilePath;arguments=$ArgumentList;directory=$WorkingDirectory;style=$WindowStyle} }
try { & ([scriptblock]::Create($rendered));Assert ($env:PYTHON_EXE -ceq $py) 'Verified Python must survive Agent self-update' } finally { Remove-Item Function:\Start-Process;$env:REQUESTS_CA_BUNDLE=$originalCa;$env:WEB_SERVER_URL=$originalServer;$env:PYTHON_EXE=$originalPython }
Assert ($script:CapturedStart.directory -ceq "C:\Users\O'Brien\전산 송명학" -and $script:CapturedStart.style -eq 'Hidden') 'Launcher invocation lost path or window policy'
Assert ($script:CapturedStart.arguments.Contains('"C:\Users\O''Brien\전산 송명학\web_v1\agent\erp_agent.py"')) 'Agent path is not quoted'
$passed++;Write-Host 'PASS generated launcher invocation without starting an Agent'
$private = Protect-Output 'https://person:password@example.test/path?token=secret token=secret password=secret'
Assert (-not $private.Contains('person:password') -and -not $private.Contains('=secret')) 'Sensitive output not redacted'
$passed++;Write-Host 'PASS diagnostic output redaction'
foreach ($file in @('repair.ps1','repair-common.ps1')) {
    $bytes=[IO.File]::ReadAllBytes((Join-Path $resources $file))
    Assert ($bytes[0] -eq 239 -and $bytes[1] -eq 187 -and $bytes[2] -eq 191) 'Windows PowerShell Korean resource needs UTF-8 BOM'
    [Management.Automation.Language.Parser]::ParseInput([IO.File]::ReadAllText((Join-Path $resources $file)),[ref]$tokens,[ref]$errors) | Out-Null
    Assert ($errors.Count -eq 0) "Invalid packaged script: $file"
}
$passed++;Write-Host 'PASS packaged Windows PowerShell resources and encoding'
& (Join-Path $PackageDirectory 'AccountingWebSongRepair.exe') --self-test
Assert ($LASTEXITCODE -eq 0) 'Compiled executable resource test failed'
$passed++;Write-Host 'PASS standalone executable resources (no repair executed)'
Write-Host "All $passed checks passed. No settings, certificate stores, startup registration or Agent process changed."
