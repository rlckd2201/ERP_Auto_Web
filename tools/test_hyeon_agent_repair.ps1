$ErrorActionPreference = 'Stop'
$source = [IO.File]::ReadAllText((Join-Path $PSScriptRoot 'hyeon_agent_repair.ps1'))
$tokens = $null; $errors = $null
[Management.Automation.Language.Parser]::ParseInput($source, [ref]$tokens, [ref]$errors) | Out-Null
if ($errors.Count) { throw ($errors | Out-String) }
. ([scriptblock]::Create($source)) -LibraryOnly
function Assert($Condition, [string]$Message) { if (-not $Condition) { throw $Message } }
$py = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'
Assert (Test-Path -LiteralPath $py) 'Test interpreter missing'
$values = @('space value', 'quote"value', 'C:\trailing\', '현시훈', "single'quote")
$run = Invoke-Python $py 'import json,sys; print(json.dumps(sys.argv[1:],ensure_ascii=False))' $values
Assert ($run.exit_code -eq 0) 'Native invocation failed'
$roundTrip = ConvertFrom-Json -InputObject $run.stdout.Trim()
for ($i=0; $i -lt $values.Count; $i++) { Assert ($roundTrip[$i] -ceq $values[$i]) "Argument corruption at $i" }
Write-Host 'PASS native argument round trip: spaces, quotes, trailing slash, Korean'
$probe = Get-PythonProbe $py
Assert ($probe.executable -and $probe.version[0] -eq 3 -and $probe.modules.requests) 'Real interpreter/import probe failed'
Write-Host 'PASS real interpreter and module imports (no installation)'
$failed = Invoke-Python $py 'import sys; print("intentional"); sys.exit(17)'
Assert ($failed.exit_code -eq 17) 'Exit status lost'
$script:Report = @{steps=(New-Object 'Collections.Generic.List[object]')}
$threw = $false
try { Require-Success 'expected_failure' $failed } catch { $threw = $true }
Assert $threw 'Failed package command must stop before launcher mutation'
Assert ($script:Report.steps[0].result.exit_code -eq 17) 'Failure metadata missing'
Write-Host 'PASS failed child process is recorded and stops the workflow'
$private = Protect-Output 'https://person:password@example.test/index?token=secret token=secret password=secret'
Assert (-not $private.Contains('person:password') -and -not $private.Contains('=secret')) 'Sensitive output not redacted'
Write-Host 'PASS credentials and query redaction'
$launcher = New-Launcher "C:\Users\O'Brien\업무" $py 'https://172.16.19.105:3010'
[Management.Automation.Language.Parser]::ParseInput($launcher,[ref]$tokens,[ref]$errors) | Out-Null
Assert ($errors.Count -eq 0) 'Generated launcher is not valid PowerShell'
Assert ($launcher.Contains("O''Brien") -and $launcher.Contains('REQUESTS_CA_BUNDLE')) 'Launcher quoting/trust settings missing'
Assert ((Read-LauncherPython '$env:PYTHON_EXE = "C:\Python315\python.exe"') -eq 'C:\Python315\python.exe') 'Configured interpreter parsing failed'
Write-Host 'PASS launcher rendering and configured interpreter parsing'
Assert ($source.Contains("`$env:COMPUTERNAME -ne '현시훈PC'")) 'Machine guard absent'
Assert (-not $source.Contains('--insecure')) 'Repair must use certificate verification'
Assert (-not $source.Contains('Remove-Item')) 'Repair must not delete installed applications'
Write-Host 'PASS target guard, TLS verification and non-destructive scope'
$modern = [pscustomobject]@{executable='C:\Python315\python.exe';version=@(3,15,1);bits=64;all_ok=$true}
$compatible = [pscustomobject]@{executable='C:\Python311\python.exe';version=@(3,11,9);bits=64;all_ok=$true}
$incomplete = [pscustomobject]@{executable='C:\Incomplete311\python.exe';version=@(3,11,9);bits=64;all_ok=$false}
Assert (@(Select-RepairPython @($modern)).Count -eq 0) 'Import-success alone must not reuse the observed TLS-incompatible interpreter'
Assert ((Select-RepairPython @($modern,$compatible)).executable -eq $compatible.executable) 'Known compatible runtime must be selected'
Assert (@(Select-RepairPython @($incomplete)).Count -eq 0) 'Incomplete interpreter must take the isolated-repair branch'
Write-Host 'PASS v2 runtime selection: healthy imports on 3.15 still require the verified 3.11 path'
Write-Host 'All 7 checks passed. No repair, installation or Agent launch was performed.'
