param([string]$Supervisor = (Join-Path $PSScriptRoot '..\run_accounting_backend.ps1'))
$ErrorActionPreference='Stop'
$tokens=$null;$errors=$null
[System.Management.Automation.Language.Parser]::ParseFile($Supervisor,[ref]$tokens,[ref]$errors)|Out-Null
if($errors.Count){throw 'PowerShell syntax invalid'}
. $Supervisor -Library
$fixture=Join-Path ([IO.Path]::GetTempPath()) ('accounting-supervisor-test-'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory((Join-Path $fixture 'private'))|Out-Null
[IO.File]::WriteAllText((Join-Path $fixture 'private/native-host.json'),'{"originalRoot":"C:/fixture"}')
$script:SState=$fixture
$script:sample=$null;$script:pinned=$null;$script:stops=@();$script:ports=@()
function S-Log([string]$Text){}
function Start-Process {
 $script:sample=[pscustomobject]@{ProcessId=4321;CreationDate=[DateTime]::UtcNow;ExecutablePath=$script:SExe;CommandLine=('"'+$script:SExe+'" '+($script:SArgv -join ' '))}
 return [pscustomobject]@{Id=4321}
}
function S-Process([int]$ProcessId){if($script:sample -and $ProcessId-eq$script:sample.ProcessId){return $script:sample}}
function S-WriteRecord($Record){$script:pinned=$Record}
function S-ReadRecord{return $script:pinned}
function S-Listeners{return $script:ports}
function S-GuardProcesses{if($script:sample){return @($script:sample)};return @()}
function Stop-Process([int]$Id,[switch]$Force){$script:stops+=@($Id);$script:sample=$null}
function S-Pause{throw 'Unexpected monitor delay'}
$results=@()
S-Launch
if(!$script:pinned-or!(S-Pinned $script:sample $script:pinned)){throw 'Child was not pinned before waiting for a listener'}
$results+='launch pins child before port opens'
$valid=$script:pinned
$script:pinned=@{processId=999;createdAtUtc=$valid.createdAtUtc;commandLineSha256=$valid.commandLineSha256}
try{S-RecoverStoppedListener;throw 'Expected identity rejection'}catch{if($_.Exception.Message-ne'ORPHAN_RUNTIME_IDENTITY_DIFFERS'){throw}}
if($script:stops.Count){throw 'Unverified process was stopped'}
$results+='stale record fails closed'
$script:pinned=$valid
$originalCreation=$script:sample.CreationDate
$script:sample.CreationDate=$originalCreation.AddMinutes(1)
try{S-RecoverStoppedListener;throw 'Expected PID reuse rejection'}catch{if($_.Exception.Message-ne'ORPHAN_RUNTIME_IDENTITY_DIFFERS'){throw}}
if($script:stops.Count){throw 'Reused PID was stopped'}
$script:sample.CreationDate=$originalCreation
$results+='reused PID fails closed'
S-Monitor $script:sample $script:pinned
$results+='missing owned listener returns to recovery'
$script:ports=@([pscustomobject]@{LocalAddress='127.0.0.1';OwningProcess=9876})
try{S-Monitor $script:sample $script:pinned;throw 'Expected foreign listener rejection'}catch{if($_.Exception.Message-ne'SUPERVISED_LISTENER_CHANGED'){throw}}
if($script:stops.Count){throw 'Foreign listener was stopped'}
$results+='foreign listener fails closed'
$script:ports=@()
S-RecoverStoppedListener
if($script:stops.Count-ne1-or$script:stops[0]-ne4321){throw 'Recovery did not target exact pinned process'}
$results+='recovery stops only exact pinned process'
$results|ConvertTo-Json -Compress
# The fixture is a unique verified temp directory; leave it for audit.
