param([switch]$Library)
$ErrorActionPreference='Stop'
$script:SState='D:\PortalConnectedSystems\accounting-automation'
$script:SExe='C:\ERP_DB\runtime\Python311\python.exe'
$script:SArgv=@('-B','-u','D:/PortalConnectedSystems/accounting-automation/feature/backend/screens/connection/native-host.py','--config','D:/PortalConnectedSystems/accounting-automation/private/native-host.json')
$script:SRecord=$script:SState+'\ops\runtime-supervision.json'
function S-Hash([string]$Text){$h=[Security.Cryptography.SHA256]::Create();try{return ([BitConverter]::ToString($h.ComputeHash([Text.Encoding]::UTF8.GetBytes($Text)))).Replace('-','').ToLowerInvariant()}finally{$h.Dispose()}}
function S-Canonical([string]$File){return [IO.Path]::GetFullPath($File).ToLowerInvariant()}
function S-Process([int]$ProcessId){return Get-CimInstance Win32_Process -Filter ('ProcessId='+$ProcessId) -ErrorAction SilentlyContinue}
function S-Matches($Process){
 if(!$Process-or![string]$Process.ExecutablePath-or(S-Canonical $Process.ExecutablePath)-cne(S-Canonical $script:SExe)){return $false}
 $tokens=@([regex]::Matches([string]$Process.CommandLine,'"[^"]*"|[^\s"]+')|ForEach-Object{$_.Value.Trim('"')})
 if($tokens.Count-ne$script:SArgv.Count+1){return $false};for($index=0;$index-lt$script:SArgv.Count;$index++){if($tokens[$index+1]-cne$script:SArgv[$index]){return $false}};return $true
}
function S-Listeners {return @(Get-NetTCPConnection -State Listen|Where-Object{$_.LocalPort-eq8081})}
function S-GuardProcesses {return @(Get-CimInstance Win32_Process -Filter "Name='python.exe'"|Where-Object{S-Matches $_})}
function S-ReadRecord {return [IO.File]::ReadAllText($script:SRecord)|ConvertFrom-Json}
function S-Record($Process){return @{processId=$Process.ProcessId;createdAtUtc=$Process.CreationDate.ToUniversalTime().ToString('o');commandLineSha256=(S-Hash ([string]$Process.CommandLine))}}
function S-Pinned($Process,$Record){return (S-Matches $Process)-and$Process.ProcessId-eq$Record.processId-and[DateTimeOffset]$Process.CreationDate-eq[DateTimeOffset]$Record.createdAtUtc-and(S-Hash ([string]$Process.CommandLine))-ceq$Record.commandLineSha256}
function S-WriteRecord($Record){$temp=$script:SRecord+'.'+[guid]::NewGuid().ToString('N')+'.tmp';try{[IO.File]::WriteAllText($temp,($Record|ConvertTo-Json -Compress),[Text.UTF8Encoding]::new($false));if(Test-Path -LiteralPath $script:SRecord){[IO.File]::Replace($temp,$script:SRecord,[System.Management.Automation.Language.NullString]::Value)}else{[IO.File]::Move($temp,$script:SRecord)}}finally{if(Test-Path -LiteralPath $temp){[IO.File]::Delete($temp)}}}
function S-Log([string]$Text){[IO.File]::AppendAllText($script:SLog,([DateTime]::UtcNow.ToString('o')+' '+$Text+[Environment]::NewLine),[Text.UTF8Encoding]::new($false))}
function S-Pause {Start-Sleep -Milliseconds 1000}
function S-Launch {
 $hostConfig=[IO.File]::ReadAllText($script:SState+'\private\native-host.json')|ConvertFrom-Json
 $env:PYTHONHOME=$null;$env:PYTHONPATH=$hostConfig.originalRoot;$env:PLAYWRIGHT_BROWSERS_PATH='C:\ERP_DB\runtime\ms-playwright'
 $stamp=[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ');$logs=$script:SState+'\logs'
 $launched=Start-Process -FilePath $script:SExe -ArgumentList $script:SArgv -WorkingDirectory $hostConfig.originalRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logs ($stamp+'.stdout.log')) -RedirectStandardError (Join-Path $logs ($stamp+'.stderr.log')) -PassThru
 $process=S-Process $launched.Id
 if(!(S-Matches $process)){throw 'LAUNCHED_PROCESS_IDENTITY_DIFFERS'}
 # Pin the exact child before waiting for imports/startup to open its listener.
 S-WriteRecord (S-Record $process)
 S-Log ('launched pinned runtime '+$process.ProcessId)
}
function S-Monitor($Process,$Record){
 S-Log ('adopted listener '+$Process.ProcessId)
 while($true){$current=S-Process $Record.processId;if(!$current){S-Log 'listener exited';return};if(!(S-Pinned $current $Record)){throw 'SUPERVISED_PROCESS_IDENTITY_CHANGED'};$ports=@(S-Listeners);if($ports.Count-eq0){S-Log 'pinned listener stopped; recovering';return};if($ports.Count-ne1-or$ports[0].LocalAddress-cne'127.0.0.1'-or$ports[0].OwningProcess-ne$Record.processId){throw 'SUPERVISED_LISTENER_CHANGED'};S-Pause}
}
# Included in the accounting runtime supervisor. No recovery runs on import.
# S-Pinned checks executable, exact command, PID and process creation time.
function S-RecoverStoppedListener {
    $guards = @(S-GuardProcesses)
    if ($guards.Count -eq 0) { return }
    if ($guards.Count -ne 1) { throw 'MULTIPLE_GUARD_PROCESSES' }
    $record = S-ReadRecord
    $current = S-Process $guards[0].ProcessId
    if (!$current -or !(S-Pinned $current $record)) {
        throw 'ORPHAN_RUNTIME_IDENTITY_DIFFERS'
    }
    # A listener that appeared during inspection may belong to a healthy runtime.
    if (@(S-Listeners).Count) { throw 'LISTENER_APPEARED_DURING_RECOVERY' }
    $current = S-Process $record.processId
    if (!$current -or !(S-Pinned $current $record)) {
        throw 'ORPHAN_RUNTIME_IDENTITY_CHANGED'
    }
    S-Log ('recovering pinned runtime without listener ' + $record.processId)
    Stop-Process -Id $record.processId -Force -ErrorAction Stop
    $deadline = [DateTime]::UtcNow.AddSeconds(10)
    while ($remaining = S-Process $record.processId) {
        if (!(S-Pinned $remaining $record)) { throw 'RECOVERY_PROCESS_ID_REUSED' }
        if ([DateTime]::UtcNow -ge $deadline) { throw 'ORPHAN_RUNTIME_STOP_TIMEOUT' }
        Start-Sleep -Milliseconds 100
    }
}

function S-Run {
 $ports=@(S-Listeners)
 if($ports.Count){if($ports.Count-ne1-or$ports[0].LocalAddress-cne'127.0.0.1'){throw 'FOREIGN_OR_AMBIGUOUS_LISTENER'};$process=S-Process $ports[0].OwningProcess;$record=S-ReadRecord;if(!(S-Pinned $process $record)){throw 'EXISTING_LISTENER_IDENTITY_DIFFERS'};return S-Monitor $process $record}
 S-RecoverStoppedListener
 $started=[DateTimeOffset]::UtcNow;S-Launch
 $deadline=[DateTime]::UtcNow.AddSeconds(180)
 do{$ports=@(S-Listeners);$guards=@(S-GuardProcesses);if($guards.Count-gt1){throw 'MULTIPLE_GUARD_PROCESSES'};if($ports.Count){if($ports.Count-ne1-or$ports[0].LocalAddress-cne'127.0.0.1'){throw 'STARTED_LISTENER_DIFFERS'};$process=S-Process $ports[0].OwningProcess;$record=S-ReadRecord;if(!(S-Pinned $process $record)-or[DateTimeOffset]$process.CreationDate-lt$started){throw 'STARTED_PROCESS_IDENTITY_DIFFERS'};return S-Monitor $process $record};S-Pause}while([DateTime]::UtcNow-lt$deadline)
 throw 'VERIFIED_LISTENER_START_TIMEOUT'
}
if(!$Library){
 $mutex=[Threading.Mutex]::new($false,'Global\DSIGAccountingNativeRuntimeSupervisor');$held=$false
 try{try{$held=$mutex.WaitOne(0)}catch [Threading.AbandonedMutexException]{$held=$true};if(!$held){exit 0};$logs=$script:SState+'\logs';[IO.Directory]::CreateDirectory($logs)|Out-Null;$script:SLog=Join-Path $logs ('supervision-'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ')+'-'+$PID+'.log');while($true){S-Run;S-Pause}}
 catch{if($script:SLog){S-Log ('supervision rejected runtime: '+$_.Exception.Message)};exit 1}
 finally{if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}
}
